import os
import sys

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import models so SQLAlchemy metadata is populated for any schema access.
from app.domain.users import models as user_models  # noqa: F401
from app.domain.jobs import models as job_models  # noqa: F401
from app.domain.assessments import models as assessment_models  # noqa: F401
from app.domain.interviews import models as interview_models  # noqa: F401
from app.domain.learning import models as learning_models  # noqa: F401
from app.domain.notifications import models as notification_models  # noqa: F401
from app.domain.ai_orchestration import models as ai_models  # noqa: F401
from app.domain.audit_logs import models as audit_models  # noqa: F401
from app.domain.knowledge import models as knowledge_models  # noqa: F401
from app.db.session import SessionLocal


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
