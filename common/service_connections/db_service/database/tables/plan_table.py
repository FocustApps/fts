"""
Docstring for common.service_connections.db_service.database.tables.plan_table
"""


from typing import Optional
from common.service_connections.db_service.database.base import Base
from sqlalchemy import String as sqlString, DateTime as sqlDateTime, Enum as sqlEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import sqlalchemy as sql


class PlanTable(Base):
    """
    Docstring for PlanTable
    """
    plan_id: Mapped[str] = mapped_column(sqlString(36), primary_key=True)
    plan_name: Mapped[str] = mapped_column(sqlString(255), nullable=False)
    test_suite_ids: Mapped[str] = mapped_column(sqlString(1024), nullable=False)
    suite_tags: Mapped[Optional[str]] = mapped_column(sql.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sqlDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sqlDateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        sqlEnum("active", "inactive", name="plan_status_enum"), nullable=False, default="active"
    )
    owner_user_id: Mapped[Optional[str]] = mapped_column(sql.Integer, nullable=True)