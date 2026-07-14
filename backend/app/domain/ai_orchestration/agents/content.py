from app.domain.ai_orchestration.agents.base import BaseAgent
import json
import logging

logger = logging.getLogger(__name__)

class QuestionGenerationAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "QuestionGenerationAgent"

    def generate_questions(self, user_id: int, context_text: str, document_metadata: dict) -> list:
        prompt = f"""
        System: Act as an Engineering Professor (20+ years), Placement Trainer, and Technical Interviewer.
        Goal: Generate exactly 3 strict questions (1 Easy, 1 Medium, 1 Hard) strictly based on the provided RAG Context.
        
        Constraints:
        - Never use outside knowledge. If the context is insufficient, return an empty array [].
        - Output strictly as a valid JSON array. DO NOT wrap in markdown ticks like ```json.
        
        Document Context:
        {context_text}
        
        Metadata:
        {json.dumps(document_metadata)}
        
        Output Schema for each object:
        {{
            "topic": "Extracted Topic",
            "subject": "Extracted Subject",
            "type": "mcq", // or "subjective"
            "difficulty": 5, // 1-10
            "interview_difficulty": 5, // 1-10
            "company_difficulty": 5, // 1-10
            "bloom_level": "Apply", // e.g. Remember, Understand, Apply, Analyze, Evaluate, Create
            "content": "The actual question text",
            "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, // Only if mcq
            "correct_answer": "A",
            "detailed_explanation": "Step by step reasoning",
            "hints": ["Hint 1", "Hint 2"],
            "common_mistakes": ["Mistake 1"],
            "company_tags": ["TCS", "Infosys"], // If applicable based on context
            "placement_relevance": 8, // 1-10
            "estimated_time": 60, // seconds
            "marks": 1.0
        }}
        """
        
        # Use Pro model for generation tasks as it requires deep reasoning
        response_text = self.run_inference(prompt, user_id, use_pro=True)
        
        try:
            questions = json.loads(response_text.strip('`').removeprefix('json').strip())
            return questions
        except Exception as e:
            logger.error(f"Failed to parse generated questions: {e}")
            return []


class ContentGenerationAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "ContentGenerationAgent"

    def generate_learning_resources(self, user_id: int, context_text: str, document_metadata: dict) -> dict:
        prompt = f"""
        System: Act as an elite educational content creator.
        Goal: Transform the provided RAG Context into structured learning resources.
        
        Constraints:
        - Strictly use the provided context.
        - Output strictly as valid JSON, NO markdown wrappers.
        
        Context:
        {context_text}
        
        Output Schema:
        {{
            "flashcards": [
                {{"front": "Concept Name", "back": "Definition or key point"}}
            ],
            "revision_notes": "Markdown string containing a concise 5-minute revision summary with bullet points.",
            "cheat_sheet": "Markdown string containing formulas, syntax, or key algorithms."
        }}
        """
        
        response_text = self.run_inference(prompt, user_id, use_pro=True)
        
        try:
            resources = json.loads(response_text.strip('`').removeprefix('json').strip())
            return resources
        except Exception as e:
            logger.error(f"Failed to parse generated resources: {e}")
            return {}
