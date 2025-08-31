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


# 1. All investors for a given company
query_investors_for_company = """
PREFIX : <http://example.org/investment#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?investorName ?percentage ?date ?source
WHERE {
    ?rel a :OwnershipRelation ;
         :company :Dropbox ;
         :investor ?investor ;
         :percentage ?percentage ;
         :investmentDate ?date ;
         :source_url ?source .
    ?investor rdfs:label ?investorName .
}
ORDER BY DESC(?percentage)
"""

print(run_sparql(g_all, query_investors_for_company))


# 2. Companies where BlackRock has majority control
query_majority_blackrock = """
PREFIX : <http://example.org/investment#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?companyName ?percentage ?date
WHERE {
    ?rel a :OwnershipRelation ;
         :investor :BlackRock ;
         :company ?company ;
         :percentage ?percentage ;
         :investmentDate ?date .
    ?company rdfs:label ?companyName .
    FILTER(xsd:decimal(?percentage) > 50)
}
ORDER BY DESC(?percentage)
"""

print(run_sparql(g_all, query_majority_blackrock))


# 3. Investments after a given date
query_after_date = """
PREFIX : <http://example.org/investment#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?investorName ?companyName ?percentage ?date
WHERE {
    ?rel a :OwnershipRelation ;
         :investor ?investor ;
         :company ?company ;
         :percentage ?percentage ;
         :investmentDate ?date .
    ?investor rdfs:label ?investorName .
    ?company rdfs:label ?companyName .
    FILTER(xsd:date(?date) > "2023-01-01"^^xsd:date)
}
ORDER BY ?date
"""

print(run_sparql(g_all, query_after_date))


-------------
# Dynamic SPARQL generation
def generate_sparql_from_question(question):
    prompt = f"""
PREFIX : <http://example.org/investment#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

Classes:
:OwnershipRelation  
:Investor  
:Company  

Predicates:
:investor (OwnershipRelation → Investor)  
:company (OwnershipRelation → Company)  
:percentage (OwnershipRelation → decimal)  
:investmentDate (OwnershipRelation → date)  
:source_url (OwnershipRelation → string)  
rdfs:label (Investor/Company → string)

Generate a SPARQL query that answers the following question:
\"\"\"{question}\"\"\"
Return ONLY the SPARQL query.
"""
    response = gemini_model.generate_content(prompt)
    return response.text.strip()


# Hybrid retrieval
def hybrid_answer(user_question):
    sparql_query = generate_sparql_from_question(user_question)
    structured_results = g_all.query(sparql_query)
    structured_facts = list(structured_results)

    vector_results = weaviate_client.query.get(
        "OwnershipRelation", ["investor", "company", "percentage", "investmentDate", "source_url"]
    ).with_near_text({"concepts": [user_question]}).with_limit(5).do()

    context = f"Structured Facts:\n{structured_facts}\n\nVector Context:\n{vector_results}"
    final_prompt = f"""
Given the following information from two sources:

{context}

Answer the user’s question: \"{user_question}\".
List major and minority stakeholders, investment percentages, and dates.
Cite sources where possible using the provided source URLs.
"""
    llm_response = gemini_model.generate_content(final_prompt)
    return llm_response.text
