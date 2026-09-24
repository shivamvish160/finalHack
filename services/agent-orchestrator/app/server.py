"""agent-orchestrator process entrypoint.

Registers all 9 Pub/Sub push-subscription stage routes (matching
infra/modules/pubsub's topic_routes and the `/stages/*` paths every
subscription's push_config points at) on one FastAPI app. The SAME image
is deployed as 3 Cloud Run services (agent-orchestrator-alerts/-incidents/
-predictive, research.md §17) -- each instance runs the full app, but only
ever RECEIVES traffic for the topics Pub/Sub routed to its own URL, so no
runtime `--stage-family` branching is needed for correctness (T53).
"""

from __future__ import annotations

from fastapi import FastAPI

from .common.orchestrator import StageOrchestrator
from .stages import (
    alert_correlation_stage,
    executive_impact_stage,
    predictive_risk_stage,
    remediation_execute_stage,
    remediation_propose_stage,
    remediation_rejected_stage,
    retrain_forecast_model_stage,
    root_cause_stage,
    runbook_retrieval_stage,
)

app = FastAPI(title="agent-orchestrator", version="0.1.0")
_orchestrator = StageOrchestrator(app)

_orchestrator.register_stage("/stages/alert-correlation", alert_correlation_stage.handle_alerts_replay)
_orchestrator.register_stage("/stages/root-cause", root_cause_stage.handle_incidents_correlated)
_orchestrator.register_stage("/stages/runbook-retrieval", runbook_retrieval_stage.handle_root_cause_identified)
_orchestrator.register_stage("/stages/remediation-propose", remediation_propose_stage.handle_runbook_matched)
_orchestrator.register_stage("/stages/remediation-execute", remediation_execute_stage.handle_remediation_approved)
_orchestrator.register_stage("/stages/remediation-rejected", remediation_rejected_stage.handle_remediation_rejected)
_orchestrator.register_stage("/stages/predictive-risk", predictive_risk_stage.handle_predictions_tick)
_orchestrator.register_stage("/stages/executive-impact", executive_impact_stage.handle_remediation_executed)
_orchestrator.register_stage("/stages/retrain-forecast-model", retrain_forecast_model_stage.handle_retrain_tick)


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"healthy": True}
