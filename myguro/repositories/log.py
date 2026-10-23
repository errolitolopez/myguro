from myguro.repositories.base import Repository


class LogRepository(Repository):
    """The activity log table. Entries are only ever added and read; the one deletion is trim(),
    which removes the oldest when the log is over its size limit. Nothing updates a row."""

    def add(self, actor, action, category, summary, target_type="", target_id=None, target_name="",
            address="", at=None):
        """Add one entry. actor = {id, name, username, role} (id may be None). at is for tests and
        imports ("YYYY-MM-DD HH:MM:SS" UTC); normally the database clock is used. Does not commit."""
        columns = ["actor_id", "actor_name", "actor_username", "actor_role", "action", "category", "target_type",
                   "target_id", "target_name", "summary", "address"]
        values = [actor["id"], actor["name"], actor["username"], actor["role"], action, category, target_type,
                  target_id, target_name, summary, address]
        if at is not None:
            columns.append("at")
            values.append(at)
        marks = ", ".join("?" for _ in columns)
        return self.execute(f"INSERT INTO activity_log ({', '.join(columns)}) VALUES ({marks})", values).lastrowid

    def trim(self, keep):
        """Remove the oldest entries so about the newest `keep` stay (FIFO). Ids only grow, so one
        indexed DELETE does it, without counting rows. This is the only place an entry is deleted.
        Does not commit."""
        self.execute("DELETE FROM activity_log WHERE id <= (SELECT MAX(id) FROM activity_log) - ?", (keep,))

    @staticmethod
    def _where(filters):
        """WHERE for the filters: q (a LIKE pattern), role, category, user_id, date_from (>=), date_to (<)."""
        clauses, params = [], []
        if filters.get("q"):
            clauses.append("(actor_name LIKE ? ESCAPE '\\' OR actor_username LIKE ? ESCAPE '\\' "
                           "OR target_name LIKE ? ESCAPE '\\' OR summary LIKE ? ESCAPE '\\')")
            params += [filters["q"]] * 4
        for column, key in (("actor_role", "role"), ("category", "category"), ("actor_id", "user_id")):
            if filters.get(key) not in (None, ""):
                clauses.append(f"{column} = ?")
                params.append(filters[key])
        if filters.get("date_from"):
            clauses.append("at >= ?")
            params.append(filters["date_from"])
        if filters.get("date_to"):
            clauses.append("at < ?")
            params.append(filters["date_to"])
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    def count(self, filters):
        where, params = self._where(filters)
        return self.value(f"SELECT COUNT(*) FROM activity_log{where}", params)

    def search(self, filters, limit, offset):
        """One page of entries, newest first."""
        where, params = self._where(filters)
        return self.all(f"SELECT * FROM activity_log{where} ORDER BY at DESC, id DESC LIMIT ? OFFSET ?",
                        [*params, limit, offset])
