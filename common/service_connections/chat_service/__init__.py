from abc import ABC, abstractmethod
    

class ChatService(ABC):

    @abstractmethod
    def send_message(self, message: str):
        """
        Sends a message to the chat service
        """
        ...
