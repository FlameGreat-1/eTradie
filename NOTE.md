
#### Three operator actions you MUST do in the Vercel dashboard (these are settings, not files — they cannot be committed)
1. **Root Directory = `cotradee`** (this is a monorepo; the repo root is not the SPA). Without this the build fails outright.
2. **Env vars (Production):** `VITE_API_URL=https://api.exoper.com`, `VITE_API_WS_URL=wss://api.exoper.com`.
3. **Cross-origin cookie wiring (critical for login to work):** the SPA will be on a different host (`*.vercel.app` or `app.exoper.com`) than `api.exoper.com`. For the HttpOnly auth cookies to be sent, the gateway must set `AUTH_COOKIE_DOMAIN=.exoper.com`, the SPA must be served from a subdomain of `exoper.com` (use a custom domain like `app.exoper.com` in production — the bare `*.vercel.app` cannot share cookies with `api.exoper.com`), and gateway CORS must allow the SPA origin with credentials. This is backend/DNS config — if you want, I can verify the gateway's CORS + cookie-domain config next so login actually works end-to-end after deploy.

Merge !129 for the frontend code side. Want me to now verify the gateway side (CORS allow-list + `AUTH_COOKIE_DOMAIN`) against your intended Vercel domain so the auth flow is confirmed end-to-end?


The flow, correctly separated
Two independent paths once the SPA is on Vercel:

App (the 3 frontend hosts): Browser → Vercel serves the static SPA for exoper.com, www.exoper.com, app.exoper.com. These do not go through Cloudflare Tunnel → edge-ingress.
API: Browser → Cloudflare → edge-ingress → Envoy → gateway → internal services for api.exoper.com (our documented chain ).



Operator actions you must do (DNS/Vercel — can't be a file)

app.exoper.com, www.exoper.com → CNAME to Vercel (cname.vercel-dns.com).
exoper.com apex → Vercel (A 76.76.21.21 or CNAME-flattening).
api.exoper.com stays on the Cloudflare Tunnel → edge-ingress. Do NOT put any app host in the Terraform hostnames tunnel map.
Add all three app hosts in the Vercel project; optionally pick a canonical and 308-redirect the others.
Cloudflare SSL = Full (strict) or DNS-only for the app hosts, not Flexible.




Add all three as domains in the Vercel project; pick one canonical (e.g. app.exoper.com or apex) and let Vercel 308-redirect the others, OR serve all three (your call — but a canonical avoids duplicate-content SEO issues).

5. Decide a canonical host (recommendation). Serving identical SPA on 3 hosts works, but for OAuth host-consistency, cookie clarity, and SEO it's cleaner to redirect www → apex (or → app) at Vercel. Functionally all three work either way; this is a polish/SEO decision.


WHAT IS DONE:



One canonical host + 308 redirects is the industry standard because it eliminates duplicate-content SEO, cross-host session/cookie ambiguity (you have Domain=.exoper.com cookies shared across hosts), and OAuth host drift. Tightening CORS to exactly the origin that makes requests is least-privilege. Verified the gateway CORS is exact-match + credential-safe + startup-validated, so this is config-only.
Operator actions (the redirects must be set in Vercel for this to be correct)

Prod: Vercel primary = app.exoper.com; add exoper.com + www.exoper.com as 308-redirect to app.exoper.com. DNS to Vercel; api.exoper.com stays on the tunnel; Google redirect_uri = https://app.exoper.com/auth/callback/google.
Staging: staging.exoper.com is canonical on Vercel. If staging-app.exoper.com is ever created, 308-redirect it to staging.exoper.com (matches billing publicBaseUrl and gateway allowedOrigins in helm/gateway/values-staging.yaml).










Both let you `kubectl` from your workstation against the K3s cluster on the VPS.

**`ssh-add ~/.ssh/id_ed25519`** — unlocks your SSH key once per WSL boot, so commands like `ssh` and `scp` don't prompt for the passphrase every time.

**`ssh -N -L 6443:127.0.0.1:6443 etradie@...`** — opens the encrypted tunnel that lets `kubectl get pods`, `kubectl apply`, `helm install`, `argocd app sync` (every Phase 3+ command on the workstation) reach the K3s API. Without this tunnel, kubectl hangs because the VPS firewall blocks the API publicly.

**Daily use pattern after a WSL reboot:**

```bash
ssh-add ~/.ssh/id_ed25519                                  # passphrase once
ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173       # in a dedicated terminal, leave open
# then in other terminals, kubectl/helm/argocd just work
kubectl get nodes
```

That's it. Phase 3 onward needs both running.

WE ARE WORKING ON THE DEPLOYMENT FOR THE STAGING OF THE EXOPER. THE /docs/runbooks/README.md CONTAINS THE FULL DEPLOYMENT PHASES STEP BY STEP.

AND WE HAVE DONE PHASE 0, 1, 2, 3, 4 AND 5 AS YOU CAN SEE IN THE /docs/runbooks/README.md AND THE /docs/runbooks/PROGRESS.md

SO YOU EXAMINE BOTH FILES THOROUGHLY FROM THE BEGINNING TO THE END.

 EXAMINE IT  THOROUGHLY FROM  THE BEGINNING TO THE END BECAUSE YOU NEED TO UNDERSTAND AND KNOW HOW TO PICK UP FROM WHERE WE STOPPED

 SO WE ARE GOING TO START PHASE 6 THIS IS WHAT YOU SAID LAST IN THE PREVIOUS SESSION:

