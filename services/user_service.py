from database import conn, cursor


def create_user(telegram_id, first_name, username):
    cursor.execute(
        "SELECT telegram_id FROM users WHERE telegram_id=?",
        (telegram_id,)
    )

    if cursor.fetchone() is None:
        cursor.execute(
            """
            INSERT INTO users
            (telegram_id, first_name, username)
            VALUES (?, ?, ?)
            """,
            (
                telegram_id,
                first_name,
                username
            )
        )
        conn.commit()


def get_user(telegram_id):
    cursor.execute(
        "SELECT * FROM users WHERE telegram_id=?",
        (telegram_id,)
    )
    return cursor.fetchone()
