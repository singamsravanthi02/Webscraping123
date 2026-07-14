import json
from typing import List, Dict, Any
from .qdrant_service import search_documents
from app.domain.ai_orchestration.gateway import gateway
from app.domain.ai_orchestration.agents.rag import RAGAgent

agent = RAGAgent()

async def chat_with_context(query: str, chat_history: List[Dict[str, str]], subject: str = None, user_id: int = None) -> Dict[str, Any]:
    """
    RAG-enabled chat. Fetches context, prompts Gemini, and parses out the response + citations.
    """
    # 1. Retrieve Context
    search_query = query
    if subject:
        search_query = f"{subject}: {query}"
        
    retrieved_docs = search_documents(search_query, limit=4)
    
    context_str = ""
    citations_meta = []
    
    for i, doc in enumerate(retrieved_docs):
        citation_id = f"[{i+1}]"
        context_str += f"{citation_id} Source: {doc['title']}\nContent: {doc['text']}\n\n"
        citations_meta.append({
            "id": i+1,
            "title": doc['title'],
            "type": doc['source_type']
        })
        
    # 2. Build Prompt
    system_prompt = f"""
    You are an expert AI Learning Assistant. Your goal is to help students learn effectively.
    
    Use the following retrieved context to answer the user's question. 
    Whenever you use information from the context, you MUST cite it using the bracket notation, e.g., [1], [2].
    
    CRITICAL RULE - HALLUCINATION PREVENTION:
    If the context does not contain the answer, or if the context is empty, YOU MUST STRICTLY follow these instructions:
    1. Set "confidence_level" to "Low".
    2. Set "concise_explanation" exactly to: "I don't have enough information in the provided academic context to answer this question accurately. Please refer to your course materials or ask your professor."
    3. Do NOT guess or invent facts.
    
    Context:
    {context_str}
    
    You MUST output your response EXACTLY in the following strict JSON format, without any markdown formatting around it (no ```json):
    {{
        "concise_explanation": "Your detailed answer here, using markdown formatting for readability and including [1] citations.",
        "confidence_level": "High/Medium/Low",
        "related_topics": ["Topic 1", "Topic 2", "Topic 3"],
        "suggested_quiz": "A suggested title for a follow-up quiz",
        "suggested_flashcards": "A suggested topic for flashcards",
        "suggested_revision_notes": "A suggested topic for revision notes"
    }}
    """
    
    chat_session = gateway.chat_session(use_pro=False)
    chat_session.history.append({"role": "user", "parts": [system_prompt]})
    chat_session.history.append({"role": "model", "parts": ["Understood."]})
    
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        if msg["role"] != "system":
            chat_session.history.append({"role": role, "parts": [msg["content"]]})
            
    try:
        if user_id:
            response_text = agent.process_rag_chat(user_id, chat_session, query, citations_meta)
        else:
            response = chat_session.send_message(query)
            response_text = response.text
            
        # Try to parse the JSON
        parsed = {}
        try:
            # clean up markdown backticks if any
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean_text)
        except Exception as parse_e:
            print(f"Failed to parse JSON response: {parse_e}")
            parsed = {
                "concise_explanation": response_text,
                "confidence_level": "Medium",
                "related_topics": []
            }
            
        return {
            "content": json.dumps(parsed), # Store as a JSON string in content field for DB
            "citations": citations_meta if retrieved_docs else []
        }
    except Exception as e:
        print(f"Error generating AI response: {e}")
        error_resp = {
            "concise_explanation": "I'm sorry, I'm having trouble processing that right now. Please try again.",
            "confidence_level": "Low",
            "related_topics": []
        }
        return {
            "content": json.dumps(error_resp),
            "citations": []
        }

async def generate_study_material(material_type: str, topic: str, chat_history: List[Dict[str, str]] = None, user_id: int = None) -> str:
    """
    Generates specific study materials (quiz, summary, flashcards) based on a topic or recent chat context.
    """
    context_docs = search_documents(topic, limit=5)
    context_str = "\n".join([f"- {doc['text']}" for doc in context_docs])
    
    if material_type == "quiz":
        prompt = f"""
        Generate a 5-question multiple choice quiz on the topic: '{topic}'.
        Use this reference material if helpful:
        {context_str}
        
        Format the output in strict JSON like this:
        {{
            "questions": [
                {{
                    "question": "...",
                    "options": ["A", "B", "C", "D"],
                    "answer_index": 0,
                    "explanation": "..."
                }}
            ]
        }}
        """
    elif material_type == "flashcards":
        prompt = f"""
        Generate 5 study flashcards on the topic: '{topic}'.
        Use this reference material if helpful:
        {context_str}
        
        Format the output in strict JSON like this:
        {{
            "flashcards": [
                {{
                    "front": "Term or Question",
                    "back": "Definition or Answer"
                }}
            ]
        }}
        """
    elif material_type == "summary":
        prompt = f"""
        Provide a comprehensive markdown summary of the topic: '{topic}'.
        Make it beautiful and easy to read. Use headings, bullet points, and highlight key terms.
        Use this reference material:
        {context_str}
        """
    else:
        return "Invalid material type requested."
        
    try:
        text = gateway.generate_content(prompt, use_pro=False, user_id=user_id, feature=f"generate_{material_type}")
        
        # If JSON requested, try to clean it
        if material_type in ["quiz", "flashcards"]:
            text = text.replace("```json", "").replace("```", "").strip()
            
        return text
    except Exception as e:
        print(f"Error generating material: {e}")
        return "Failed to generate study material."
