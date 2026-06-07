# Tier 10/11 (Container & Infrastructure Security) — Operator Runbook

> Companion to `docs/security/TIER10_11_CONTAINER_INFRA_SECURITY.md`
> (design + implementation state). Step-by-step operator procedure for
> the actions that cannot be hardcoded in the repo: pinning base-image
> digests, making the digest-pin CI gate blocking, verifying published
> image signatures, and wiring admission-time verification.

---

## 1. Pin the base-image digests (one-time; then Dependabot-maintained)

The Dockerfile `FROM` lines reference base images by tag
(`alpine:3.19`, `golang:1.23-alpine`, `python:3.12-slim`,
`ubuntu:24.04`, `rust:1.88-slim-bookworm`, `debian:bookworm-slim`). Pin
them to immutable digests on a machine with Docker + registry access:

```bash
make pin-image-digests      # resolves each FROM's digest from the
                            # registry and rewrites it to
                            # FROM image:tag@sha256:<digest>
git diff                    # review the resolved pins
git add -A && git commit -m "build: pin base-image digests"
```

The digests are read from the live registry by
`scripts/pin-image-digests.sh`; they are never hand-typed. After the
pins are committed, Dependabot's `docker` ecosystem (already configured
per-Dockerfile in `.github/dependabot.yml`) opens PRs when a tag's
digest changes.

Audit locally at any time:

```bash
make check-image-digests
```

## 2. Make the digest-pin CI gate blocking

The `dockerfile-digest-pin` job in
`.github/workflows/security-scan.yml` is WARN-ONLY until step 1 is done
(a hard gate would fail every run before any digest exists). Once the
pins are committed, replace that step's `run:` body with the single
line:

```yaml
        run: bash scripts/check-image-digests.sh
```

From then on any unpinned `FROM` fails CI.

## 3. Verify a published image signature

Keyless cosign signatures verify against the GitHub OIDC issuer and the
repo's `ci.yml` workflow identity:

```bash
cosign verify \
  --certificate-identity-regexp 'https://github.com/.+/.github/workflows/ci.yml@refs/heads/main' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/flamegreat-1/etradie/<service>:<tag>
```

## 4. Wire admission-time signature verification (cluster add-on)

Verifying signatures at admission is a per-cluster policy add-on (e.g. a
Kyverno `ClusterPolicy` or the Sigstore policy-controller) that requires
a valid cosign signature for `ghcr.io/flamegreat-1/etradie/*`. Install
it on the target cluster alongside the other bootstrap add-ons (ESO,
ArgoCD, Linkerd). Do this AFTER step 1 + the first signed build so every
deployed image already carries a signature; enabling it earlier blocks
all deploys.
