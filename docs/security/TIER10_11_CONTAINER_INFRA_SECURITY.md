# 🔴 TIER 10 & 11: Container & Infrastructure Security — Remediation

> Status: **IMPLEMENTED** on branch `tier10-11-hardening`.
>
> Operator procedure: see
> `docs/runbooks/tier10-11-container-supply-chain.md`.
>
> Scope: the container-supply-chain and service-hardening gaps found in
> the Tier 10/11 audit. Each item below is wired end to end; the items
> that require live-registry data (base-image digest pinning) ship as
> runnable tooling plus the runbook, never as hand-written hashes.

## Progress tracker (this branch)

- [x] **gRPC reflection gated to non-production.** gateway, execution,
      and management registered gRPC server reflection unconditionally,
      leaking the full service descriptor on :50052 / :50053 / :50054.
      Each service now registers reflection only when
      `Config.IsProdLike()` is false. `IsProdLike()` is a single
      accessor per config (gateway delegates to the existing
      `isProdLikeEnv()`; execution/management read the `AppEnv` value
      `validate()` already normalises).
- [x] **Go runtime images pinned to numeric non-root UID + HEALTHCHECK.**
      gateway/execution/management/billing created their user with
      `adduser -S`, yielding a non-deterministic Alpine system UID that
      did not match the charts' `securityContext.runAsUser: 65532`. All
      four now use `USER 65532:65532` with `COPY --chown=65532:65532`
      and a `HEALTHCHECK` against their real `/health` port
      (gateway 8080, execution 8080, management 8083, billing 8082).
- [x] **Trivy image-layer scan.** `security-scan.yml` gained a
      `trivy-image` matrix job that builds each Go service image locally
      and runs `scan-type: image` on the assembled layers (fixable
      HIGH/CRITICAL gate). The pre-existing `fs` scan is unchanged.
- [x] **Image signing + provenance + SBOM.** `ci.yml` build job now
      emits build provenance and SBOM attestations and signs every
      pushed image with cosign keyless (GitHub OIDC → Fulcio/Rekor, no
      stored key). Signing is BY DIGEST, so the git-SHA tag and the
      RELEASE_TAG ref (same digest) are both covered.
- [x] **Base-image digest-pinning mechanism.** `scripts/pin-image-digests.sh`
      (resolver) + `scripts/check-image-digests.sh` (gate) +
      `make pin-image-digests` / `make check-image-digests` + a
      warn-only `dockerfile-digest-pin` CI job. The literal `@sha256`
      digests are produced by the resolver against the registry — the
      operator materialises and commits them per the runbook, after
      which Dependabot's `docker` ecosystem keeps them current.

## Notes

- **Admission-time signature verification** (requiring a valid cosign
  signature before a Pod is admitted) is a per-cluster policy add-on
  (e.g. Kyverno or the Sigstore policy-controller). It is installed on
  the target cluster alongside the other bootstrap add-ons (ESO,
  ArgoCD, Linkerd), not in CI, because it is environment-specific. The
  runbook covers wiring it after the images are signed.
