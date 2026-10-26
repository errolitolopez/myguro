from myguro.repositories.base import Repository


class FeedbackRepository(Repository):
    def mine(self, user_id):
        """{question key: rating} the person gave before (empty if never)."""
        rows = self.all("SELECT question, rating FROM feedback WHERE user_id = ?", (user_id,))
        return {row["question"]: row["rating"] for row in rows}

    def save(self, user_id, question, rating):
        """Add the rating, or replace the person's earlier one for this question."""
        self.execute(
            "INSERT INTO feedback (user_id, question, rating) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id, question) DO UPDATE SET rating = excluded.rating, updated_at = datetime('now')",
            (user_id, question, rating),
        )

    def counts(self, role=None):
        """[(question, rating, how many)] for everyone, or only for one role. No names."""
        sql = ("SELECT f.question, f.rating, COUNT(*) AS how_many FROM feedback f "
               "JOIN users u ON u.id = f.user_id {where} GROUP BY f.question, f.rating")
        if role:
            rows = self.all(sql.format(where="WHERE u.role = ?"), (role,))
        else:
            rows = self.all(sql.format(where=""))
        return [(row["question"], row["rating"], row["how_many"]) for row in rows]

    def respondents(self, role=None):
        """How many different people rated anything (everyone, or only one role)."""
        sql = "SELECT COUNT(DISTINCT f.user_id) FROM feedback f JOIN users u ON u.id = f.user_id {where}"
        if role:
            return self.value(sql.format(where="WHERE u.role = ?"), (role,))
        return self.value(sql.format(where=""))
