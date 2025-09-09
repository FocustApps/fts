from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient

from fts.common.service_connections.cloud_service import CloudService


class AzureCloudService(CloudService):
    """
    AzureCloudService is a class that provides methods to interact with Azure cloud services.

    Methods
    -------
    authenticate():
        Authenticates the Azure cloud service using DefaultAzureCredential.

    unauthenticate():
        Closes the DefaultAzureCredential session.

    get_secret(vault_url: str, secret_name: str):
        Retrieves a secret from the Azure Key Vault.

    save_report_to_cloud(file_path: str, storage_url: str):
        Placeholder method to save a report to Azure cloud storage.

    retrieve_cloud_attributes(account_uri: str, account_key: str) -> CosmosClient:
        Retrieves cloud attributes using the CosmosClient.

    save_file_to_cloud_storage(file_path: str, blob_name: str, storage_account_url: str, container_name: str):
        Saves a file to Azure Blob Storage.
    """

    def authenticate(self):
        """
        Authenticates the Azure cloud service
        """
        return DefaultAzureCredential()

    def unauthenticate(self):
        return DefaultAzureCredential().close()

    def get_secret(self, vault_url: str, secret_name: str):
        return (
            SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
            .get_secret(secret_name)
            .value
        )

    def save_report_to_cloud(self, file_path: str, storage_url: str):
        pass

    def retrieve_cloud_attributes(
        self, account_uri: str, account_key: str
    ) -> CosmosClient:
        return CosmosClient(url=account_uri, credential=account_key)

    def save_file_to_cloud_storage(
        self,
        file_path: str,
        blob_name: str,
        storage_account_url: str,
        container_name: str,
    ):

        # Create the BlobServiceClient object
        blob_service_client = BlobServiceClient(
            account_url=f"https://{storage_account_url}.blob.core.windows.net",
            credential=DefaultAzureCredential(),
        )

        # Get the BlobClient object
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_name
        )

        with open(file_path, "rb") as datafile_path:
            data = datafile_path.read()
        return blob_client.upload_blob(data=data)

    def get_cloud_storage_by_name(self, name: str): ...
