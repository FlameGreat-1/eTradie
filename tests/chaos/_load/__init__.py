"""Load-test harness package.

Modules here MUST NOT import each other in ways that create cycles.
The public entry point is harness.LoadHarness; everything else is
an implementation detail.

Design constraint: every public method here MUST be async and MUST
be cancellable. A test that hits its SLO budget early should be able
to cancel the harness cleanly without leaving orphan Pods.
"""
