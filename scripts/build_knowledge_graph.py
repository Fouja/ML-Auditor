#!/usr/bin/env python3
"""
Build a graphify knowledge graph of the ML-Auditor codebase.

Usage:
    python scripts/build_knowledge_graph.py

Output:
    graphify-out/graph.json      - full knowledge graph
    graphify-out/graph.html      - interactive visualization
    graphify-out/GRAPH_REPORT.md - human-readable report
"""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GRAPHIFY_OUT = ROOT / "graphify-out"


def ensure_graphify() -> str:
    """Return the path to the graphify module entrypoint."""
    venv = ROOT / "backend" / "venv"
    candidates = [
        venv / "bin" / "python",
        venv / "Scripts" / "python.exe",
        Path(sys.executable),
    ]
    python = None
    for candidate in candidates:
        if candidate.exists():
            python = str(candidate)
            break
    if python is None:
        raise RuntimeError(
            "Could not find a Python interpreter. Create backend/venv first."
        )
    result = subprocess.run(
        [python, "-c", "import graphify; print('ok')"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"graphifyy is not installed for {python}. "
            "Run: {python} -m pip install -r backend/requirements.txt"
        )
    return python


def build_graph(python: str) -> None:
    """Run graphify update from the repository root."""
    os.chdir(ROOT)
    cmd = [python, "-m", "graphify", "update", str(ROOT), "--force"]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def print_summary() -> None:
    """Print a concise summary of the generated graph."""
    report = GRAPHIFY_OUT / "GRAPH_REPORT.md"
    if report.exists():
        lines = report.read_text(encoding="utf-8").splitlines()
        print("\n--- Graph Report (first 40 lines) ---")
        for line in lines[:40]:
            print(line)
        print("--- end summary ---\n")

    graph_json = GRAPHIFY_OUT / "graph.json"
    if graph_json.exists():
        size_mb = graph_json.stat().st_size / (1024 * 1024)
        print(f"Graph JSON: {graph_json} ({size_mb:.2f} MB)")
    print(f"Graph HTML: {GRAPHIFY_OUT / 'graph.html'}")


def main() -> int:
    try:
        python = ensure_graphify()
        build_graph(python)
        print_summary()
        return 0
    except Exception as exc:
        print(f"Error building knowledge graph: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
