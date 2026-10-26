"""Console tools for whoever runs the server."""

import os

import click
from flask import current_app
from flask.cli import with_appcontext

from myguro import backup
from myguro.database import get_db
from myguro.services import BackupService

DEFAULT_KEEP = 14


@click.command("backup")
@click.option("--to", "folder", default=None, help="Folder for the backup (default: instance/backups).")
@click.option("--keep", default=DEFAULT_KEEP, show_default=True, help="How many backups to keep. Older ones are deleted.")
@with_appcontext
def backup_command(folder, keep):
    """Write a complete copy of the database to a new file, and delete the oldest copies."""
    if keep < 1:
        raise click.ClickException("--keep must be 1 or more.")
    folder = folder or os.path.join(current_app.instance_path, "backups")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, backup.backup_name())
    backup.backup_to(current_app.config["DATABASE"], path)
    db = get_db()
    BackupService(db).record()
    db.commit()
    removed = backup.prune(folder, keep)
    click.echo(f"Backup written to {path}" + (f" ({len(removed)} old ones deleted)." if removed else "."))
