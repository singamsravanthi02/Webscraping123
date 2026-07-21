from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

PROMPT_VERSION_RESUME = "ai-resume-v1"
PROMPT_VERSION_JOB_EXTRACT = "ai-job-extract-v1"
PROMPT_VERSION_JOB_QUERY = "ai-job-query-v1"
PROMPT_VERSION_INTERVIEW_TURN = "ai-interview-turn-v1"
PROMPT_VERSION_INTERVIEW_EVAL = "ai-interview-eval-v1"
PROMPT_VERSION_RAG = "ai-rag-v1"
PROMPT_VERSION_STUDY_MATERIAL = "ai-study-material-v1"
PROMPT_VERSION_QUESTION_GENERATION = "ai-question-generation-v1"
PROMPT_VERSION_CONTENT_GENERATION = "ai-content-generation-v1"
PROMPT_VERSION_JSON_REPAIR = "ai-json-repair-v1"


def _schema(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True)


def resume_analysis_prompt(resume_text: str) -> str:
    return f"""Extract the following information from this resume into JSON format:
{_schema({
    "technical_skills": [],
    "soft_skills": [],
    "years_of_experience": 0,
    "education_level": "",
    "projects": [],
    "overall_score": 0,
    "improvement_suggestions": [],
})}
Resume Text:
{resume_text}
"""


def job_extraction_prompt(raw_description: str) -> str:
    return f"""Extract structured data from the following job description.
Return ONLY valid JSON with the following keys:
{_schema({
    "skills": [],
    "eligibility": "Not specified",
    "ai_summary": "A great opportunity.",
})}

Description:
{raw_description[:3000]}
"""


def job_query_prompt(profile: Dict[str, Any]) -> str:
    return f"""Student Profile:
Skills:
{chr(10).join(profile.get("skills", []))}

Education:
{profile.get("education", "Not specified")}

Preferred Roles:
{chr(10).join(profile.get("preferred_roles", []))}

Preferred Locations:
{chr(10).join(profile.get("preferred_locations", []))}

Career Goal:
{profile.get("career_goal", "Not specified")}

Interview Scores:
{json.dumps(profile.get("interview_scores", {}))}

Learning Progress:
{json.dumps(profile.get("learning_progress", {}))}

Generate the best Google Job Search queries for this student.
Return valid JSON only in this exact format:
{_schema({"queries": ["query 1", "query 2"]})}

Generate 10-20 search queries. Focus on internships, fresher roles, remote roles, and location-aware roles when relevant.
"""


def job_chat_prompt(message: str, profile: Dict[str, Any], location: Optional[str] = None) -> str:
    return f"""User message: {message}
Location: {location or 'Any'}
Profile keywords: {', '.join(profile.get('keywords', []))}
Preferred roles: {', '.join(profile.get('preferred_roles', []))}
Convert the message into job search queries. Return valid JSON only:
{_schema({"queries": ["..."]})}
"""


def interview_system_prompt(interview_type: str, job_description: str = None, resume_text: str = None) -> str:
    prompt = f"You are a professional AI interviewer conducting a {interview_type} interview.\n"
    prompt += "Keep your responses concise, realistic, and conversational. Ask one question at a time.\n"
    if job_description:
        prompt += f"The job description is:\n{job_description}\n"
    if resume_text:
        prompt += f"The candidate's resume is:\n{resume_text}\n"
    if interview_type == "hr":
        prompt += "Focus on cultural fit, work history, and general HR questions."
    elif interview_type == "technical":
        prompt += "Focus on technical skills, architecture, and problem-solving."
    elif interview_type == "behavioral":
        prompt += "Focus on behavioral questions using the STAR method."
    elif interview_type == "coding":
        prompt += "Ask a coding question and evaluate their approach, logic, and code."
    prompt += "\nBegin the interview by introducing yourself briefly and asking the first question."
    return prompt


def interview_turn_prompt(system_prompt: str, chat_history: List[Dict[str, str]], new_message: str) -> str:
    transcript = "\n".join(f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history)
    return f"""Interview context:
{system_prompt}

Conversation so far:
{transcript}

Candidate response:
{new_message}

Reply as the interviewer with one concise, realistic next question or follow-up.
"""


def interview_evaluation_prompt(system_prompt: str, chat_history: List[Dict[str, str]]) -> str:
    transcript = "Interview Transcript:\n\n"
    for msg in chat_history:
        role_str = "Candidate" if msg["role"] == "user" else "Interviewer"
        transcript += f"{role_str}: {msg['content']}\n\n"
    return f"""You are an expert technical recruiter and interview evaluator.
Review the following interview transcript and provide a structured JSON evaluation.

The interview context was:
{system_prompt}

{transcript}

Provide the output exactly in this JSON structure:
{_schema({
    "confidence_score": 0,
    "communication_score": 0,
    "technical_score": 0,
    "problem_solving_score": 0,
    "overall_grade": 0,
    "feedback_summary": "string",
    "suggestions": ["string"],
    "strengths": ["string"],
    "weaknesses": ["string"],
    "recommended_topics": ["string"],
    "learning_plan": "string",
    "placement_readiness_contribution": 0,
})}

Only output valid JSON, without markdown blocks.
"""


