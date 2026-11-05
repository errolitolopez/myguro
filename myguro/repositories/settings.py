from myguro.repositories.base import Repository


class SettingsRepository(Repository):
    def get(self, key):
        """The saved value (text), or None when the setting was never saved."""
        row = self.one("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else None

    def set(self, key, value):
        self.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def get_for_user(self, user_id, key):
        """A teacher's own setting (text), or None when they never saved it."""
        row = self.one("SELECT value FROM teacher_settings WHERE user_id = ? AND key = ?", (user_id, key))
        return row["value"] if row else None

    def set_for_user(self, user_id, key, value):
        self.execute(
            "INSERT INTO teacher_settings (user_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id, key) DO UPDATE SET value = excluded.value",
            (user_id, key, value),
        )
