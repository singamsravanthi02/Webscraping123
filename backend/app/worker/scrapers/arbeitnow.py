import httpx
import logging
from typing import List, Dict, Any
from .base import BaseJobScraper

logger = logging.getLogger(__name__)

class ArbeitnowScraper(BaseJobScraper):
    def scrape(self, keyword: str = "", location: str = "") -> List[Dict[str, Any]]:
        """
        Scrapes job data from Arbeitnow API.
        Arbeitnow API is public and does not require an API key.
        """
        logger.info("Scraping Arbeitnow for jobs...")
        jobs = []
        url = "https://www.arbeitnow.com/api/job-board-api"
        
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get("data", []):
                    # Basic filtering for MVP
                    title = item.get("title", "")
                    if keyword and keyword.lower() not in title.lower():
                        continue
                        
                    jobs.append({
                        "title": title,
                        "company": item.get("company_name", "Unknown"),
                        "location": item.get("location", "Remote"),
                        "salary_range": None, # Arbeitnow rarely provides this structured
                        "apply_link": item.get("url", ""),
                        "raw_description": item.get("description", ""),
                        "employment_type": "Full-time",
                        "posted_date": item.get("created_at"),
                        "external_id": f"arbeitnow_{item.get('slug')}"
                    })
        except Exception as e:
            logger.error(f"Failed to scrape Arbeitnow: {e}")
            
        return jobs
