#!/usr/bin/env python3
"""CLI-facing re-export of the durable workspace.feedback sink (hub + spokes)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.capability_adapter.feedback_sink import (  # noqa: E402
    DEFAULT_SINK_REL,
    SCHEMA,
    append_event,
    default_sink_path,
    normalize_event,
    read_events,
    validate_event,
)

__all__ = [
    "DEFAULT_SINK_REL",
    "SCHEMA",
    "append_event",
    "default_sink_path",
    "normalize_event",
    "read_events",
    "validate_event",
]
