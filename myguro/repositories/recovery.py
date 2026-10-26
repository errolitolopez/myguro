from myguro.repositories.base import Repository


class RecoveryRepository(Repository):
    def get(self, user_id):
        """The person's code row (code_hash, created_at), or None if they never made one."""
        return self.one("SELECT code_hash, created_at FROM recovery_codes WHERE user_id = ?", (user_id,))

    def save(self, user_id, code_hash):
        """Keep this hash as the person's code, replacing the old one."""
        self.execute(
            "INSERT INTO recovery_codes (user_id, code_hash) VALUES (?, ?) "
            "ON CONFLICT (user_id) DO UPDATE SET code_hash = excluded.code_hash, created_at = datetime('now')",
            (user_id, code_hash),
        )
