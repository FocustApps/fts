from abc import ABC, abstractmethod
from typing import List
import xml.etree.ElementTree as ET

class ReportingService(ABC):

    @abstractmethod
    def send_report(
        self, file_path: str, destination: str, destination_path: str | None = None
    ) -> str: ...

    @abstractmethod
    def get_reports_from_storage(self, storage_path: str) -> List[str]: ...


def choose_report_service_based_on_environment(cloud_config: str) -> ReportingService:

    match cloud_config:
        case "LOCAL":
            from service_connections.reporting_service.local_reporting import LocalReportingService

            return LocalReportingService()
        case "AZURE":
            from service_connections.cloud_service.azure_service import AzureCloudService
            from service_connections.reporting_service.cloud_reporting import CloudReportingService

            return CloudReportingService(cloud_service=AzureCloudService())
        case "AWS":
            from service_connections.cloud_service.aws_service import AwsCloudService
            from service_connections.reporting_service.cloud_reporting import CloudReportingService

            return CloudReportingService(cloud_service=AwsCloudService())
        case _:
            raise ValueError(f"Unknown reporting service: {cloud_config}")


def parse_xml_report(xml_file_path: str) -> dict:
    """
    Parses an XML report file and returns the data as a dictionary.
    """

    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    testsuite_node = root.find("testsuite")
    if testsuite_node is None:
        raise ValueError("No 'testsuite' node found in the XML file.")

    return testsuite_node.attrib