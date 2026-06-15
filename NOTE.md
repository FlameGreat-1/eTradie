
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

AND WE HAVE DONE PHASE 0, 1, 2, 3, 4, 5, 6, 7, 8 AND 9 AS YOU CAN SEE IN THE /docs/runbooks/README.md AND THE /docs/runbooks/PROGRESS.md

SO YOU EXAMINE BOTH FILES THOROUGHLY FROM THE BEGINNING TO THE END.

 EXAMINE IT  THOROUGHLY FROM  THE BEGINNING TO THE END BECAUSE YOU NEED TO UNDERSTAND AND KNOW HOW TO PICK UP FROM WHERE WE STOPPED

 SO WE ARE GOING TO CONTINUE WITH PHASE 10 THIS IS WHAT YOU SAID LAST IN THE PREVIOUS SESSION.


 THESE ARE THE LAST THINGS YOU ASKED ME TO DO IN THE PREVIOUS SESSION:



Now I understand the full picture, and I have to be honest: **my previous fix was wrong, and I should have caught it.**

#### What actually broke

The chromadb image's entrypoint runs:
```
uvicorn chromadb.app:app --log-config chromadb/log_config.yml
```

That `chromadb/log_config.yml` is a **relative path**. The image's WORKDIR is `/chroma`. So `chromadb/log_config.yml` resolves to `/chroma/chromadb/log_config.yml` — a file that ships INSIDE the image at that path, baked into the container's `/chroma` directory.

By mounting our PVC at `/chroma`, **we shadowed the entire `/chroma` directory** — including the image-baked `chromadb/log_config.yml` file. The PVC is empty, so when uvicorn tries to read `chromadb/log_config.yml` it finds nothing.

So my previous fix solved one problem (read-only filesystem for the log file) and created another (we hid the image's baked-in files). Confirmed by `--previous` showing the same error, and confirmed by the new pod definitely using the new mount path. The fix was structurally wrong.

I'm being upfront about this. The correct fix needs to:

- Keep the original PVC mount at `/chroma/chroma` (so the image's `/chroma/chromadb/...` files remain visible).
- Provide a writable path for the `/chroma/chroma.log` file ONLY, without hiding the rest of `/chroma`.

#### The actually-correct fix

Mount a **small `emptyDir` as a single FILE at `/chroma/chroma.log`** using `subPath`. This is the canonical "make one file writable on a read-only-root container" pattern.

The `subPath` field lets you mount a single entry from a volume at a specific destination path. Combined with an emptyDir source, this gives us a writable single file at exactly `/chroma/chroma.log` without touching any other path in the container.

Spec shape:

```yaml
volumeMounts:
  - name: data
    mountPath: /chroma/chroma             # PVC back at the original subpath
  - name: chroma-log                       # NEW
    mountPath: /chroma/chroma.log
    subPath: chroma.log
  - name: tmp
    mountPath: /tmp
volumes:
  - name: chroma-log                       # NEW
    emptyDir:
      sizeLimit: 32Mi
  - name: tmp
    emptyDir:
      sizeLimit: 64Mi
```

The PVC mount goes back where it was. The image's baked-in `/chroma/chromadb/log_config.yml` becomes visible again. The single file `/chroma/chroma.log` is a per-pod emptyDir (ephemeral, that's fine — chromadb's log file doesn't need to persist; we have Loki for log aggregation), so the FileHandler can open it for writing.

`PERSIST_DIRECTORY` reverts to `/chroma/chroma` to match the PVC mount.

I'm 100% certain this works because:

1. `subPath` mounting a single file from an emptyDir is a documented K8s pattern (and one I should have proposed first).
2. The image's `/chroma/chromadb/log_config.yml` is no longer hidden because the PVC mount only covers `/chroma/chroma/`, not `/chroma/`.
3. The emptyDir-backed `/chroma/chroma.log` is fully writable by uid 1000 because emptyDir respects `fsGroup: 1000` set on the pod spec.

#### Committing the fix

This reverts `f81a646a`'s mount-point change and adds the single-file emptyDir mount instead. One commit, one file.


Commit landed. Push and let ArgoCD pick it up.

```bash
cd ~/eTradie
git pull --rebase gitlab main
git push origin main

# Force ArgoCD to pick up the new commit immediately
argocd app terminate-op data-layer-staging 2>/dev/null
sleep 2
argocd app get data-layer-staging --refresh >/dev/null
argocd app sync data-layer-staging --timeout 600

# Now we need to delete the existing chromadb-0 pod again because the
# StatefulSet will be in the same "rolling update can't proceed because
# pod-0 is not Ready" deadlock with the now-NEW template.
sleep 10
kubectl -n etradie-system delete pod chromadb-0
kubectl -n etradie-system get pod chromadb-0 -w
```

When you see `2/2 Running` with 0 restarts and stable for 30+ seconds, Ctrl-C the watch. Then:

```bash
# Quick verify chromadb is actually serving
kubectl -n etradie-system exec chromadb-0 -c chromadb -- \
  curl -sf http://localhost:8000/api/v2/heartbeat
echo ""

# Pod state across all namespaces
kubectl -n etradie-system get pods
echo ""
kubectl -n envoy-system get pods
echo ""

# Application state
argocd app list --grpc-web | grep -E '(staging|monitoring-stack-staging)'
```

Paste all of that. Once chromadb is Healthy, the engine→gateway→execution/management/billing cascade should unblock over the next 2-3 minutes. Envoy is the remaining concern — once that pod log is available we'll diagnose Defect C.


