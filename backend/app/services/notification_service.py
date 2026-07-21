from abc import ABC, abstractmethod

class BaseNotificationService(ABC):
    @abstractmethod
    def send_notification(self, user_id: str, title: str, message: str) -> None:
        raise NotImplementedError

class AppNotificationService(BaseNotificationService):
    def send_notification(self, user_id: str, title: str, message: str) -> None:
        logger.info("Notification for user %s: %s", user_id, title)
