import boto3
from botocore.exceptions import ClientError

import logging
from fts.common.service_connections.cloud_service import CloudService


class AwsCloudService(CloudService):
    """
    AwsCloudService is a class that provides methods to interact with AWS cloud services.

    Methods:
        authenticate():
            Authenticates the AWS cloud service.

        unauthenticate():
            Unauthenticates the AWS cloud service.

        get_secret(secret_name: str):
            Retrieves a secret from AWS Secrets Manager.
            :param secret_name: The name of the secret to retrieve.

        retrieve_cloud_attributes(attributes: dict):
            Retrieves specified cloud attributes.
            :param attributes: A dictionary of attributes to retrieve.

        save_file_to_cloud_storage(file_path: str, destination: str, object_name: str = None):
            Uploads a file to an S3 bucket.
            :param file_path: The path to the file to upload.
            :param destination: The S3 bucket to upload to.
            :param object_name: The S3 object name. If not specified, the file name is used.
            :return: True if the file was uploaded successfully, else False.

        list_files_in_cloud_storage(bucket_name: str):
            Lists all files
    """

    def authenticate(self):
        """
        Authenticates the AWS cloud service
        """
        pass

    def unauthenticate(self):
        pass

    def get_secret(self, secret_name: str):
        pass

    def retrieve_cloud_attributes(self, attributes: dict):
        pass

    def save_file_to_cloud_storage(
        self, file_path: str, destination: str, object_name: str = None
    ):
        """Upload a file to an S3 bucket
        :param file_name: File to upload
        :param bucket: Bucket to upload to
        :param object_name: S3 object name. If not specified then file_name is used
        :return: True if file was uploaded, else False
        """

        # If S3 object_name was not specified, use file_name
        if object_name is None:
            object_name = os.path.basename(file_name)

        # Upload the file
        s3_client = boto3.client("s3")
        try:
            s3_client.upload_file(file_path, destination, object_name)
        except ClientError as e:
            logging.error(e)
            return False

        return True

    def list_files_in_cloud_storage(self, bucket_name: str):
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(bucket_name)
        files = []
        for obj in bucket.objects.all():
            files.append(obj.key)
        return files

    def get_cloud_storage_by_name(self, name: str):
        s3 = boto3.resource("s3")

        for bucket in s3.buckets.all():
            if bucket.name == name:
                return bucket
