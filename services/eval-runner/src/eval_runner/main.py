"""Eval runner CLI stub.

Phase 5 (use Opus 4.7 for tasks 5.1 + 5.3): replace this with golden-dataset loader,
LLM-judge scoring, and trend dashboards.
"""

from __future__ import annotations

import sys

from eval_runner import __version__


def main() -> int:
    print(f"clinicalscribe-eval-runner {__version__} — stub OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
