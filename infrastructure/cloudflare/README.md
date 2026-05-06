# infrastructure/cloudflare

Provisions Cloudflare zone settings and DNS records that publish the
eTradie platform via Cloudflare Tunnel.

## What it owns

* Cloudflare zone TLS posture (min TLS 1.2, TLS 1.3 on, always-https,
  strict SSL).
* Authenticated Origin Pulls (AOP) at the zone level (defence-in-depth
  on top of Tunnel).
* DNS records (`api.exoper.com`, `*.exoper.com`, etc.) that CNAME
  to the Cloudflare Tunnel UUID (`<id>.cfargotunnel.com`).

## What it does NOT own

* The Cloudflare Tunnel itself — create that in the Cloudflare Zero
  Trust UI (or via `cloudflare_zero_trust_tunnel` resource in a
  wrapper module). The Tunnel `token` lives in Vault at
  `etradie/services/edge-ingress/<env>/cloudflare/tunnel`; the
  cloudflared pod (in the edge-ingress chart) reads it via ESO.
* The AOP CA bytes — those live in Vault, populated by the operator.
* Any Kubernetes manifest.
* Any AWS / OCI / cloud-IaaS resource. The platform is
  cloud-LB-agnostic; Tunnel removes the entire LB layer.

## Apply

Apply AFTER:
  1. The Cloudflare Tunnel is created in Zero Trust (you'll have a
     UUID and a token).
  2. The Tunnel UUID is known so it can be passed as the CNAME target
     in the `hostnames` map.

```bash
cd infrastructure/cloudflare
terraform init
terraform apply \
  -var environment=production \
  -var zone_id=<...> \
  -var 'hostnames={ "api.exoper.com" = "<tunnel-id>.cfargotunnel.com", "app.exoper.com" = "<tunnel-id>.cfargotunnel.com" }'
```

The Tunnel token must also be written to Vault before the
edge-ingress chart is reconciled by ArgoCD (see
`infrastructure/cluster/bootstrap/README.md` step 5).
