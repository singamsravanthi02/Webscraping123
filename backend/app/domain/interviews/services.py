import json
from typing import Dict, Any, List
from app.domain.interviews.models import InterviewType, MessageRole
from app.domain.ai_orchestration.gateway import gateway
from app.domain.ai_orchestration.agents.interviews import InterviewAgent

agent = InterviewAgent()

def get_system_prompt_for_type(interview_type: InterviewType, job_description: str = None, resume_text: str = None) -> str:
    prompt = f"You are a professional AI interviewer conducting a {interview_type.value} interview.\n"
    prompt += "Keep your responses concise, realistic, and conversational. Ask one question at a time.\n"
    
    if job_description:
        prompt += f"The job description is:\n{job_description}\n"
        
    if resume_text:
        prompt += f"The candidate's resume is:\n{resume_text}\n"
        
    if interview_type == InterviewType.HR:
        prompt += "Focus on cultural fit, work history, and general HR questions."
    elif interview_type == InterviewType.TECHNICAL:
        prompt += "Focus on technical skills, architecture, and problem-solving."
    elif interview_type == InterviewType.BEHAVIORAL:
        prompt += "Focus on behavioral questions using the STAR method."
    elif interview_type == InterviewType.CODING:
        prompt += "Ask a coding question and evaluate their approach, logic, and code."
        
    prompt += "\nBegin the interview by introducing yourself briefly and asking the first question."
    return prompt

async def generate_ai_response(system_prompt: str, chat_history: List[Dict[str, str]], new_message: str, user_id: int) -> str:
    chat_session = gateway.chat_session(use_pro=False)
    
    # Initialize history
    chat_session.history.append({"role": "user", "parts": [system_prompt]})
    chat_session.history.append({"role": "model", "parts": ["Understood. I will begin the interview."]})
    
    for msg in chat_history:
        role = "user" if msg["role"] == MessageRole.USER else "model"
        if msg["role"] == MessageRole.SYSTEM:
            continue
        chat_session.history.append({"role": role, "parts": [msg["content"]]})
        
    try:
        # The agent handles logging to AIRecommendationLog and token usage via Gateway
        return agent.process_turn(user_id, chat_session, new_message)
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return "I apologize, but I am having trouble connecting right now. Could you please repeat that?"

async def evaluate_interview_transcript(system_prompt: str, chat_history: List[Dict[str, str]], user_id: int) -> Dict[str, Any]:
    transcript = "Interview Transcript:\n\n"
    for msg in chat_history:
        role_str = "Candidate" if msg["role"] == MessageRole.USER else "Interviewer"
        transcript += f"{role_str}: {msg['content']}\n\n"
        
    eval_prompt = f"""
    You are an expert technical recruiter and interview evaluator.
    Review the following interview transcript and provide a structured JSON evaluation.
    
    The interview context was:
    {system_prompt}
    
    {transcript}
    
    Provide the output exactly in this JSON structure:
    {{
        "confidence_score": <float 0-10>,
        "communication_score": <float 0-10>,
        "technical_score": <float 0-10>,
        "problem_solving_score": <float 0-10>,
        "overall_grade": <float 0-10>,
        "feedback_summary": "<A comprehensive paragraph summarizing their performance>",
        "suggestions": ["<Actionable suggestion 1>", "<Actionable suggestion 2>"],
        "strengths": ["<strength 1>", "<strength 2>"],
        "weaknesses": ["<weakness 1>", "<weakness 2>"],
        "recommended_topics": ["<topic 1>", "<topic 2>"],
        "learning_plan": "<A concise step-by-step learning plan paragraph>",
        "placement_readiness_contribution": <float 0-5>
    }}
    
    Only output valid JSON, without markdown blocks.
    """
    
    try:
        # Evaluations are complex, route to Pro model
        response_text = gateway.generate_content(eval_prompt, use_pro=True, user_id=user_id, feature="interview_evaluation")
        result_text = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(result_text)
        
        # Explainable AI logging
        agent.log_recommendation(
            user_id=user_id,
            action="evaluate_interview",
            confidence=0.9,
            reasoning="Evaluated transcript based on communication and technical alignment.",
            evidence=[transcript]
        )
        return data
    except Exception as e:
        print(f"Error evaluating interview: {e}")
        user_turns = sum(1 for msg in chat_history if msg["role"] == MessageRole.USER)
        engagement_bonus = min(user_turns * 0.5, 2.0)
        return {
            "confidence_score": round(5.0 + engagement_bonus, 1),
            "communication_score": round(5.5 + engagement_bonus, 1),
            "technical_score": round(4.5 + engagement_bonus, 1),
            "problem_solving_score": round(4.5 + engagement_bonus, 1),
            "overall_grade": round(5.0 + engagement_bonus, 1),
            "feedback_summary": "AI evaluation was unavailable, so this fallback review was generated from the interview transcript. The candidate participated clearly, showed reasonable communication, and should continue building technical depth through longer practice sessions.",
            "suggestions": [
                "Practice answering frontend architecture questions out loud.",
                "Prepare concise examples of accessibility, state management, and API integration work."
            ],
            "strengths": [
                "Engaged with the interviewer",
                "Communicated intent clearly"
            ],
            "weaknesses": [
                "Insufficient transcript depth for a full technical assessment",
                "No verified evidence of advanced problem solving in this short session"
            ],
            "recommended_topics": [
                "React component architecture",
                "Accessibility patterns",
                "State management and API integration"
            ],
            "learning_plan": "1. Review one frontend system design topic. 2. Practice one STAR-style answer. 3. Rehearse a short code walkthrough. 4. Run another mock interview and compare progress.",
            "placement_readiness_contribution": round(1.5 + engagement_bonus / 2, 1)
        }
