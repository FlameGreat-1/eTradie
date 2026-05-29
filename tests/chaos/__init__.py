"""Chaos and soak tests for the eTradie self-hosted MT node layer.

Covers CHECKLIST Section 1 (terminal lifecycle, memory, CPU),
Section 2 (broker connectivity), and Section 10 (load + chaos +
recovery). Designed to run on three cadences:

  - CI per-PR  : 30-min soak  (`make mt-node-soak`)
  - nightly    : 24-hour soak (`make mt-node-soak-nightly`)
  - weekly     : 72-hour soak (operator-triggered)

Unit tests in this directory use kubernetes_asyncio's fake-client
harness and skip when K8s API access is not available.
"""
