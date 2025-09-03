"""
Initializes the database and creates the tables for fenrir application.
"""

from enum import Enum
import logging
import os
import urllib
import urllib.parse

from dotenv import load_dotenv
from pydantic import BaseModel
from sqlalchemy import Engine, create_engine


class DatabaseTypeEnum(Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"
    MSSQL = "mssql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"

    @classmethod
    def get_database_types(cls):
        return [db_type.value for db_type in cls]

    @classmethod
    def get_database_type(cls, db_type: str):
        return cls[db_type.upper()]


class DatabaseServiceConfig(BaseModel):

    database_type: DatabaseTypeEnum | None = None
    database_server_name: str | None = "localhost"
    database_name: str | None = "fenrir"
    database_user: str | None = None
    database_password: str | None = None
    database_port: int | None = 5432
    database_pool_size: int | None = 20
    database_echo: bool | None = False


def get_database_service_config() -> DatabaseServiceConfig:
    load_dotenv()
    _db_type = os.getenv("DATABASE_TYPE") or os.getenv("REPORTING_DATABASE_TYPE")

    database_config = None

    match _db_type:
        case "postgres":
            logging.info("Using PostgreSQL database.")
            database_config = DatabaseServiceConfig(
                database_type=DatabaseTypeEnum.get_database_type(_db_type),
                database_server_name=os.getenv("DB_HOST", "postgres"),
                database_name=os.getenv("POSTGRES_DB"),
                database_user=os.getenv("POSTGRES_USER"),
                database_password=os.getenv("POSTGRES_PASSWORD"),
                database_port=int(os.getenv("DB_PORT", "5432")),
            )
        case "mysql" | "mssql":
            logging.info(f"Using {_db_type.upper()} database.")
            database_config = DatabaseServiceConfig(
                database_type=DatabaseTypeEnum.get_database_type(_db_type),
                database_server_name=os.getenv("DB_HOST"),
                database_name=os.getenv("DB_NAME"),
                database_user=os.getenv("DB_USER"),
                database_password=os.getenv("DB_PASSWORD"),
                database_port=int(os.getenv("DB_PORT", "5432")),
                database_pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
                database_echo=bool(os.getenv("DB_ECHO") == "True"),
            )
        case _:
            raise ValueError(
                f"Unsupported database type: {_db_type}. Supported types: {DatabaseTypeEnum.get_database_types()}"
            )

    if database_config is None:
        raise ValueError("Failed to create database configuration")

    logging.debug(f"Database service config: {database_config}")
    for field, value in database_config:
        if value is None:
            logging.error(f"Database service config field '{field}' is not set.")
            continue
    return database_config


def build_connection_string(database_config: DatabaseServiceConfig) -> str:
    """
    Loads the database connection string based on the database type.
    This function will return a connection string based on the database type.
    It will return a connection string for MySQL, MSSQL, or SQLite.
    """

    match database_config.database_type:
        case DatabaseTypeEnum.MYSQL | DatabaseTypeEnum.MSSQL:
            _AZURE_SQL_CONNECTION_STRING = (
                "Driver={ODBC Driver 18 for SQL Server};Server=tcp:"
                + database_config.database_server_name
                + ".database.windows.net,1433;Database="
                + database_config.database_name
                + ";UID="
                + database_config.database_user
                + ";PWD="
                + database_config.database_password
                + ";Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
            )

            # URL-encode the connection string
            quoted = urllib.parse.quote_plus(_AZURE_SQL_CONNECTION_STRING)
            # Create Database Engine Variable
            return f"mssql+pyodbc:///?odbc_connect={quoted}"
        case DatabaseTypeEnum.POSTGRES:
            return (
                f"postgresql+psycopg2://{database_config.database_user}:"
                f"{urllib.parse.quote_plus(database_config.database_password)}@"
                f"{database_config.database_server_name}:{database_config.database_port}/"
                f"{database_config.database_name}"
            )
        case DatabaseTypeEnum.SQLITE:
            return f"sqlite:///{database_config.database_name}"
        case _:
            logging.error(
                f"Database type {database_config.database_type} is not supported."
            )
            raise ValueError(
                f"Unsupported database type: {database_config.database_type}"
            )


def resolve_database_engine(database_config: DatabaseServiceConfig) -> Engine:
    """
    Since there is a remote database and a local database,
    this function will determine which database to use.
    """
    connection_string = build_connection_string(database_config=database_config)

    # Set connect_args based on database type
    connect_args = {}
    if database_config.database_type == DatabaseTypeEnum.SQLITE:
        connect_args = {"check_same_thread": False}

    try:
        engine: Engine = create_engine(
            connection_string,
            echo=database_config.database_echo,
            pool_size=database_config.database_pool_size,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        logging.debug(f"Database connection string: {connection_string}")
    except Exception as e:
        raise RuntimeError(f"Database connection failed. {connection_string}: {e}") from e
    return engine


DB_ENGINE: Engine = resolve_database_engine(database_config=get_database_service_config())
