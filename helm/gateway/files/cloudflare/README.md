# helm/gateway/files/cloudflare

The two CIDR files in this directory are the **chart-local** copy of the
source-of-truth Cloudflare published origin ranges committed at
`deployments/cloudflare/ip-ranges/`. Helm forbids `.Files.Get` from
reading outside the chart directory, so they are duplicated here.

## Drift policy

These files MUST stay byte-identical to
`deployments/cloudflare/ip-ranges/{ipv4,ipv6}.txt`. The weekly CI job
(`deployments/cloudflare/scripts/refresh-cloudflare-ips.sh`) writes
both locations atomically. A pre-commit hook + a CI gate enforce the
invariant.

Do NOT edit these files by hand. If you need to add a CIDR, edit the
canonical files at `deployments/cloudflare/ip-ranges/` and let the
refresh job propagate the change here.

## Why duplicated

- The canonical files are the artefact the **operator** sees first when
  inspecting the trust-chain (alongside the AOP CA).
- The chart-local copies are what `.Files.Get` reads at
  `helm template` / `helm install` time.
- Reconciliation between the two is mechanical (a CI gate diffs them);
  it is not a human-merge problem.
