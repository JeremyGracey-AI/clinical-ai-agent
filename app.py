"""Hugging Face Spaces / local entrypoint.

Adds ``src/`` to the path so ``clinical_agent`` imports on HF Spaces (which runs
app.py directly without ``pip install -e .``). Harmless when the package is already
installed locally.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from clinical_agent.ui.layout import build_demo  # noqa: E402

if __name__ == "__main__":
    build_demo().launch()
