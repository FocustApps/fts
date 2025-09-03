from datetime import datetime
from uuid import UUID
from uuid import uuid4
from pydantic import BaseModel
import sqlalchemy as sql
from sqlalchemy import Engine
from sqlalchemy.orm import Mapped, mapped_column, declarative_base, Session


Base = declarative_base()


class IngestTable(Base):
    __tablename__ = "Ingest"
    __table_args__ = {"schema": "QAReporting"}

    id: Mapped[str] = mapped_column(sql.String, primary_key=True)
    CreatedDate: Mapped[datetime] = mapped_column(sql.DateTime)
    ReportFile: Mapped[str] = mapped_column(sql.String)
    SystemUnderTest: Mapped[str] = mapped_column(sql.String)
    EnvironmentUnderTest: Mapped[str] = mapped_column(sql.String)


class IngestModel(BaseModel):
    """
    IngestModel is a Pydantic model that represents the data
    structure for the Ingest table.
    """

    id: str | None = None
    CreatedDate: datetime | None = None
    ReportFile: str | None = None
    SystemUnderTest: str | None = None
    EnvironmentUnderTest: str | None = None


def insert_ingest_data(
    engine: Engine, session: Session, ingest_data: IngestModel
) -> IngestModel:
    """
    Inserts data into the Ingest table.
    """
    with Session(engine) as session:
        ingest_data.id = str(uuid4())
        ingest_entry = IngestTable(**ingest_data.model_dump())
        session.add(ingest_entry)
        session.commit()
        session.refresh(ingest_entry)
    return IngestModel(**ingest_entry.__dict__)

def delete_ingest_data_by_id(
    engine: Engine, session: Session, ingest_id: int
) -> bool:
    """
    Deletes data from the Ingest table by ID.
    """
    with Session(engine) as session:
        ingest_entry = session.query(IngestTable).filter(IngestTable.id == ingest_id).first()
        if ingest_entry:
            session.delete(ingest_entry)
            session.commit()
            return True
        return False