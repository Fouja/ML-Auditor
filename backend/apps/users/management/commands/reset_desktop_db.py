"""
Management command used by the desktop app to wipe the local SQLite database.

This is invoked by the Tauri sidecar (not run through ``manage.py`` directly) so
it can delete the database file even when Django has it open, then re-run
migrations and seed demo data.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Reset the ML-Auditor desktop SQLite database"

    def handle(self, *args, **options):
        db_path = Path(getattr(settings, "DESKTOP_DB_PATH", settings.DATABASES["default"]["NAME"]))
        data_dir = Path(getattr(settings, "DATA_DIR", db_path.parent))

        self.stdout.write(self.style.NOTICE(f"Resetting desktop database at {db_path}"))

        # Delete SQLite file and any WAL/SHM journal files.
        for suffix in ("", "-wal", "-shm", "-journal"):
            candidate = Path(str(db_path) + suffix)
            if candidate.exists():
                candidate.unlink()
                self.stdout.write(self.style.WARNING(f"Deleted {candidate}"))

        # Also drop the sqlite-vec virtual table file if it exists.
        vec_path = data_dir / "document_chunks_vec.vec0"
        if vec_path.exists():
            shutil.rmtree(vec_path, ignore_errors=True)
            self.stdout.write(self.style.WARNING(f"Deleted {vec_path}"))

        # Run migrations on the fresh database.
        call_command("migrate", interactive=False, verbosity=1)

        # Seed demo data if the seed script exists.
        seed_script = Path(settings.BASE_DIR).parent / "scripts" / "seed.sh"  # noqa: F841
        if seed_script.exists():
            self.stdout.write(self.style.NOTICE("Seeding demo data..."))
            result = subprocess.run(
                ["bash", str(seed_script)],
                cwd=Path(settings.BASE_DIR).parent,
                capture_output=True,
                text=True,
                env={**os.environ, "DJANGO_SETTINGS_MODULE": "config.desktop_settings"},
            )
            if result.returncode != 0:
                self.stderr.write(self.style.ERROR(f"Seed failed: {result.stderr}"))
            else:
                self.stdout.write(self.style.SUCCESS("Demo data seeded"))

        self.stdout.write(self.style.SUCCESS("Desktop database reset complete"))
