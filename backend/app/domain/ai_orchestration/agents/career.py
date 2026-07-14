from app.domain.ai_orchestration.agents.base import BaseAgent

class CareerCoachAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "CareerCoachAgent"

    def generate_weekly_plan(self, user_id: int, memory_data: dict) -> str:
        prompt = f"""
        System: Act as an expert, strict, and precise personalized career coach for engineering students.
        Goal: Based ONLY on this student's memory, generate a highly structured 5-day adaptive learning plan.
        
        Constraints:
        - NEVER hallucinate external facts or tools.
        - NEVER recommend paid services.
        - MUST focus heavily on the student's listed weak topics.
        - Output strictly in valid Markdown formatting.
        
        Student Memory Context:
        {memory_data}
        
        Required Output Structure:
        - ## Goal of the Week
        - ## 3 Actionable Steps
        - ## Daily Schedule (Day 1 to 5)
        - ## Confidence Building Exercises
        - **Confidence Score**: [Rate the feasibility of this plan from 0.0 to 1.0]
        """
        
        response = self.run_inference(prompt, user_id, use_pro=True)
        
        self.log_recommendation(
            user_id=user_id,
            action="generate_weekly_plan",
            confidence=0.88,
            reasoning="Synthesized weak topics and career goals to build actionable plan.",
            sources=["Student AI Memory Table"]
        )
        
        return response
