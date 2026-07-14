from typing import List
from .base import BaseJobScraper
from .arbeitnow import ArbeitnowScraper
from .remoteok import RemoteOKScraper

from app.core.config import settings

def get_all_scrapers() -> List[BaseJobScraper]:
    """
    Returns a list of all active scraper instances based on configuration.
    """
    scrapers = []
    if settings.ARBEITNOW_ENABLED:
        scrapers.append(ArbeitnowScraper())
    if settings.REMOTEOK_ENABLED:
        scrapers.append(RemoteOKScraper())
    return scrapers