def rag_prompt(query: str, context_str: str, history_text: str = "") -> str:
    return f"""You are an expert AI Learning Assistant. Your goal is to help students learn effectively.

Use the following retrieved context to answer the user's question.
Whenever you use information from the context, you MUST cite it using bracket notation, e.g., [1], [2].

CRITICAL RULE - HALLUCINATION PREVENTION:
If the context does not contain the answer, or if the context is empty, YOU MUST STRICTLY follow these instructions:
1. Set "confidence_level" to "Low".
2. Set "concise_explanation" exactly to: "I don't have enough information in the provided academic context to answer this question accurately. Please refer to your course materials or ask your professor."
3. Do NOT guess or invent facts.

Context:
{context_str}

Conversation history:
{history_text or "None"}

User question:
{query}

You MUST output your response EXACTLY in the following strict JSON format, without any markdown formatting around it:
{_schema({
    "concise_explanation": "Your detailed answer here, using markdown formatting for readability and including [1] citations.",
    "confidence_level": "High/Medium/Low",
    "related_topics": ["Topic 1", "Topic 2", "Topic 3"],
    "suggested_quiz": "A suggested title for a follow-up quiz",
    "suggested_flashcards": "A suggested topic for flashcards",
    "suggested_revision_notes": "A suggested topic for revision notes",
})}
"""


def study_material_prompt(material_type: str, topic: str, context_str: str) -> str:
    if material_type == "quiz":
        return f"""Generate a 5-question multiple choice quiz on the topic: '{topic}'.
Use this reference material if helpful:
{context_str}

Format the output in strict JSON like this:
{_schema({
    "material_type": "quiz",
    "topic": "{topic}",
    "questions": [
        {
            "question": "…",
            "options": ["A", "B", "C", "D"],
            "answer_index": 0,
            "explanation": "…",
        }
    ]
})}
"""
    if material_type == "flashcards":
        return f"""Generate 5 study flashcards on the topic: '{topic}'.
Use this reference material if helpful:
{context_str}

Format the output in strict JSON like this:
{_schema({
    "material_type": "flashcards",
    "topic": "{topic}",
    "flashcards": [
        {"front": "Term or Question", "back": "Definition or Answer"}
    ],
    "summary_markdown": "",
    "key_points": [],
    "cheat_sheet": ""
})}
"""
    if material_type == "summary":
        return f"""Provide a comprehensive markdown summary of the topic: '{topic}'.
Make it beautiful and easy to read. Use headings, bullet points, and highlight key terms.
Use this reference material:
{context_str}

Return strict JSON with this shape:
{_schema({
    "material_type": "summary",
    "topic": "{topic}",
    "summary_markdown": "A concise markdown summary.",
    "key_points": ["Key point 1", "Key point 2"],
    "flashcards": [],
    "questions": [],
    "cheat_sheet": "Short cheat sheet."
})}
"""
    return "Invalid material type requested."


def question_generation_prompt(context_text: str, document_metadata: Dict[str, Any]) -> str:
    schema = _schema({
        "topic": "Extracted Topic",
        "subject": "Extracted Subject",
        "type": "mcq",
        "difficulty": 5,
        "interview_difficulty": 5,
        "company_difficulty": 5,
        "bloom_level": "Apply",
        "content": "The actual question text",
        "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
        "correct_answer": "A",
        "detailed_explanation": "Step by step reasoning",
        "hints": ["Hint 1", "Hint 2"],
        "common_mistakes": ["Mistake 1"],
        "company_tags": ["TCS", "Infosys"],
        "placement_relevance": 8,
        "estimated_time": 60,
        "marks": 1.0,
    })
    return (
        "System: Act as an Engineering Professor (20+ years), Placement Trainer, and Technical Interviewer.\n"
        "Goal: Generate exactly 3 strict questions (1 Easy, 1 Medium, 1 Hard) strictly based on the provided RAG Context.\n\n"
        "Constraints:\n"
        "- Never use outside knowledge. If the context is insufficient, return {\"questions\": []}.\n"
        '- Output strictly as a valid JSON object with a single top-level "questions" array. DO NOT wrap in markdown ticks like ```json.\n\n'
        f"Document Context:\n{context_text}\n\n"
        f"Metadata:\n{json.dumps(document_metadata)}\n\n"
        f"Output Schema for each object:\n{schema}\n"
        f"The final output must be:\n{_schema({'questions': []})}\n"
    )


def content_generation_prompt(context_text: str) -> str:
    schema = _schema({
        "flashcards": [
            {"front": "Concept Name", "back": "Definition or key point"}
        ],
        "revision_notes": "Concise markdown summary with short bullet points only.",
        "cheat_sheet": "Concise markdown cheat sheet with only the essential points.",
    })
    return (
        "System: Act as an elite educational content creator.\n"
        "Goal: Transform the provided RAG Context into structured learning resources.\n\n"
        "Constraints:\n"
        "- Strictly use the provided context.\n"
        "- Generate exactly 3 flashcards.\n"
        "- Keep revision notes and cheat sheet concise.\n"
        "- Output strictly as valid JSON, NO markdown wrappers.\n\n"
        f"Context:\n{context_text[:12000]}\n\n"
        f"Output Schema:\n{schema}\n"
    )


def repair_json_prompt(schema_name: str, raw_response: str, schema_json: Dict[str, Any]) -> str:
    return f"""The previous response did not parse as valid JSON for schema {schema_name}.
Fix it and return ONLY valid JSON with this schema:
{_schema(schema_json)}

Broken response:
{raw_response}
"""
