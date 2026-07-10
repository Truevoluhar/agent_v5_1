import sqlite3

def create_database(database_name: str) -> None:

    try:
        connection = sqlite3.connect(database_name)

    except Exception as e:
        print(e)
        return
    
    finally:
        connection.close()

create_database("./resources/db/agent_db")
