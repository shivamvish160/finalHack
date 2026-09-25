"""Custom Pub/Sub-driven agent orchestrator dispatcher (T17).

Composes the 6 ADK agents via plain `LlmAgent` + `Runner.run_async` calls,
NOT ADK's deprecated `SequentialAgent`/`ParallelAgent`/`LoopAgent`
(research.md §5, design.md §3.2). Each stage is its own Pub/Sub push
subscription handler; this module provides the shared "invoke the agent,
then enforce BigQuery-write-then-Firestore-then-publish-next-event
ordering" scaffold every stage in services/agent-orchestrator/app/stages/
builds on.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import FastAPI, Request
from google.cloud import pubsub_v1

# Every stage handler is a plain, synchronous function (blocking BigQuery/
# Firestore client calls, no real async I/O) -- dispatched via
# asyncio.to_thread below so one slow handler can't block the whole event
# loop and starve Cloud Run's configured request concurrency.
StageHandler = Callable[[dict[str, Any]], dict[str, Any] | list[dict[str, Any]] | None]


@dataclass(frozen=True)
class PubSubPushEnvelope:
    """Shape of a Cloud Run Pub/Sub push subscription request body."""

    message_id: str
    publish_time: str
    data: dict[str, Any]
    attributes: dict[str, str]

    @classmethod
    def from_request_body(cls, body: dict[str, Any]) -> "PubSubPushEnvelope":
        message = body["message"]
        raw_data = base64.b64decode(message.get("data", "")).decode("utf-8") if message.get("data") else "{}"
        return cls(
            message_id=message["messageId"],
            publish_time=message["publishTime"],
            data=json.loads(raw_data),
            attributes=message.get("attributes", {}),
        )


class StageOrchestrator:
    """Registers one FastAPI POST route per Pub/Sub push subscription.

    Each registered `handler` is responsible for its own
    BigQuery-write -> Firestore-projection -> publish-next-event ordering
    (design.md §3.2/§8); this class only handles envelope decoding, ack
    semantics, and next-topic publishing so every stage doesn't repeat that
    boilerplate.
    """

    def __init__(self, app: FastAPI, project_id: str | None = None) -> None:
        self._app = app
        self._project_id = project_id or os.environ["GCP_PROJECT_ID"]
        self._publisher = pubsub_v1.PublisherClient()

    def register_stage(self, route_path: str, handler: StageHandler, next_topic: str | None = None) -> None:
        @self._app.post(route_path)
        async def _endpoint(request: Request) -> dict[str, str]:  # noqa: ANN202
            body = await request.json()
            envelope = PubSubPushEnvelope.from_request_body(body)
            # Every stage handler expects a flat dict of the envelope's
            # inner `payload` fields (e.g. sourceAlert) PLUS the envelope's
            # own `incidentId` (a sibling of `payload`, not nested inside
            # it, per contracts/pubsub-events.md) -- merge them here once
            # rather than making every handler unwrap the envelope itself.
            merged_payload = dict(envelope.data.get("payload") or {})
            merged_payload["incidentId"] = envelope.data.get("incidentId")
            result = await asyncio.to_thread(handler, merged_payload)
            # `next_topic` forwards the handler's own {"incidentId", "payload"}
            # return value(s) to the next stage in the pipeline -- a handler
            # may process >1 incident per call (e.g. alert correlation) and
            # return a list, or a single dict, or None (nothing to forward,
            # e.g. a below-threshold runbook match or a terminal stage).
            if next_topic and result:
                for item in result if isinstance(result, list) else [result]:
                    self.publish(next_topic, item)
            # Returning 200 acks the message; an unhandled exception in
            # `handler` propagates as a 500, triggering Pub/Sub redelivery
            # and eventually the topic's -dlq after 5 attempts (NFR-012).
            return {"status": "ok"}

    def publish(self, topic_name: str, payload: dict[str, Any]) -> str:
        topic_path = self._publisher.topic_path(self._project_id, topic_name)
        future = self._publisher.publish(topic_path, json.dumps(payload).encode("utf-8"))
        return future.result()
