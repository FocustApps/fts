"""
Docstring for common.service_connections.db_service.database.tables.purge_table
"""

from common.service_connections.db_service.database.base import Base
from sqlalchemy import String as sqlString, DateTime as sqlDateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import sqlalchemy as sql


class PurgeTable(Base):
    """Purge table model for tracking purge operations.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Tracks automated data retention and purge operations for other tables. Manages
         when tables were last purged and defines purge intervals to maintain database
         performance and comply with data retention policies.

    2. What level of user should be interacting with this table?
       - Super Admin: Full CRUD access to configure purge schedules
       - Automated Background Jobs: Updates last_purged_at after executing purge operations
       - Regular Users/Admins: No direct access

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: None (system/operational table)
       - Below: None (references other tables via table_name string field)
       - Related: Indirectly manages EmailProcessorTable, test results, and other high-volume tables

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - No. PurgeTable records should only be deleted manually by Super Admin or if the
         referenced table no longer exists in the database schema.

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required.
    """

    __tablename__ = "purgeTable"

    purge_id: Mapped[str] = mapped_column(sqlString(36), primary_key=True)
    table_name: Mapped[str] = mapped_column(sqlString(255), nullable=False)
    last_purged_at: Mapped[datetime] = mapped_column(
        sqlDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        sqlDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(sqlDateTime, nullable=True)
    purge_interval_days: Mapped[int] = mapped_column(
        sql.Integer, nullable=False, default=30
    )

    def __repr__(self) -> str:
        return f"<PurgeTable(id={self.id}, table_name='{self.table_name}', last_purged_at={self.last_purged_at})>"
