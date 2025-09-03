from sqlalchemy import MetaData, Table, text
from service_connections.db_service.db_manager import DB_ENGINE


metadata = MetaData()


def main():
    # work_item_table = Table("workItemTable", metadata, autoload_with=engine)

    # add new column
    with DB_ENGINE.connect() as conn:
        conn.execute(text("ALTER TABLE workItemTable ADD multi_email_flag BIT;"))
        conn.commit()

    # drop old column
    # with engine.connect() as conn:
    #     conn.execute(text("ALTER TABLE workItemTable DROP COLUMN multi_item_email_ids;"))
    #     conn.commit()


if __name__ == "__main__":
    main()
