import os
import shutil
from datetime import datetime

from service_connections.reporting_service import ReportingService


class LocalReportingService(ReportingService):

    def send_report(self, file_path: str, file_destination: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file at {file_path} does not exist.")

        if not os.path.exists(file_destination):
            os.makedirs(file_destination)

        timestamp = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
        file_name = os.path.basename(file_path)
        new_file_name = f"{timestamp}-{file_name}"
        new_file_path = os.path.join(file_destination, new_file_name)

        shutil.copy(file_path, new_file_path)

        return new_file_path

    def get_reports_from_storage(self, storage_path: str):
        if not os.path.exists(storage_path):
            raise FileNotFoundError(f"The directory at {storage_path} does not exist.")

        return os.listdir(storage_path)