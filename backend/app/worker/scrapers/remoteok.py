import httpx
import logging
from typing import List, Dict, Any
from .base import BaseJobScraper

logger = logging.getLogger(__name__)

class RemoteOKScraper(BaseJobScraper):
    def scrape(self, keyword: str = "", location: str = "") -> List[Dict[str, Any]]:
        """
        Scrapes job data from RemoteOK API.
        """
        logger.info("Scraping RemoteOK for jobs...")
        jobs = []
        url = "https://remoteok.com/api"
        
        try:
            # Note: RemoteOK requires a user-agent to avoid 403
            headers = {"User-Agent": "SPIP-JobAggregator/1.0"}
            with httpx.Client(timeout=10.0, headers=headers) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()
                
                # The first item is usually legal boilerplate, so we skip index 0
                for item in data[1:]:
                    title = item.get("position", "")
                    if keyword and keyword.lower() not in title.lower():
                        continue
                        
                    jobs.append({
                        "title": title,
                        "company": item.get("company", "Unknown"),
                        "location": item.get("location", "Remote"),
                        "salary_range": f"${item.get('salary_min', '')} - ${item.get('salary_max', '')}" if item.get('salary_min') else None,
                        "apply_link": item.get("apply_url", item.get("url", "")),
                        "raw_description": item.get("description", ""),
                        "employment_type": "Full-time",
                        "posted_date": item.get("date"),
                        "external_id": f"remoteok_{item.get('id')}"
                    })
        except Exception as e:
            logger.error(f"Failed to scrape RemoteOK: {e}")
            
        return jobs
