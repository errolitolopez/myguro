from myguro.repositories.base import Repository


class RecoveryRepository(Repository):
    def get(self, user_id):
        """The person's code row (code_hash, uses_left, created_at), or None if they never made one."""
        return self.one("SELECT code_hash, uses_left, created_at FROM recovery_codes WHERE user_id = ?", (user_id,))

    def save(self, user_id, code_hash, uses):
        """Keep this hash as the person's code, with this many uses, replacing the old one."""
        self.execute(
            "INSERT INTO recovery_codes (user_id, code_hash, uses_left) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id) DO UPDATE SET code_hash = excluded.code_hash, uses_left = excluded.uses_left, "
            "created_at = datetime('now')",
            (user_id, code_hash, uses),
        )

    def use_one(self, user_id):
        """Take one use from the code. Returns how many are left. Never goes below 0."""
        self.execute("UPDATE recovery_codes SET uses_left = uses_left - 1 WHERE user_id = ? AND uses_left > 0",
                     (user_id,))
        return self.get(user_id)["uses_left"]
