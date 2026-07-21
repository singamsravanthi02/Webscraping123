import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BaseKnowledgeAdapter(ABC):
    """
    Abstract base class for all Knowledge Source Adapters.
    """
    
    @abstractmethod
    def discover(self) -> List[str]:
        """Finds all URLs or entry points to process."""
        raise NotImplementedError
        
    @abstractmethod
    def fetch(self, url: str) -> str:
        """Fetches raw content from a given URL."""
        raise NotImplementedError
        
    @abstractmethod
    def clean(self, raw_content: str) -> str:
        """Removes boilerplate, HTML tags, and normalizes text."""
        raise NotImplementedError
        
    @abstractmethod
    def extract_metadata(self, url: str, raw_content: str) -> Dict[str, Any]:
        """Extracts title, department, etc."""
        raise NotImplementedError
        
    def sync(self) -> List[Dict[str, Any]]:
        """
        Main orchestration method:
        1. Discover URLs
        2. Fetch & Clean
        3. Extract Metadata
        4. Return structured documents for the pipeline
        """
        documents = []
        urls = self.discover()
        for url in urls:
            try:
                raw = self.fetch(url)
                cleaned = self.clean(raw)
                meta = self.extract_metadata(url, raw)
                
                documents.append({
                    "url": url,
                    "raw_content": raw,
                    "cleaned_content": cleaned,
                    "metadata": meta
                })
            except Exception as e:
                # Log error and continue
                logger.warning("Error syncing %s: %s", url, e)
                
        return documents
