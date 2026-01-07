"""
Email processor table model for email automation tasks.
"""

from datetime import datetime, timezone
from typing import List, Optional

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from common.service_connections.db_service.database.base import Base


class EmailProcessorTable(Base):
    """Email processor model for handling email automation tasks.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Tracks test cases that will require an email to be sent for some sort of
      workflow validation (e.g., user registration, password reset).

    2. What level of user should be interacting with this table?
       - Test Automation Framework: Primary user - creates and updates records during test execution
       - Admin: Read access for monitoring and debugging email processing jobs
       - Super Admin: Full CRUD for troubleshooting and manual intervention

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: None (independent processing queue)
       - Below: None (no child tables)
       - Related: Indirectly related to SystemUnderTestTable via 'system' field

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
      - No. EmailProcessorTable records should be retained for audit/history or purged
         based on age (see PurgeTable for scheduled cleanup).

    5. Will this table be require a connection a secure cloud provider service?
      - No direct cloud connection required.
    """

    __tablename__ = "emailProcessorTable"

    email_processor_id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    email_item_id: Mapped[int] = mapped_column(sql.Integer, unique=True, nullable=False)
    multi_item_email_ids: Mapped[Optional[List]] = mapped_column(JSONB)
    multi_email_flag: Mapped[bool] = mapped_column(sql.Boolean, default=False)
    multi_attachment_flag: Mapped[bool] = mapped_column(sql.Boolean, default=False)
    system: Mapped[Optional[str]] = mapped_column(sql.String(96))
    test_name: Mapped[Optional[str]] = mapped_column(sql.String(255))
    requires_processing: Mapped[bool] = mapped_column(sql.Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime, nullable=True)
    last_processed_at: Mapped[Optional[datetime]] = mapped_column(
        sql.DateTime, nullable=True
    )

    def __repr__(self) -> str:
        return f"<EmailProcessor(id={self.email_processor_id}, \
        email_item_id={self.email_item_id}, system='{self.system}')>"


__all__ = ["EmailProcessorTable"]
