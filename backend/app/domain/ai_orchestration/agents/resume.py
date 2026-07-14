from app.domain.ai_orchestration.agents.base import BaseAgent
import json

class ResumeAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "ResumeAnalysisAgent"

    def analyze_resume(self, user_id: int, resume_text: str) -> dict:
        prompt = f"""
        Extract the following information from this resume into JSON format:
        {{
            "technical_skills": [],
            "soft_skills": [],
            "years_of_experience": 0,
            "education_level": "",
            "overall_score": 0-100,
            "improvement_suggestions": []
        }}
        Resume Text:
        {resume_text}
        """
        
        response = self.run_inference(prompt, user_id, use_pro=True) # Use Pro for complex extraction
        
        # In production, use robust JSON parsing/regex to extract the block
        try:
            # Strip markdown code blocks if any
            clean_json = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            self.log_recommendation(
                user_id=user_id,
                action="resume_analysis",
                confidence=0.9,
                reasoning="Extracted entities using Gemini 1.5 Pro structured output.",
                next_actions=data.get("improvement_suggestions", [])
            )
            return data
        except Exception:
            return {"error": "Failed to parse resume"}
