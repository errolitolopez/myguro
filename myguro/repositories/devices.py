from myguro.domain.devices import MAX_SHARED_DEVICES, SHARED_AT_LEAST
from myguro.repositories.base import Repository


class DeviceRepository(Repository):
    """Which devices each person signed in from (counts and times only)."""

    def record(self, user_id, device_key, device_name):
        """Remember a sign-in of this person from this device."""
        self.execute(
            "INSERT INTO device_logins (device_key, user_id, device_name) VALUES (?, ?, ?) "
            "ON CONFLICT (device_key, user_id) DO UPDATE SET logins = logins + 1, last_at = datetime('now'), "
            "device_name = excluded.device_name",
            (device_key, user_id, device_name),
        )

    def shared(self):
        """Rows of the devices that two or more accounts signed in from, newest first. The admin's own account is
        left out: it signs in as other people to help, which is not sharing."""
        return self.all(
            """
            SELECT dl.device_key, dl.user_id, dl.logins, dl.first_at, dl.last_at, dl.device_name,
                   u.name, u.username, u.role
            FROM device_logins dl JOIN users u ON u.id = dl.user_id
            WHERE u.role != 'admin' AND dl.device_key IN (
                SELECT d.device_key FROM device_logins d JOIN users x ON x.id = d.user_id
                WHERE x.role != 'admin' GROUP BY d.device_key HAVING COUNT(*) >= ?
                ORDER BY MAX(d.last_at) DESC LIMIT ?)
            ORDER BY dl.last_at DESC
            """,
            (SHARED_AT_LEAST, MAX_SHARED_DEVICES),
        )
