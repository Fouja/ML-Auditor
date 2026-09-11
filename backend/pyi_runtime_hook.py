# PyInstaller runtime hook for the ML-Auditor desktop sidecar.
#
# When PyInstaller builds with console=False (GUI subsystem, no console window),
# sys.stdout and sys.stderr are None. Django's command output wrapper calls
# .write() on them and crashes with AttributeError. Give them a write-able
# devnull stream so the frozen backend boots normally; structured logs go to
# the file + Logstash TCP handlers, not stdout.

import os
import sys

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="replace")