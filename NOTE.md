
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









grep -E '^[A-Z][A-Z0-9_]*=' ~/eTradie/.env | cut -d= -f1 | sort -u
