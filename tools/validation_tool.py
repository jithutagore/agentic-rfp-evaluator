from pydantic import BaseModel, Field
from typing import List

class CriterionScore(BaseModel):
    criterion_id: int
    score: float = Field(..., description="Score out of max_score")
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
    """
    Validates and normalizes the parsed JSON using Pydantic.
    Ensures missing criteria are handled, clips out-of-range scores.
    active_criteria is a list of dicts: [{'criterion_id': 1, 'max_score': 10}, ...]
    """
    try:
        eval_data = SupplierEvaluation(**raw_json)
    except Exception as e:
        raise ValueError(f"Schema validation failed: {e}")

    # Create a lookup for active criteria
    active_dict = {c['criterion_id']: c for c in active_criteria}
    evaluated_dict = {c.criterion_id: c for c in eval_data.criteria}

    normalized_criteria = []
    
    for crit_id, crit_info in active_dict.items():
        if crit_id in evaluated_dict:
            score_data = evaluated_dict[crit_id]
            # Clip score between 0 and max_score
            max_score = crit_info['max_score']
            clipped_score = max(0, min(score_data.score, max_score))
            score_data.score = clipped_score
            score_data.max_score = max_score
            normalized_criteria.append(score_data)
        else:
            # Handle missing criterion by assigning 0
            normalized_criteria.append(CriterionScore(
                criterion_id=crit_id,
                score=0,
                max_score=crit_info['max_score'],
                justification="Criterion missing from evaluation.",
                evidence="None found."
            ))
            
    eval_data.criteria = normalized_criteria
    return eval_data
