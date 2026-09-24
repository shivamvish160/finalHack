"""alert-replay-service process entrypoint.

Cloud Run Services must listen on $PORT; the replay loop itself is a
long-running publisher with no request/response shape, so it runs in a
background thread while a minimal FastAPI app satisfies Cloud Run's health
check / listening requirement.
"""

from __future__ import annotations

import os
import threading

from fastapi import FastAPI

from .replay import run_replay_loop

app = FastAPI(title="alert-replay-service", version="0.1.0")
_replay_thread: threading.Thread | None = None


@app.on_event("startup")
async def _start_replay_loop() -> None:
    global _replay_thread
    target_rate = int(os.environ.get("ALERT_REPLAY_TARGET_MSGS_PER_MINUTE", "1000"))
    _replay_thread = threading.Thread(target=run_replay_loop, args=(target_rate,), daemon=True)
    _replay_thread.start()


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"healthy": _replay_thread is not None and _replay_thread.is_alive()}
