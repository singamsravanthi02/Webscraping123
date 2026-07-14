import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    logger.info("Validating configuration injection...")
    from app.core.config import settings
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    
    logger.info("Validating gateway initialization...")
    from app.domain.ai_orchestration.gateway import gateway
    logger.info("Gateway initialized successfully.")
    
    logger.info("Validating qdrant initialization...")
    from app.domain.learning.services.qdrant_service import qdrant_client
    logger.info("Qdrant service module imported successfully.")
    
    logger.info("Validating email service initialization...")
    from app.services.email_service import email_service
    logger.info(f"Email service initialized: {email_service.__class__.__name__}")
    
    logger.info("Validating job scraper factory...")
    from app.worker.scrapers.factory import get_all_scrapers
    scrapers = get_all_scrapers()
    logger.info(f"Loaded scrapers: {[s.__class__.__name__ for s in scrapers]}")

    logger.info("Validation successful. The app started without missing optional keys.")
    sys.exit(0)
except Exception as e:
    logger.error(f"Startup validation failed: {e}")
    sys.exit(1)
