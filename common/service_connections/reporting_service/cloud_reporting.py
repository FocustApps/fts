import os
import logging
from datetime import datetime

from common.service_connections.cloud_service import CloudService
from common.service_connections.reporting_service import ReportingService


class CloudReportingService(ReportingService):

    def __init__(self, cloud_service: CloudService):
        self.cloud_service = cloud_service

    def send_report(
        self, file_path: str, destination: str, destination_path: str | None = None
    ) -> str:
        timestamp = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
        file_name = os.path.basename(file_path)
        new_file_name = f"{timestamp}-{file_name}"
        destination_path_with_file = (
            f"{destination_path}/{new_file_name}" if destination_path else new_file_name
        )
        logging.info(f"Uploading file to cloud storage: {new_file_name}")
        self.cloud_service.save_file_to_cloud_storage(
            file_path=file_path,
            destination=destination,
            object_name=destination_path_with_file,
        )
        return destination

    def get_reports_from_storage(self, directory: str) -> list:
        return self.cloud_service.list_files_in_cloud_storage(directory)
