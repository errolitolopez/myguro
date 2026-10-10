class Repository:
    def __init__(self, db):
        self.db = db  # a sqlite3 connection (rows behave like dicts)

    def one(self, sql, params=()):
        return self.db.execute(sql, params).fetchone()

    def all(self, sql, params=()):
        return self.db.execute(sql, params).fetchall()

    def value(self, sql, params=()):
        """The first column of the first row (e.g. a COUNT)."""
        return self.db.execute(sql, params).fetchone()[0]

    def execute(self, sql, params=()):
        return self.db.execute(sql, params)
