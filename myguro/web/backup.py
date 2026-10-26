"""The backup download. Admin only: the file holds all the school's data, including password hashes."""

from flask import Blueprint, Response

from myguro import config
from myguro.database import get_db
from myguro.services import BackupService
from myguro.web.security import current_user, role_required_api

bp = Blueprint("backup", __name__)


@bp.get("/backup/download")
@role_required_api("admin")
def download():
    """A complete copy of the database as one file."""
    data = BackupService(get_db(), current_user()).download()
    filename = f"myguro-backup-{config.school_today().isoformat()}.db"
    return Response(data, mimetype="application/vnd.sqlite3",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})
