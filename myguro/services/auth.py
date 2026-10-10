import time

from werkzeug.security import check_password_hash, generate_password_hash

from myguro.domain.accounts import check_password_change
from myguro.errors import ForbiddenError, TooManyRequestsError, UnauthorizedError, ValidationError
from myguro.services.base import Service


class LoginThrottle:
    """After too many wrong passwords, block that device + username for a while."""

    MAX_ATTEMPTS = 5
    LOCK_SECONDS = 5 * 60

    def __init__(self):
        self.failed = {}  # (ip address, username) -> {"count": wrong tries, "locked_until": timestamp}

    def check(self, key):
        record = self.failed.get(key, {"count": 0, "locked_until": 0})
        wait = int(record["locked_until"] - time.time())
        if wait > 0:
            raise TooManyRequestsError(f"Too many wrong tries. Try again in {wait // 60 + 1} min.")

    def wrong(self, key):
        record = self.failed.get(key, {"count": 0, "locked_until": 0})
        record["count"] += 1
        if record["count"] >= self.MAX_ATTEMPTS:
            record = {"count": 0, "locked_until": time.time() + self.LOCK_SECONDS}
        self.failed[key] = record

    def passed(self, key):
        self.failed.pop(key, None)

    def reset(self):
        self.failed.clear()


class AuthService(Service):
    def login(self, username, password, ip, throttle):
        """The user's row when the username and password are right."""
        username = str(username or "").strip()
        password = str(password or "")
        if not username or not password:
            raise ValidationError("Enter your username and password.")
        key = (ip, username.lower())
        throttle.check(key)
        user = self.users.by_username(username)
        if user is None or not check_password_hash(user["password_hash"], password):
            throttle.wrong(key)
            raise UnauthorizedError("Wrong username or password.")
        if not user["active"]:
            raise ForbiddenError("This account is deactivated. Ask the admin.")
        throttle.passed(key)
        return user

    def change_password(self, current_password, new_password):
        current_password = str(current_password or "")
        new_password = str(new_password or "")
        if not check_password_hash(self.user["password_hash"], current_password):
            raise ValidationError("Current password is wrong.")
        check_password_change(self.user["username"], current_password, new_password)
        self.users.set_password(self.user["id"], generate_password_hash(new_password), must_change_password=False)
        self.commit()
