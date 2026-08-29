import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import datetime

from tools.document_tool import extract_text_from_pdf
from tools.evaluation_agent import evaluate_supplier
from tools.validation_tool import validate_evaluation
from tools.ranking_tool import calculate_metrics

DB_PATH = "rfp_evaluation.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_active_criteria():
    conn = get_db_connection()
    criteria = conn.execute("SELECT * FROM evaluation_criteria WHERE is_active = 1").fetchall()
    conn.close()
    return [dict(c) for c in criteria]

def save_run(status="COMPLETED"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rfp_runs (status) VALUES (?)", (status,))
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return run_id

def save_supplier_results(run_id, suppliers_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for s in suppliers_data:
        # Convert Pydantic evaluation to dict for JSON storage
        result_json = s['evaluation'].json()
        
        cursor.execute('''
            INSERT INTO supplier_results 
            (rfp_run_id, supplier_name, submission_date, experience_rating, absolute_score, ppi, final_rank, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (run_id, s['supplier_name'], s['submission_date'], s['experience_rating'], s['absolute_score'], s['ppi'], s['final_rank'], result_json))
        
    conn.commit()
    conn.close()

st.set_page_config(page_title="Agentic RFP Evaluator", layout="wide")

st.title("Agentic RFP Evaluation & Supplier Ranking")

# Load Criteria
criteria = get_active_criteria()
st.sidebar.header("Active Evaluation Criteria")
if criteria:
    for c in criteria:
        st.sidebar.markdown(f"**{c['name']}** (Weight: {c['weight']*100:.0f}%, Max Score: {c['max_score']})")
        st.sidebar.caption(c['description'])
else:
    st.sidebar.warning("No active criteria found in DB. Please run init_db.py")

st.header("1. Supplier Input")

# Dynamic form for multiple suppliers
if 'supplier_count' not in st.session_state:
    st.session_state.supplier_count = 1

col1, col2 = st.columns([1, 5])
with col1:
    if st.button("Add Supplier"):
        st.session_state.supplier_count += 1
with col2:
    if st.button("Remove Supplier") and st.session_state.supplier_count > 1:
        st.session_state.supplier_count -= 1

supplier_inputs = []

with st.form("evaluation_form"):
    for i in range(st.session_state.supplier_count):
        st.subheader(f"Supplier {i+1}")
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Supplier Name", key=f"name_{i}")
        sub_date = c2.date_input("Submission Date", key=f"date_{i}")
        exp_rating = c3.number_input("Experience Rating (1-10)", min_value=1, max_value=10, value=5, key=f"exp_{i}")
        pdf_file = c4.file_uploader("Upload Proposal PDF", type=["pdf"], key=f"pdf_{i}")
        
        supplier_inputs.append({
            "supplier_name": name,
            "submission_date": str(sub_date),
            "experience_rating": exp_rating,
            "pdf_file": pdf_file
        })
        
    submit_button = st.form_submit_button("Run Evaluation")

if submit_button:
    # Validation
    valid = True
    for idx, s in enumerate(supplier_inputs):
        if not s['supplier_name'] or not s['pdf_file']:
            st.error(f"Please provide name and PDF for Supplier {idx+1}")
            valid = False
            
    if valid:
        st.header("2. Processing Workflow")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        suppliers_data = []
        total_steps = len(supplier_inputs) * 3 + 2
        current_step = 0
        
        try:
            for s in supplier_inputs:
                # 1. Extract Text
                status_text.text(f"Extracting text from {s['supplier_name']}'s PDF...")
                text = extract_text_from_pdf(s['pdf_file'])
                current_step += 1; progress_bar.progress(current_step / total_steps)
                
                # 2. Evaluate using LLM
                status_text.text(f"Evaluating {s['supplier_name']} with LLM...")
                raw_json = evaluate_supplier(s['supplier_name'], text, criteria)
                current_step += 1; progress_bar.progress(current_step / total_steps)
                
                # 3. Validate
                status_text.text(f"Validating outputs for {s['supplier_name']}...")
                validated_eval = validate_evaluation(raw_json, criteria)
                current_step += 1; progress_bar.progress(current_step / total_steps)
                
                s['evaluation'] = validated_eval
                suppliers_data.append(s)
            
            # 4. Rank and Calculate Metrics
            status_text.text("Benchmarking and calculating final ranks...")
            suppliers_data, benchmarks = calculate_metrics(suppliers_data, criteria)
            current_step += 1; progress_bar.progress(current_step / total_steps)
            
            # 5. Save to DB
            status_text.text("Saving results to database...")
            run_id = save_run("COMPLETED")
            save_supplier_results(run_id, suppliers_data)
            current_step += 1; progress_bar.progress(current_step / total_steps)
            
            status_text.success(f"Evaluation complete! Run ID: {run_id}")
            
            # Leaderboard
            st.header("3. Leaderboard")
            
            leaderboard_data = []
            for s in suppliers_data:
                leaderboard_data.append({
                    "Rank": s['final_rank'],
                    "Supplier": s['supplier_name'],
                    "Absolute Score": f"{s['absolute_score']:.2f}",
                    "PPI": f"{s['ppi']:.2f}%",
                    "Experience": s['experience_rating'],
                    "Submission Date": s['submission_date']
                })
            
            df_leaderboard = pd.DataFrame(leaderboard_data)
            st.dataframe(df_leaderboard, hide_index=True, use_container_width=True)
            
            st.info("Tie-break order: Higher PPI -> Earlier submission date -> Higher experience rating -> Supplier name ascending")
            
            # Detailed Scorecards
            st.header("4. Detailed Scorecards")
            
            for s in suppliers_data:
                with st.expander(f"Scorecard: {s['supplier_name']} (Rank #{s['final_rank']})"):
                    eval_obj = s['evaluation']
                    
                    st.write(f"**Overall Summary**: {eval_obj.overall_summary}")
                    
                    if eval_obj.risks:
                        st.markdown("**Risks Detected:**")
                        for r in eval_obj.risks:
                            st.markdown(f"- {r}")
                            
                    score_data = []
                    for crit in eval_obj.criteria:
                        # Find name
                        crit_name = next((c['name'] for c in criteria if c['criterion_id'] == crit.criterion_id), f"ID {crit.criterion_id}")
                        weight = next((c['weight'] for c in criteria if c['criterion_id'] == crit.criterion_id), 0.0)
                        
                        score_data.append({
                            "Criterion": crit_name,
                            "Weight": f"{weight*100:.0f}%",
                            "Score": crit.score,
                            "Max": crit.max_score,
                            "Benchmark": crit.benchmark,
                            "Gap": crit.gap,
                            "Relative %": f"{crit.relative_performance_pct:.2f}%",
                            "Justification": crit.justification,
                            "Evidence": crit.evidence
                        })
                        
                    st.dataframe(pd.DataFrame(score_data), hide_index=True)
            
            # JSON Download
            st.header("5. Run Details")
            st.write(f"RFP_RUN_ID: {run_id}")
            
            # Prepare JSON for download
            full_json_export = {
                "rfp_run_id": run_id,
                "timestamp": datetime.now().isoformat(),
                "benchmarks": benchmarks,
                "results": [json.loads(s['evaluation'].json()) for s in suppliers_data]
            }
            
            st.download_button(
                label="Download Complete Results (JSON)",
                data=json.dumps(full_json_export, indent=2),
                file_name=f"rfp_run_{run_id}.json",
                mime="application/json"
            )
            
        except Exception as e:
            st.error(f"An error occurred during evaluation: {e}")
            import traceback
            st.code(traceback.format_exc())
