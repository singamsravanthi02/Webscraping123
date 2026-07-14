import httpx
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from .base import BaseKnowledgeAdapter

logger = logging.getLogger(__name__)

class SreyasKnowledgeAdapter(BaseKnowledgeAdapter):
    def discover(self) -> List[str]:
        # For V1, we target specific high-value public pages.
        # In a full crawl, this would recursively find links within domain constraints.
        return [
            "https://sreyas.ac.in/academics/departments/cse/",
            "https://sreyas.ac.in/placements/"
        ]
        
    def fetch(self, url: str) -> str:
        with httpx.Client(timeout=10.0) as client:
            res = client.get(url)
            res.raise_for_status()
            return res.text
            
    def clean(self, raw_content: str) -> str:
        soup = BeautifulSoup(raw_content, 'html.parser')
        
        # Remove nav, footer, scripts
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
            
        text = soup.get_text(separator='\n')
        
        # Clean whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
        
    def extract_metadata(self, url: str, raw_content: str) -> Dict[str, Any]:
        soup = BeautifulSoup(raw_content, 'html.parser')
        title = soup.title.string if soup.title else url
        
        dept = "General"
        if "cse" in url.lower():
            dept = "CSE"
            
        return {
            "title": title,
            "source": "SREYAS",
            "department": dept,
            "language": "en",
            "doc_type": "webpage"
        }
