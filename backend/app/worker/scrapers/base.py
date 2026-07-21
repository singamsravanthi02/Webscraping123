from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseJobScraper(ABC):
    def __init__(self):
        self.jobs_scraped = 0
        
    @abstractmethod
    def scrape(self, keyword: str, location: str) -> List[Dict[str, Any]]:
        """
        Scrapes job data from the source and returns a list of dictionaries.
        Expected keys: title, company, location, salary_range, apply_link, raw_description.
        """
        raise NotImplementedError
