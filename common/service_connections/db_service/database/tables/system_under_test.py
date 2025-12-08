from common.service_connections.db_service.database.base import Base


class SystemUnderTestTable(Base):
    """
    Table representing systems under test.

    Attributes:
        sut_id str(uuid): Unique identifier for the system under test.
        system_name str: Name of the system under test.
        repositories List[repository_ids]: List of repo IDs associated with the system.
        environments List[environment_ids]: List of environment IDs associated with the system.
        description str: Description of the system under test.
        wiki_url str: URL to the wiki page for the system under test.
        created_at datetime: Timestamp when the record was created.
        updated_at datetime: Timestamp when the record was last updated.
        deleted_at datetime: Timestamp when the record was deleted.
    """