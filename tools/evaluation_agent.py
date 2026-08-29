import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def evaluate_supplier(supplier_name: str, extracted_text: str, active_criteria: list) -> dict:
    """
    Evaluates a single supplier's document against active criteria using OpenRouter.
    Returns a dictionary representing the parsed JSON.
    """
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY")
    )
    
    # Construct the criteria description for the prompt
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
        model="liquid/lfm-2.5-2.6b:free", # Default OpenRouter model
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    
    return json.loads(response.choices[0].message.content)
