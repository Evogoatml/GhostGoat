import sqlite3

class Optimizer:
    def __init__(self, db_path="data/brain.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS performance (user_id TEXT, action TEXT, result TEXT)"
        )
        self.conn.commit()

    def observe(self, user_id, action, result):
        self.conn.execute(
            "INSERT INTO performance (user_id, action, result) VALUES (?,?,?)",
            (str(user_id), action, result),
        )
        self.conn.commit()
