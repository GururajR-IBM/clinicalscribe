"""Worker entrypoint. Phase 0 stub: prints a banner and exits 0.

Phase 2 will subscribe to Service Bus, run ASR/OCR, chunk, embed, write to Cosmos.
"""

from __future__ import annotations

import sys

from ingestion_worker import __version__


def main() -> int:
    print(f"clinicalscribe-ingestion-worker {__version__} — stub OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
