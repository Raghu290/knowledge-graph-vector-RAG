from markdownify import markdownify as md
import requests
import cloudscraper
from markdownify import markdownify as md
from typing import List, Dict, Any

def fetch_fintel_ownership(ticker: str) -> List[Dict[str, Any]]:
    url = f"https://fintel.io/so/us/{ticker.lower()}"
    try:
        # Create scraper that mimics Chrome browser
        scraper = cloudscraper.create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        })
        html = scraper.get(url).text
   
        # Convert HTML to Markdown for easy table parsing
        markdown_text = md(html)
        
        # Extract markdown tables
        lines = markdown_text.split("\n")
        tables = []
        current = []
        for line in lines:
            if "|" in line:
                current.append(line)
            elif current:
                tables.append(current)
                current = []
        if current:
            tables.append(current)
        

        def parse_table(table_lines):
            header = [h.strip() for h in table_lines[0].split("|") if h.strip()]
            rows = []
            for row_line in table_lines[2:]:
                cols = [c.strip() for c in row_line.split("|") if c.strip()]
                if len(cols) != len(header):
                    continue
                rows.append(dict(zip(header, cols)))
            return rows

        chosen_table = None
        for tbl in tables:
            rows = parse_table(tbl)
            if rows and any("File Date" in h or "Investor" in h or "Schedule" in h  and  "Form" in h for h in rows[0].keys()):
                chosen_table = rows
                break

        # Fallback to first table if no 13D/G found
        if not chosen_table and tables:
            chosen_table = parse_table(tables[0])

        if not chosen_table:
            print(f"No ownership table found for {ticker}")
            return []

        result = []
    
        for row in chosen_table:
            investor = row.get("Investor") or row.get("Holder") or next(iter(row.values()), None)
            pct_text = row.get("% Ownership") or row.get("% Out") or row.get("Ownership (%)") or row.get("Ownership (Percent)") or ""
            try:
                pct_val = float(pct_text.replace("%", "").strip())
            except:
                pct_val = None
            date = row.get("Effective Date") or row.get("File Date") or None

            result.append({
                "investor": investor,
                "company": ticker,
                "percentage": pct_val,
                "source": "Fintel (13D/G)" if any("13D" in h or "13G" in h for h in row.keys()) else "Fintel (Fallback)",
                "raw_text": " | ".join(row.values()),
                "investment_date": date
            })

        return result

    except Exception as e:
        print(f"Fintel fetch error for {ticker}: {e}")
        return []

print(fetch_fintel_ownership('DBX'))
