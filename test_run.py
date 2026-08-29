import os
import sqlite3
import json
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from pypdf import PdfReader
from pydantic import BaseModel, Field
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "rfp_evaluation.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create tables if not exist
cursor.execute('''CREATE TABLE IF NOT EXISTS evaluation_criteria (criterion_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT NOT NULL, weight REAL NOT NULL, max_score INTEGER NOT NULL, is_active BOOLEAN NOT NULL DEFAULT 1)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS rfp_runs (rfp_run_id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT NOT NULL)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS supplier_results (id INTEGER PRIMARY KEY AUTOINCREMENT, rfp_run_id INTEGER NOT NULL, supplier_name TEXT NOT NULL, submission_date TEXT NOT NULL, experience_rating INTEGER NOT NULL, absolute_score REAL, ppi REAL, final_rank INTEGER, result_json TEXT, FOREIGN KEY(rfp_run_id) REFERENCES rfp_runs(rfp_run_id))''')

criteria_data = [
    ("Technical Capability", "Architecture, integrations, scalability, technical fit", 0.30, 10, 1),
    ("Implementation Plan", "Timeline, milestones, staffing, risk plan", 0.20, 10, 1),
    ("Commercial Value", "Pricing clarity, total cost, assumptions", 0.20, 10, 1),
    ("Security & Compliance", "Controls, certifications, privacy, auditability", 0.20, 10, 1),
    ("Support & Experience", "Support model, similar projects, references", 0.10, 10, 1)
]
cursor.executemany('''INSERT OR IGNORE INTO evaluation_criteria (name, description, weight, max_score, is_active) VALUES (?, ?, ?, ?, ?)''', criteria_data)
conn.commit()
conn.close()
print("Database initialized and seeded.")

os.makedirs("synthetic_rfps", exist_ok=True)

PROPOSALS = {
    "Apex Systems": {"summary": "Strong technical design and security; higher price; moderate delivery schedule.", "solution": "Microservices and multi-region failover.", "timeline": "Phase 1 in 4 months, Phase 2 in 8 months.", "pricing": "Total Cost: $1,200,000.", "security": "Military-grade encryption, SOC 2 Type II.", "support": "24/7 dedicated support model."},
    "BrightPath Tech": {"summary": "Lowest price and fast timeline; weak compliance detail and limited experience.", "solution": "Off-the-shelf platform customization.", "timeline": "Full rollout expected within 6 weeks.", "pricing": "Total Cost: $350,000.", "security": "Basic SSL and standard data encryption.", "support": "Email-only support with 48-hour SLA."},
    "NexaWorks": {"summary": "Balanced proposal; strongest implementation plan and support model.", "solution": "Hybrid cloud model. Well-documented API.", "timeline": "Full deployment in 5 months. Detailed week-by-week milestones.", "pricing": "Total Cost: $750,000.", "security": "ISO 27001 certified.", "support": "1-hour critical response time. Extensive training."},
    "Orbit Digital": {"summary": "Strong experience and references; vague integration plan; medium pricing.", "solution": "Legacy-compatible solution. SOAP APIs.", "timeline": "Timeline is roughly 6-7 months.", "pricing": "Total Cost: $600,000.", "security": "Legacy compliance standards met.", "support": "Extremely strong references from Fortune 500 companies."}
}

class RFP_PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 15)
        self.cell(0, 10, "Supplier RFP Response", border=0, new_x="LMARGIN", new_y="NEXT", align="C")

for supplier, content in PROPOSALS.items():
    file_path = f"synthetic_rfps/{supplier.replace(' ', '_')}_Proposal.pdf"
    if not os.path.exists(file_path):
        pdf = RFP_PDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"Proposal: {supplier}", new_x="LMARGIN", new_y="NEXT", align="C")
        for title, body in content.items():
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, title.capitalize(), new_x="LMARGIN", new_y="NEXT", align="L")
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, body)
        pdf.output(file_path)

print("Synthetic PDFs checked/generated in 'synthetic_rfps/'")

def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

class CriterionScore(BaseModel):
    criterion_id: int
    score: float
    max_score: int
    justification: str
    evidence: str
    benchmark: float = 0.0
    gap: float = 0.0
    relative_performance_pct: float = 0.0

class SupplierEvaluation(BaseModel):
    supplier_name: str
    criteria: List[CriterionScore]
    risks: List[str]
    overall_summary: str

def validate_evaluation(raw_json: dict, active_criteria: list) -> SupplierEvaluation:
    eval_data = SupplierEvaluation(**raw_json)
    active_dict = {c['criterion_id']: c for c in active_criteria}
    evaluated_dict = {c.criterion_id: c for c in eval_data.criteria}
    
    normalized_criteria = []
    for crit_id, crit_info in active_dict.items():
        if crit_id in evaluated_dict:
            score_data = evaluated_dict[crit_id]
            score_data.score = max(0, min(score_data.score, crit_info['max_score']))
            score_data.max_score = crit_info['max_score']
            normalized_criteria.append(score_data)
        else:
            normalized_criteria.append(CriterionScore(criterion_id=crit_id, score=0, max_score=crit_info['max_score'], justification="Missing", evidence="None"))
            
    eval_data.criteria = normalized_criteria
    return eval_data

