import httpx
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from .base import BaseKnowledgeAdapter

logger = logging.getLogger(__name__)

class JNTUHKnowledgeAdapter(BaseKnowledgeAdapter):
    def discover(self) -> List[str]:
        return [
            "https://jntuh.ac.in/academics"
        ]
        
    def fetch(self, url: str) -> str:
        # Note: JNTUH often requires verify=False for local dev if SSL is flaky
        with httpx.Client(timeout=15.0, verify=False) as client:
            res = client.get(url)
            res.raise_for_status()
            return res.text
            
    def clean(self, raw_content: str) -> str:
        soup = BeautifulSoup(raw_content, 'html.parser')
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        text = soup.get_text(separator='\n')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text
        
    def extract_metadata(self, url: str, raw_content: str) -> Dict[str, Any]:
        soup = BeautifulSoup(raw_content, 'html.parser')
        title = soup.title.string if soup.title else "JNTUH Academic Record"
        
        return {
            "title": title,
            "source": "JNTUH",
            "department": "University",
            "language": "en",
            "doc_type": "webpage"
        }
