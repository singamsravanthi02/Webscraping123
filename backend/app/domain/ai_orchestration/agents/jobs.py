from app.domain.ai_orchestration.agents.base import BaseAgent
import json

class JobMatchingAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "JobMatchingAgent"

    def match_jobs(self, user_id: int, student_profile: str, job_descriptions: list) -> list:
        prompt = f"""
        System: Act as an expert ATS (Applicant Tracking System) algorithm.
        Goal: Given the student profile and the list of job descriptions, score the match for each job from 0 to 100.
        
        Constraints:
        - Output strictly in valid JSON format, without markdown wrapping.
        - Ensure deterministic scoring (e.g., matching skills = +10, missing skills = -5).
        - DO NOT hallucinate matches.
        
        Student Profile:
        {student_profile}
        
        Jobs:
        {job_descriptions}
        
        Required Output JSON Schema:
        [
            {{
                "job_id": 1, 
                "match_score": 95, 
                "missing_skills": ["Docker", "AWS"], 
                "ai_summary": "Great match because...",
                "confidence_score": 0.95
            }}
        ]
        """
        
        response = self.run_inference(prompt, user_id, use_pro=False)  # Flash is fine for fast sorting
        try:
            scores = json.loads(response.strip('`').removeprefix('json').strip())
        except Exception:
            scores = []
        
        self.log_recommendation(
            user_id=user_id,
            action="job_matching",
            confidence=0.85,
            reasoning="Compared semantic overlap of skills in profile vs job requirements.",
            sources=["Student Profile", "Active Jobs List"]
        )
        return scores
