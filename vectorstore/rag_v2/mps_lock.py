"""One lock for every local model call.

Apple MPS aborts the process if two command buffers are encoded concurrently
on the same device (``A command encoder is already encoding ...``). The warm-up
thread and the first request can overlap, so all embedding/reranker inference
is serialized through this RLock.
"""
from __future__ import annotations

import threading

MODEL_LOCK = threading.RLock()
