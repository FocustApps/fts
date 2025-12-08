"""
This module provides functionality to send an email with an attachment using Gmail's SMTP server.

Functions:
- is_valid_email(email): Validates if the provided email address matches the standard email format.
- send_email_with_attachment(): Sends an email with a PDF attachment to a recipient
email address specified in environment variables.

Dependencies:
- os: For accessing environment variables.
- re: For regular expression matching.
- smtplib: For sending emails using the SMTP protocol.
- email: For constructing email messages with attachments.
- uuid: For generating unique identifiers.
- dotenv: For loading environment variables from a .env file.
- services.utils: For getting the project root directory.
"""

from datetime import datetime
import os
import re
from typing import List
import logging

import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy.orm import Session

from service_connections.db_service.db_manager import DB_ENGINE
from common.config import EmailServiceConfig, get_email_service_config
from common.service_connections.db_service.models.email_processor_model import (
    SystemEnum,
    EmailProcessorModel,
    update_email_item_by_id,
)
from common.service_connections.test_case_service.azure_devops_test_cases import (
    get_attachment_data,
    get_attachment_id,
    get_multiple_attachment_ids,
)
from common.utils import create_pdf_file

_DATETIME_FORMAT = "%d-%m-%y-%H-%M-%S"


def is_valid_email(email) -> bool:
    """
    Check if the provided email address is valid.
    Args:
        email (str): The email address to validate.
    Returns:
        bool: True if the email address is valid, False otherwise.
    """
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if re.match(pattern, email) is not None:
        return True
    return False


def load_file_data(file_path: str, file_type: str = "pdf") -> MIMEBase:
    """
    Load a file from disk and wrap it as an email attachment part.

    Args:
        file_path (str): Absolute or relative path to the file on disk.
        file_type (str): MIME subtype for the attachment's content type
            (e.g., "pdf", "docx"). Defaults to "pdf".

    Returns:
        MIMEBase: A MIMEBase object with the file content, base64-encoded and
            a Content-Disposition header set with the filename.

    Raises:
        FileNotFoundError: If the file at file_path cannot be opened.
    """
    with open(file_path, "rb") as attachment:
        part = MIMEBase("application", file_type)
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={file_path.split('/')[-1]}",
        )
    return part


def get_valid_system_recipient_from_work_item(
    work_item: EmailProcessorModel,
) -> SystemEnum:
    """
    Validate that a work item has a system set and return it.

    Args:
        work_item (WorkItemModel): The work item whose system recipient will be
            used to determine where to send email.

    Returns:
        SystemEnum: The system value from the work item.

    Raises:
        ValueError: If the work item does not have a system set.
    """
    system = getattr(work_item, "system", None)
    if not system:
        raise ValueError("Unknown system recipient for work item.")
    return system


def fetch_and_write_attachment(
    attachment_id: int, file_extension: str = "pdf"
) -> tuple[str, str]:
    """
    Fetch attachment bytes by id, write them to a timestamped file, and return
    file path and file name.

    The underlying writer uses create_pdf_file which accepts raw bytes. The
    caller-specified extension is preserved for the resulting filename.

    Args:
        attachment_id (int): Identifier for the remote attachment to fetch.
        file_extension (str): File extension to apply to the created file
            (e.g., "pdf", "docx"). Defaults to "pdf".

    Returns:
        tuple[str, str]: A tuple of (file_path, file_name) for the created file.
    """
    attachment_bytes = get_attachment_data(attachment_id=attachment_id)
    file_name = f"AUTO-{datetime.now().strftime(_DATETIME_FORMAT)}.{file_extension}"
    file_path = create_pdf_file(f"{os.getcwd()}/{file_name}", attachment_bytes)
    return file_path, file_name


def build_email_body_single(
    *, file_name: str, attachment_id: int, work_item: EmailProcessorModel
) -> str:
    """
    Build an email body for a single-attachment message.

    Args:
        file_name (str): Name of the file attached.
        attachment_id (int): The Azure DevOps attachment id.
        work_item (WorkItemModel): The originating work item.

    Returns:
        str: A human-readable body including file and work item details.
    """
    return (
        f"\n "
        f"        File Attachment: {file_name} \n "
        f"        Attachment ID: {attachment_id} \n "
        f"        Work Item ID: {work_item.email_item_id} \n "
        f"        Time Sent: {datetime.now().strftime('%d/%m/%y-%H-%M-%S')} \n "
        f"        Fenrir Test Name: {work_item.test_name}"
    )


