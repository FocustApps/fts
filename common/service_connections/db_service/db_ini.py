import logging
from sqlalchemy import MetaData

from service_connections.db_service import DB_TABLES
from service_connections.db_service.db_manager import DB_ENGINE


def create_db_and_tables():
    metadata = MetaData()
    metadata.create_all(
        bind=DB_ENGINE,
        tables=DB_TABLES,
    )
    return True


if __name__ == "__main__":
    logging.info("\n\n\n Attempting to create database and tables. \n\n\n")
    db_tables_created = create_db_and_tables()
    if db_tables_created:
        logging.info("Database and tables created successfully.")
    else:
        raise ConnectionError("Database and table creation failed.")
