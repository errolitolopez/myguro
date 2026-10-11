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