def build_email_body_multiple(
    *, file_paths: List[str], work_item: EmailProcessorModel
) -> str:
    """
    Build an email body for a multi-attachment message.

    Args:
        file_paths (list[str]): Paths to files that will be attached.
        work_item (WorkItemModel): The originating work item.

    Returns:
        str: A human-readable body including files and work item details.
    """
    return (
        f"\n "
        f"        File Attachments: {file_paths} \n "
        f"        Work Item ID: {work_item.email_item_id} \n "
        f"        Time Sent: {datetime.now().strftime('%d/%m/%y-%H-%M-%S')} \n "
        f"        Fenrir Test Name: {work_item.test_name}"
    )


def build_processed_work_item(
    *, work_item: EmailProcessorModel, file_names: List[str]
) -> EmailProcessorModel:
    """
    Build a WorkItemModel payload for updating the DB after email send.

    Args:
        work_item (WorkItemModel): The original work item being processed.
        file_names (list[str]): List of filenames (not paths) that were emailed.

    Returns:
        WorkItemModel: A payload suitable for update_work_item_by_id.
    """
    return EmailProcessorModel(
        email_item_id=work_item.email_item_id,
        multi_item_email_ids=file_names,
        test_name=work_item.test_name,
        requires_processing=True,
        updated_at=datetime.now(),
    )


def send_email_with_attachment(
    body: str,
    subject: str | List[str],
    file_data: MIMEBase | List[MIMEBase],
    email_config: EmailServiceConfig,
    system_recipient: SystemEnum,
) -> str | None:
    """
    Send an email with one or more attachments using Gmail's SMTP server.

    Args:
        body (str): HTML or plain text email body. Will be attached as text/plain
            by default.
        subject (str | list[str]): Subject for the email. If a list is passed,
            a generic "MULTIPLE ATTACHMENTS" subject with a timestamp is used.
        file_data (MIMEBase | list[MIMEBase]): One or more MIME parts representing
            attachments to include in the message.
        email_config (EmailServiceConfig): Credentials and recipient configuration.
        system_recipient (SystemEnum): Which system determines the To: recipient.

    Returns:
        str | None: The subject string used for the message, or None on error.

    Raises:
        ValueError: If an invalid system recipient is specified.
        smtplib.SMTPException: If there is an error sending the email.
    """
    sender_email = email_config.email_user
    sender_password = email_config.email_password
    recipient_email = email_config.miner_email_recipient

    message = MIMEMultipart()
    if isinstance(subject, list):
        used_subject = (
            f"MULTIPLE ATTACHMENTS {datetime.now().strftime('%d/%m/%y-%H-%M-%S')}"
        )
        message["Subject"] = used_subject
    else:
        used_subject = subject
        message["Subject"] = used_subject

    message["From"] = sender_email

    if system_recipient == SystemEnum.MINER_OCR:
        message["To"] = email_config.miner_email_recipient
    elif system_recipient == SystemEnum.TRUE_SOURCE_OCR:
        message["To"] = email_config.true_source_email_recipient
    else:
        raise ValueError(f"Invalid system recipient specified. {system_recipient}")
    html_part = MIMEText(body)

    message.attach(html_part)
    if isinstance(file_data, list):
        for data in file_data:
            message.attach(data)
    else:
        message.attach(file_data)

    try:
        # Use the selected To: address for actual send
        recipient_email = message.get("To", recipient_email)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        logging.info(
            f"Email sent successfully to {recipient_email} with subject: {used_subject}"
        )
        return used_subject
    except TypeError:
        logging.error(
            f"Error sending email to {recipient_email} with subject: {used_subject}"
        )
        return None


