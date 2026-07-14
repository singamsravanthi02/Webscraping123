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
        pass

class DummyLinkedInScraper(BaseJobScraper):
    def scrape(self, keyword: str, location: str) -> List[Dict[str, Any]]:
        logger.info(f"Dummy scraping LinkedIn for {keyword} in {location}")
        # In production, this would call Proxycurl or Apify
        return [
            {
                "title": f"Senior {keyword} Engineer",
                "company": "Tech Innovators Inc",
                "location": location,
                "salary_range": "$120k - $150k",
                "apply_link": "https://linkedin.com/jobs/view/123",
                "raw_description": "We are looking for an experienced software engineer with strong Python and React skills. Must have 5+ years of experience."
            }
        ]

class DummyNaukriScraper(BaseJobScraper):
    def scrape(self, keyword: str, location: str) -> List[Dict[str, Any]]:
        logger.info(f"Dummy scraping Naukri for {keyword} in {location}")
        return []
