import psycopg2


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="snickr",
        user="postgres",
        password="10204211",
        port=5432,
    )