def process_work_item_single_attachment(work_item: EmailProcessorModel) -> None:
    """
    Process a work item that has a single attachment: fetch, write, email, update DB.

    Args:
        work_item (WorkItemModel): The work item to process, including work item id,
            test name, and the target system.

    Workflow:
        1. Retrieve the attachment id associated with the work item.
        2. Fetch the attachment bytes and write a timestamped file on disk.
        3. Load the file as a MIME attachment part.
        4. Compose the email body.
        5. Send the email with the attachment to the system-specific recipient.
        6. Update the work item in the database with the sent filename.

    Raises:
        ValueError: If the work item is missing a system recipient.
        FileNotFoundError: If the created file cannot be read for attachment.
    """

    attachment_id = get_attachment_id(work_item.email_item_id)
    system_recipient = get_valid_system_recipient_from_work_item(work_item)

    file_path, file_name = fetch_and_write_attachment(
        attachment_id=attachment_id, file_extension="pdf"
    )

    file_data = load_file_data(
        file_path=file_path,
    )

    email_body = build_email_body_single(
        file_name=file_name, attachment_id=attachment_id, work_item=work_item
    )

    email_config = get_email_service_config()

    send_email_with_attachment(
        subject=file_name,
        body=email_body,
        file_data=file_data,
        email_config=email_config,
        system_recipient=system_recipient,
    )
    logging.info(f"Email sent with attachment: {file_name}")
    processed_work_item = build_processed_work_item(
        work_item=work_item, file_names=[file_name]
    )
    logging.info(f"Updating work item {work_item.id} with processed details.")
    update_email_item_by_id(
        email_item_id=work_item.id,
        work_item=processed_work_item,
        engine=DB_ENGINE,
        session=Session,
    )

    return


def process_multiple_attachments(work_item: EmailProcessorModel) -> None:
    """
    Process a work item that has multiple attachments: fetch, write, email, update DB.

    Args:
        work_item (WorkItemModel): The work item containing details such as work item id
            and test name.

    Workflow:
        1. Retrieve the list of (attachment_id, file_extension) pairs.
        2. For each, write a timestamped file on disk and collect file paths.
        3. Build the email body summarizing all attachments.
        4. Load each file as a MIME attachment part.
        5. Send the email with all attachments to the system-specific recipient.
        6. Update the work item in the database with the sent filenames.
    """

    if work_item.email_item_id == 30103:
        attachment_data = get_multiple_attachment_ids(
            work_item_id=work_item.email_item_id, file_extensions=["docx", "doc"]
        )

    else:
        attachment_data = get_multiple_attachment_ids(
            work_item_id=work_item.email_item_id
        )

    system_recipient = get_valid_system_recipient_from_work_item(work_item)

    attachment_file_names: List[str] = []
    for attachment_id, file_extension in attachment_data:
        file_path, file_name = fetch_and_write_attachment(
            attachment_id=attachment_id, file_extension=file_extension
        )
        attachment_file_names.append(file_path)

    email_body = build_email_body_multiple(
        file_paths=attachment_file_names, work_item=work_item
    )

    file_data = [
        load_file_data(file_path=file_path) for file_path in attachment_file_names
    ]

    email_config = get_email_service_config()

    send_email_with_attachment(
        subject=attachment_file_names,
        body=email_body,
        file_data=file_data,
        email_config=email_config,
        system_recipient=system_recipient,
    )
    file_names_only = [file.split("/")[-1] for file in attachment_file_names]
    processed_work_item = build_processed_work_item(
        work_item=work_item, file_names=file_names_only
    )

    update_email_item_by_id(
        email_item_id=work_item.id,
        work_item=processed_work_item,
        engine=DB_ENGINE,
        session=Session,
    )

    return


def evaluate_email_and_send_based_on_attachment_flag(
    work_item: EmailProcessorModel,
) -> None:
    """
    Dispatch email processing based on a work item's attachment flags.

    If multi_attachment_flag is true, sends a single email with multiple attachments;
    if multi_email_flag is true, reserved for future behavior (not implemented);
    otherwise sends a single email with a single attachment.

    Args:
        work_item (WorkItemModel): The work item to evaluate and process.
    """
    if work_item.multi_attachment_flag:
        logging.info(f"Work item: {work_item} is flagged with multiple attachments.")
        process_multiple_attachments(work_item=work_item)
    elif work_item.multi_email_flag:
        logging.info(f"Work item: {work_item} has multiple emails.")
    else:
        process_work_item_single_attachment(work_item)
