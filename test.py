from markdownify import markdownify as md

def fetch_fintel_ownership(ticker: str) -> List[Dict[str, Any]]:
    url = f"https://fintel.io/so/us/{ticker.lower()}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        markdown_text = md(r.text)

        lines = markdown_text.split("\n")
        tables = []
        current = []

        # Collect all markdown tables
        for line in lines:
            if "|" in line:
                current.append(line)
            elif current:
                tables.append(current)
                current = []
        if current:
            tables.append(current)

        result = []

        def parse_table(table_lines):
            header = [h.strip() for h in table_lines[0].split("|") if h.strip()]
            rows = []
            for row_line in table_lines[2:]:
                cols = [c.strip() for c in row_line.split("|") if c.strip()]
                if len(cols) != len(header): continue
                rows.append(dict(zip(header, cols)))
            return rows

        parsed = parse_table(tables[0]) if tables else []

        # Identify 13D/G vs 13F based on header presence
        if any("13D" in k or "13G" in k or "Schedule" in k for k in parsed[0].keys()):
            data = parsed
        else:
            data = parsed  # fallback to 13F table (second table if exists)
            # Optionally pick tables[1] if len(tables) > 1

        for row in data:
            investor = row.get("Investor") or row.get("Holder") or next(iter(row.values()), None)
            pct_text = row.get("% Ownership") or row.get("% Out") or row.get("Ownership (%)") or ""
            try:
                pct_val = float(pct_text.replace("%", "").strip())
            except:
                pct_val = None
            date = row.get("Effective Date") or row.get("File Date") or None

            result.append({
                "investor": investor,
                "company": ticker,
                "percentage": pct_val,
                "source": "Fintel (13D/G)" if "13D" in (row.keys()) else "Fintel (Fallback)",
                "raw_text": " | ".join(row.values()),
                "investment_date": date
            })

        return result

    except Exception as e:
        print(f"Fintel fetch error for {ticker}: {e}")
        return []
