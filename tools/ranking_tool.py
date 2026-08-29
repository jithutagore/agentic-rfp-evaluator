import pandas as pd
from datetime import datetime

def calculate_metrics(suppliers_data: list, active_criteria: list) -> dict:
    """
    suppliers_data: list of dicts with keys:
    'supplier_name', 'submission_date', 'experience_rating', 'evaluation' (SupplierEvaluation object)
    
    active_criteria: list of dicts from DB:
    [{'criterion_id': 1, 'weight': 0.3}, ...]
    
    Returns:
    - enriched_suppliers (list of dicts with final scores)
    - benchmarks (dict of criterion_id: highest_score)
    """
    
    # Create lookup for weights
    weight_lookup = {c['criterion_id']: c['weight'] for c in active_criteria}
    
    # 1. Calculate Absolute Weighted Score and find Benchmarks
    benchmarks = {}
    
    for supplier in suppliers_data:
        eval_obj = supplier['evaluation']
        abs_score = 0.0
        
        for crit in eval_obj.criteria:
            c_id = crit.criterion_id
            w = weight_lookup.get(c_id, 0)
            
            # Absolute weighted score contribution
            if crit.max_score > 0:
                abs_score += (crit.score / crit.max_score) * w
                
            # Update benchmark
            if c_id not in benchmarks or crit.score > benchmarks[c_id]:
                benchmarks[c_id] = crit.score
                
        supplier['absolute_score'] = abs_score

    # 2. Calculate Gap, Relative %, and PPI
    for supplier in suppliers_data:
        eval_obj = supplier['evaluation']
        ppi = 0.0
        
        for crit in eval_obj.criteria:
            c_id = crit.criterion_id
            w = weight_lookup.get(c_id, 0)
            b_mark = benchmarks.get(c_id, 0)
            
            crit.benchmark = b_mark
            crit.gap = crit.score - b_mark
            
            if b_mark > 0:
                rel_perf = (crit.score / b_mark) * 100
            else:
                rel_perf = 100.0 if crit.score > 0 else 0.0
            
            crit.relative_performance_pct = rel_perf
            ppi += rel_perf * w
            
        supplier['ppi'] = ppi
        
    # 3. Apply Tie-Breaks and Assign Rank
    # 1) Higher PPI first -> 2) Earlier submission date -> 3) Higher experience rating -> 4) Supplier name in ascending order
    
    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return datetime.max
            
    # Sort with custom keys
    suppliers_data.sort(key=lambda x: (
        -x['ppi'],                        # 1. Higher PPI (negative for descending)
        parse_date(x['submission_date']), # 2. Earlier date (ascending)
        -x['experience_rating'],          # 3. Higher experience (negative for descending)
        x['supplier_name'].lower()        # 4. Name ascending
    ))
    
    # Assign ranks
    for rank, supplier in enumerate(suppliers_data, start=1):
        supplier['final_rank'] = rank
        
    return suppliers_data, benchmarks
