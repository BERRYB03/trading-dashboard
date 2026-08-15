import os
import requests
import json
from dotenv import load_dotenv
from core.gcp_secrets import get_secret

# Load local environment vars as a fallback for GCP_PROJECT_ID
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env')
load_dotenv(env_path)

class SentimentAnalyzer:
    def __init__(self):
        # Dynamically fetch from GCP Secret Manager
        self.api_key = get_secret('GEMINI_API_KEY')
        if not self.api_key or self.api_key == 'YOUR_GEMINI_API_KEY_HERE':
            raise ValueError("CRITICAL ERROR: GEMINI_API_KEY is missing from Secret Manager.")
        
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={self.api_key}"

    def analyze_event(self, context_data):
        system_instruction = (
            "You are a ruthless quantitative trading engine strategist. "
            "You must respond ONLY with a valid JSON object. "
            "No preamble, no markdown formatting, no explanations. "
            "The JSON must strictly follow this schema: {\"decision\": \"EXECUTE\" | \"HOLD\" | \"LIQUIDATE\", \"direction\": \"long\" | \"short\" | \"neutral\", \"confidence\": <0-100>}. "
            "Analyze the following isolated market event and determine the mathematical probability of price continuation vs mean-reversion."
        )
        
        # DYNAMIC RAG PROMPTING LOOP
        if 'historical_warning' in context_data:
            warning = context_data.pop('historical_warning')
            hist_dir = warning.get('direction', 'UNKNOWN').upper()
            hist_reason = warning.get('failure_reason', 'UNKNOWN')
            
            rag_block = (
                f"\n\nWARNING: Historical data shows that the last time you predicted a {hist_dir} "
                f"on a setup with these parameters, the trade hit a catastrophic stop-loss due to: {hist_reason}. "
                "Recalibrate your analysis, factor in this historical failure, and adjust your confidence score accordingly."
            )
            system_instruction += rag_block
            print("[*] Gemini Payload Intercepted: Injected Historical Failure Warning.")
        
        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": [{
                "parts": [{"text": json.dumps(context_data)}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
            
            raw_text = raw_text.strip()
            if raw_text.startswith("```json"): raw_text = raw_text[7:]
            if raw_text.startswith("```"): raw_text = raw_text[3:]
            if raw_text.endswith("```"): raw_text = raw_text[:-3]
                
            result = json.loads(raw_text.strip())
            
            if "decision" not in result or "confidence" not in result:
                 return {"decision": "HOLD", "direction": "neutral", "confidence": 0, "error": "Invalid schema returned."}
                 
            return result

        except Exception as e:
            print(f"[SENTIMENT ERROR] Exception during analysis: {e}")
            return {"decision": "HOLD", "direction": "neutral", "confidence": 0, "error": str(e)}

if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    mock_event = {
        "symbol": "DEXE_USDT",
        "event": "GAMMA_PARABOLIC_BREAKOUT",
        "24h_change": 22.5,
        "historical_warning": {
            "direction": "long",
            "failure_reason": "Hit -5% hard stop in 12 minutes"
        }
    }
    decision = analyzer.analyze_event(mock_event)
    print(json.dumps(decision, indent=2))
