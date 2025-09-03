from abc import ABC, abstractmethod


class CloudService(ABC):

    @abstractmethod
    def authenticate(self):
        """
        Authenticates the cloud service
        """
        ...

    @abstractmethod
    def unauthenticate(self):
        """
        Unauthenticated the cloud service
        """
        ...

    @abstractmethod
    def get_secret(self, secret_name: str):
        """
        Retrieves a secret from the cloud service
        """
        ...

    @abstractmethod
    def retrieve_cloud_attributes(self, attributes: dict):
        """
        Retrieves attributes from the cloud service
        """
        ...

    @abstractmethod
    def save_file_to_cloud_storage(
        self, file_path: str, destination: str, object_name: str = None
    ):
        """
        Saves a file to cloud storage
        """
        ...

    @abstractmethod
    def list_files_in_cloud_storage(self):
        """
        Lists files in cloud storage
        """
        ...

    @abstractmethod
    def get_cloud_storage_by_name(self, name: str):
        """
        Gets the cloud storage
        """
        ...