def evaluate_supplier(supplier_name: str, extracted_text: str, active_criteria: list) -> dict:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY")
    )
    
    criteria_text = ""
    for c in active_criteria:
        criteria_text += f"- ID: {c['criterion_id']} | Name: {c['name']} | Max Score: {c['max_score']} | Description: {c['description']}\n"
    
    prompt = f"""
    You are an expert procurement evaluator. Please evaluate the following supplier RFP response.
    
    Supplier Name: {supplier_name}
    
    Active Evaluation Criteria:
    {criteria_text}
    
    Supplier Document Text:
    {extracted_text}
    
    Instructions:
    - Use only evidence present in the supplier document.
    - Return one result for every active criterion.
    - Stay within the score range (0 to max_score).
    - Provide a concise justification and quote specific evidence.
    - Summarize any risks and provide an overall summary.
    
    IMPORTANT: You must return the output STRICTLY as a JSON object matching the following structure:
    {{
      "supplier_name": "...",
      "criteria": [
        {{
          "criterion_id": 1,
          "score": 8,
          "max_score": 10,
          "justification": "...",
          "evidence": "..."
        }}
      ],
      "risks": ["..."],
      "overall_summary": "..."
    }}
    """
    
    response = client.chat.completions.create(
        model="liquid/lfm-2.5-2.6b:free",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    
    return json.loads(response.choices[0].message.content)

def calculate_metrics(suppliers_data: list, active_criteria: list) -> list:
    weight_lookup = {c['criterion_id']: c['weight'] for c in active_criteria}
    benchmarks = {}
    
    # Benchmarks and Absolute Score
    for s in suppliers_data:
        eval_obj = s['evaluation']
        s['absolute_score'] = sum((c.score / c.max_score) * weight_lookup.get(c.criterion_id, 0) for c in eval_obj.criteria if c.max_score > 0)
        for c in eval_obj.criteria:
            benchmarks[c.criterion_id] = max(benchmarks.get(c.criterion_id, 0), c.score)

    # PPI and Gap
    for s in suppliers_data:
        ppi = 0.0
        for c in s['evaluation'].criteria:
            c.benchmark = benchmarks.get(c.criterion_id, 0)
            c.gap = c.score - c.benchmark
            c.relative_performance_pct = (c.score / c.benchmark) * 100 if c.benchmark > 0 else (100.0 if c.score > 0 else 0.0)
            ppi += c.relative_performance_pct * weight_lookup.get(c.criterion_id, 0)
        s['ppi'] = ppi
        
    # Sort: PPI -> Date -> Experience -> Name
    suppliers_data.sort(key=lambda x: (
        -x['ppi'], datetime.strptime(x['submission_date'], "%Y-%m-%d"), -x['experience_rating'], x['supplier_name'].lower()
    ))
    
    for rank, s in enumerate(suppliers_data, 1):
        s['final_rank'] = rank
    return suppliers_data

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
active_criteria = [dict(row) for row in conn.execute("SELECT * FROM evaluation_criteria").fetchall()]
conn.close()

suppliers = [
    {"supplier_name": "Apex Systems", "submission_date": "2023-10-01", "experience_rating": 8, "pdf_path": "synthetic_rfps/Apex_Systems_Proposal.pdf"},
    {"supplier_name": "BrightPath Tech", "submission_date": "2023-10-02", "experience_rating": 5, "pdf_path": "synthetic_rfps/BrightPath_Tech_Proposal.pdf"},
    {"supplier_name": "NexaWorks", "submission_date": "2023-10-01", "experience_rating": 7, "pdf_path": "synthetic_rfps/NexaWorks_Proposal.pdf"},
    {"supplier_name": "Orbit Digital", "submission_date": "2023-09-28", "experience_rating": 9, "pdf_path": "synthetic_rfps/Orbit_Digital_Proposal.pdf"}
]

# Ensure OPENROUTER_API_KEY is set in environment
print("Starting Evaluation...")
for s in suppliers:
    print(f"Processing {s['supplier_name']}...")
    text = extract_text_from_pdf(s['pdf_path'])
    raw_json = evaluate_supplier(s['supplier_name'], text, active_criteria)
    s['evaluation'] = validate_evaluation(raw_json, active_criteria)

suppliers = calculate_metrics(suppliers, active_criteria)
print("\nEvaluation Complete!")

leaderboard = [{
    "Rank": s['final_rank'],
    "Supplier": s['supplier_name'],
    "Absolute Score": round(s['absolute_score'], 2),
    "PPI (%)": round(s['ppi'], 2)
} for s in suppliers]

df_leaderboard = pd.DataFrame(leaderboard)
print(df_leaderboard.to_string())


