"""
Azure DevOps Test Case functions.
"""

import os
from typing import Callable, Iterator, List


from azure.devops.connection import Connection
from azure.devops.v7_0.work_item_tracking.work_item_tracking_client import (
    WorkItemTrackingClient,
)
from azure.devops.v7_0.work_item_tracking.models import WorkItem
from msrest.authentication import BasicAuthentication

from common.config import get_pipeline_config


def auth_to_azure_devops() -> Connection:
    """
    Authenticate to Azure DevOps using a personal access token.
    """
    personal_access_token = f"{os.getenv('AZURE_DEVOPS_TOKEN')}"
    organization_url = "https://dev.azure.com/focustapps"
    credentials = BasicAuthentication("", personal_access_token)
    connection = Connection(base_url=organization_url, creds=credentials)
    return connection


def azure_associated_automation(work_item: str | List[str]):
    """
    Decorator to add automation labels to a work item in Azure DevOps.
    """

    def decorator_func(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            pipeline_config = get_pipeline_config()
            if pipeline_config.is_ci_job:
                if isinstance(work_item, list):
                    for item in work_item:
                        add_automation_to_work_item(
                            work_item=item,
                            function_name=func.__name__,
                            function_location=func.__module__,
                        )
                else:
                    add_automation_to_work_item(
                        work_item=work_item,
                        function_name=func.__name__,
                        function_location=func.__module__,
                    )
            return func(*args, **kwargs)

        return wrapper

    return decorator_func


def add_automation_to_work_item(
    work_item: str, function_name: str, function_location: str
):
    """
    Add automation labels to a work item in Azure DevOps.
    Name of the test. - Function name.
    Location of the test. - File it is in.
    Type of test. - Integration Test
    """
    connection = auth_to_azure_devops()
    # Get a client for the Work Item Tracking API
    wit_client = connection.clients.get_work_item_tracking_client()
    try:

        # Create a patch document
        patch_document = [
            {
                "op": "add",
                "path": "/fields/Microsoft.VSTS.TCM.AutomatedTestName",
                "value": function_name,
            },
            {
                "op": "add",
                "path": "/fields/Microsoft.VSTS.TCM.AutomatedTestStorage",
                "value": function_location,
            },
            {
                "op": "add",
                "path": "/fields/Microsoft.VSTS.TCM.AutomatedTestType",
                "value": "Integration Test",
            },
        ]

        wit_client.update_work_item(document=patch_document, id=work_item)

    except Exception:
        raise Exception(f"Failed to add automation to work item: {work_item}")


def check_if_test_case_is_automated(work_item_id: str) -> str:
    """
    Query Azure DevOps to check if a test case is automated.
    Based on the FA Automation field.
    """
    connection = auth_to_azure_devops()

    wit_client: WorkItemTrackingClient = (
        connection.clients.get_work_item_tracking_client()
    )
    try:
        work_item: WorkItem = wit_client.get_work_item(work_item_id)
        return work_item.fields["Custom.FAAutomation"]
    except KeyError:
        raise KeyError("The work item does not have a value for Custom.FAAutomation")


def get_work_item_by_id(work_item_id: str, expand: str = None) -> WorkItem:
    """
    Query the
    """
    connection = auth_to_azure_devops()

    wit_client: WorkItemTrackingClient = (
        connection.clients.get_work_item_tracking_client()
    )
    try:
        work_item = wit_client.get_work_item(work_item_id, expand=expand)
    except Exception:
        raise Exception(f"{work_item_id} not found.")
    return work_item


def check_if_work_item_has_test(work_item_id: str) -> str | bool:
    """
    Check if a work item has an automated test.
    """
    work_item_from_azure: WorkItem = get_work_item_by_id(work_item_id)
    if not work_item_from_azure.fields.get("Microsoft.VSTS.TCM.AutomatedTestName"):
        return False
    fenrir_test_name = work_item_from_azure.fields.get(
        "Microsoft.VSTS.TCM.AutomatedTestName"
    )
    return fenrir_test_name


def get_attachment_id(work_item_id: str, file_extension: str = "pdf") -> str:
    """
    param: work_item_id: str
    param: file_extension: str
    returns: str

    Retrieves the FIRST attachment ID of a work item.
    If more exist, this function will need to be updated.
    """
    work_item = get_work_item_by_id(work_item_id, expand="All")
    for rel in work_item.relations:
        if rel.attributes["name"].endswith(file_extension):
            if rel.rel == "AttachedFile" and (split_url := rel.url.split("/")):
                if split_url[-2] == "attachments":
                    return split_url[-1]
    raise ValueError("No attachment found")


def get_multiple_attachment_ids(
    work_item_id: str, file_extensions: List[str] = ["pdf"]
) -> List[tuple[str, str]]:
    """
    Get all attachment IDs of a work item based on file extension.
    Returns a list of tuples: (attachment_id, file_extension)
    """
    attachment_ids_and_extensions = []
    work_item = get_work_item_by_id(work_item_id, expand="All")

    def get_attachment_by_extension(extension: str):
        for rel in work_item.relations:
            if rel.attributes["name"].endswith(extension):
                if rel.rel == "AttachedFile" and (split_url := rel.url.split("/")):
                    if split_url[-2] == "attachments":
                        attachment_ids_and_extensions.append((split_url[-1], extension))

    for extension in file_extensions:
        get_attachment_by_extension(extension)

    if not attachment_ids_and_extensions:
        raise ValueError("No attachment found")
    return attachment_ids_and_extensions


def get_attachment_data(attachment_id: str) -> Iterator[bytes]:
    """
    Using the attachment ID from get_attachment_id()
    get the content of the attachment.
    """
    connection = auth_to_azure_devops()

    wit_client: WorkItemTrackingClient = (
        connection.clients.get_work_item_tracking_client()
    )
    try:
        return wit_client.get_attachment_content(id=attachment_id)
    except Exception:
        raise Exception(f"{attachment_id} not found.")
