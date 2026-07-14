from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class DomainException(Exception):
    def __init__(self, name: str, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.name = name
        self.detail = detail
        self.status_code = status_code

class ResourceNotFoundException(DomainException):
    def __init__(self, resource_name: str, resource_id: str):
        super().__init__(
            name="resource_not_found",
            detail=f"{resource_name} with id {resource_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

class UnauthorizedException(DomainException):
    def __init__(self, detail: str = "Unauthorized access"):
        super().__init__(
            name="unauthorized",
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED
        )

async def domain_exception_handler(request: Request, exc: DomainException):
    logger.error(f"Domain exception on {request.url.path}: {exc.name} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.name, "detail": exc.detail}
    )
