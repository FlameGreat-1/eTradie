"""Section 6 (CHECKLIST) test: every PrometheusRule renders cleanly.

Uses the locally-installed `helm` binary to render each chart and
asserts the new Section-6 alerts are present. CI installs helm; local
dev environments without helm get a clear skip message.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _helm_available() -> bool:
    return shutil.which("helm") is not None


def _helm_template(chart: str, *, set_args: list[str] | None = None) -> str:
    set_args = set_args or []
    cmd = [
        "helm",
        "template",
        "release",
        str(REPO_ROOT / "helm" / chart),
        "--namespace",
        "etradie-system",
    ]
    for s in set_args:
        cmd.extend(["--set", s])
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert out.returncode == 0, f"helm template {chart} failed: {out.stderr}"
    return out.stdout


pytestmark = pytest.mark.skipif(not _helm_available(), reason="helm binary not on PATH")


def test_engine_chart_renders_prometheusrule():
    rendered = _helm_template("engine", set_args=["config.mtNode.image=ghcr.io/ci-stub/etradie-mt-node"])
    # The rule we just added.
    assert "EngineBrokerInflightGateP95High" in rendered
    assert "EngineBrokerRequestDeadlineSpike" in rendered
    assert "EngineEAIdentityMismatch" in rendered
    assert "EnginePodMemoryGrowth" in rendered


def test_execution_chart_renders_prometheusrule():
    rendered = _helm_template("execution")
    assert "ExecutionOrderFailureRateHigh" in rendered
    assert "ExecutionOrderLatencyP99High" in rendered
    assert "ExecutionBurstQueueDrops" in rendered
    assert "ExecutionAuditWriteFailures" in rendered


def test_mt_node_chart_renders_memory_leak_rule():
    # PrometheusRule renders on the PLATFORM path (mtConnection.enabled=false),
    # NOT per-tenant. One namespace-scoped rule with kube_pod_labels selectors
    # covers every tenant Pod, matching the platform ServiceMonitor that scrapes
    # the same fleet. See helm/mt-node/templates/prometheusrule.yaml top comment
    # and the platform ArgoCD Application
    # (deployments/argocd/children/mt-node-{staging,production}.yaml) which sets
    # mtConnection.enabled=false.
    rendered = _helm_template(
        "mt-node",
        set_args=[
            "image.repository=ghcr.io/ci-stub/etradie-mt-node",
            "mtConnection.enabled=false",
            # externalsecret-platform.yaml uses `required` for vaultPath when
            # externalSecrets.enabled=true (the default). Provide a dummy path
            # that satisfies the guard so the full chart renders in CI. Real
            # values come from values-{staging,production}.yaml overlays.
            "externalSecrets.platform.vaultPath=etradie/services/mt-node/test",
        ],
    )
    assert "MTNodePodPending" in rendered
    assert "MTNodeMemoryLeak" in rendered
    assert "MTNodeMemorySoftCapTripFrequent" in rendered


def test_observability_logs_chart_renders():
    rendered = _helm_template("observability-logs")
    assert "kind: StatefulSet" in rendered  # Loki STS
    assert "kind: DaemonSet" in rendered  # Promtail DS
    assert "loki-config" in rendered or "loki.yaml" in rendered
    assert "promtail.yaml" in rendered
    assert "kind: NetworkPolicy" in rendered
