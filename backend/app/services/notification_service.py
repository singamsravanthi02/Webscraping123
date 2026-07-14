from abc import ABC, abstractmethod

class BaseNotificationService(ABC):
    @abstractmethod
    def send_notification(self, user_id: str, title: str, message: str) -> None:
        pass

class AppNotificationService(BaseNotificationService):
    def send_notification(self, user_id: str, title: str, message: str) -> None:
        # To be implemented: persist to db or send via websocket
        pass
