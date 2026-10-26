from werkzeug.security import check_password_hash, generate_password_hash

from myguro.domain import recovery as rules
from myguro.domain.accounts import check_password_change
from myguro.errors import UnauthorizedError, ValidationError
from myguro.repositories import RecoveryRepository
from myguro.services.auth import MAX_TYPED_NAME, AuthService, LoginThrottle
from myguro.services.base import Service

def plural_uses(count):
    """2 -> "2 uses", 1 -> "1 use" (for the log sentence)."""
    return f"{count} use" if count == 1 else f"{count} uses"


# Checked when nobody or nothing matches, so a wrong username takes as long to answer as a wrong code
# (otherwise the answer time would tell which usernames exist).
_DUMMY_HASH = generate_password_hash("not a real recovery code")


class RecoveryService(Service):
    """Recovery codes: a logged-in person makes (or remakes) theirs, and someone who forgot their
    password uses it to choose a new one. The code is never written to the activity log."""

    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.recovery = RecoveryRepository(db)

    def status(self):
        """Whether the logged-in person has a recovery code, when it was made (UTC) and how many uses it
        has left. has_code is False when there is none or it is used up (then a new one is needed)."""
        row = self.recovery.get(self.user["id"])
        return {"has_code": row is not None and row["uses_left"] > 0, "created_at": row["created_at"] if row else None,
                "uses_left": row["uses_left"] if row else None, "max_uses": rules.MAX_USES}

    def create(self, current_password, replace=False):
        """Make a new code for the logged-in person. Asks for the current password, so someone who finds a
        phone left logged in cannot take the account over. When the person has a code that still works,
        replace must be True (the page asks "are you sure?" first): making a new one stops the old one, and
        the question keeps it from being done by accident or over and over. A used-up code needs no
        question. The code is returned here and never again."""
        if not check_password_hash(self.user["password_hash"], str(current_password or "")):
            raise ValidationError("Current password is wrong.")
        existing = self.recovery.get(self.user["id"])
        if existing is not None and existing["uses_left"] > 0 and replace is not True:
            raise ValidationError("You already have a recovery code. Confirm that you want to replace it.")
        code = self.new_code_for(self.user["id"])
        self.log("auth.recovery_code_made", "sign-in", "Made a new recovery code.")
        self.commit()
        return {"code": code}

    def new_code_for(self, user_id):
        """Save a fresh code (as a hash) and return it as shown to the person. Does not commit."""
        code = rules.make_code()
        self.recovery.save(user_id, generate_password_hash(rules.clean_code(code)), rules.MAX_USES)
        return code

    def recover(self, username, code, new_password, ip, throttle):
        """Choose a new password with the username and the recovery code. Each use takes one of the code's
        MAX_USES; at 0 it no longer works and the person makes a new one (so a leaked code cannot be used
        for ever). The answer says how many uses are left. A wrong username, a wrong code and a used-up
        code give the same answer, count toward the same lock-out as wrong passwords, and are logged."""
        username = str(username or "").strip()
        new_password = str(new_password or "")
        if not username or not str(code or "").strip() or not new_password:
            raise ValidationError("Enter your username, your recovery code and a new password.")
        key = (ip, f"recover:{username.lower()}")
        throttle.check(key)

        user = self.users.by_username(username)
        row = self.recovery.get(user["id"]) if user is not None else None
        try:
            characters = rules.clean_code(code)
        except ValidationError:
            characters = None
        right = (user is not None and row is not None and characters is not None
                 and check_password_hash(row["code_hash"], characters) and row["uses_left"] > 0)
        if not right:
            check_password_hash(_DUMMY_HASH, characters or "x")  # takes the same time as a real check
            throttle.wrong(key)
            typed = username[:MAX_TYPED_NAME]
            actor = user if user is not None else {"id": None, "name": typed, "username": typed, "role": ""}
            auth = AuthService(self.db)
            auth.log_sign_in("auth.recovery_failed", "Wrong recovery code." if user is not None
                             else "Tried to recover an account with a username nobody has.", actor, ip)
            if throttle.is_locked(key):
                auth.log_sign_in("auth.locked", f"Locked out for {LoginThrottle.LOCK_SECONDS // 60} minutes "
                                 f"after {LoginThrottle.MAX_ATTEMPTS} wrong recovery codes.", actor, ip)
            raise UnauthorizedError("The username or the recovery code is not right.")
        if not user["active"]:
            # Said the same way as a wrong code, so this does not tell anyone the account exists
            raise UnauthorizedError("The username or the recovery code is not right.")

        check_password_change(user["username"], "", new_password)
        self.users.set_password(user["id"], generate_password_hash(new_password), must_change_password=False)
        uses_left = self.recovery.use_one(user["id"])
        throttle.passed(key)
        self.log("auth.password_recovered", "sign-in",
                 f"Chose a new password with the recovery code ({plural_uses(uses_left)} left).", actor=user, address=ip)
        self.commit()
        return {"ok": True, "uses_left": uses_left}
