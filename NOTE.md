Confirmed: the EA's only includes are `<Zmq/Zmq.mqh>` and `<JAson.mqh>` — both external (mql-zmq + JAson), neither in the repo. The EA has no direct `#import`; the `libzmq.dll` import lives inside mql-zmq's `Zmq.mqh`. So the dependency set is exactly: **mql-zmq (provides `Zmq/*.mqh` + `libzmq.dll`) and `JAson.mqh`.**

#### Direct answer to your question, settled

**No, we do not regenerate the portable MT5/MT4 zips.** Those are correct and stay as-is. The fix adds three small things on top, via the Dockerfile (same mechanism as the already-working `.ex5`/`.ex4` copy):

1. `libzmq.dll` → into the prefix so the EA's import resolves at runtime.
2. The `Zmq` MQL include tree → `MQL5/Include/Zmq/` (and MT4 `MQL4/Include/Zmq/`).
3. `JAson.mqh` → `MQL5/Include/` (and MT4).

#### The honest blocker before I can write the fix

These files come from **external projects** that are **not in your repo**:
- mql-zmq: `github.com/dingmaotu/mql-zmq` (ships `Include/Zmq/*.mqh` and a prebuilt `libzmq.dll`)
- JAson: `github.com/sierkov/JAson` → `JAson.mqh`

I cannot fetch external URLs, and I won't guess at the DLL's exact name/bitness or vendor random binaries. To do this as real engineering (not assumption), the correct path is:

**You provide the mql-zmq + JAson files** (you already have them — the EA was compiled against them to produce the committed `.ex5`). Specifically I need, placed into the repo so the Dockerfile can bake them deterministically (sha-pinned, like everything else):
- `libzmq.dll` — **both** the 64-bit (for MT5/terminal64.exe) and 32-bit (for MT4/terminal.exe) builds. The bitness must match the terminal.
- the `Zmq/` include folder (`.mqh` files)
- `JAson.mqh`

Two ways to get them, your call:
- **(A)** You drop those files onto the workstation, I tell you the exact repo paths to commit them to (`docker/mt-node/ea/deps/` is the natural home), then I write the Dockerfile copy + a build-time `libzmq.dll`-present assertion (mirroring the #13 terminal check). Deterministic, sha-pinned, no portable re-zip.
- **(B)** Since you generated the portable on a workstation with Wine, the cleaner long-term option is to **add mql-zmq + JAson into that workstation's MT5 prefix, recompile the EA there against build 5836, and include `MQL5/Libraries/libzmq.dll` + includes when you zip** — but that *would* mean re-zipping, which you don't want. So **A is better**: keep the zips, layer the deps via Dockerfile.

One critical correctness point I must flag (not a guess — a known MQL fact): **the committed `ZeroMQ_EA.ex5` was compiled against some specific MT5 build.** If that build differs materially from the baked `5836`, the `.ex5` can still fail to load even with `libzmq.dll` present. The robust fix bakes the **source** (`ZeroMQ_EA.mq5` + the includes) and lets MT5 compile it on first boot (which explains the "full recompilation" we keep seeing — MT5 *is* trying to compile, but the includes are missing so it can't). That actually ties everything together: **the per-boot recompile fails silently because `Zmq.mqh`/`JAson.mqh` are absent**, so the EA never produces a loadable `.ex5`.

So the precise question that decides the implementation: **do you want to ship the prebuilt `.ex5` + `libzmq.dll` (faster boot, but `.ex5` must match build 5836), or ship the source `.mq5` + includes + `libzmq.dll` and let MT5 compile on boot (robust across builds, matches the observed recompile behavior)?**

Tell me which, and provide the mql-zmq + JAson files (option A). Then I write the Dockerfile fix grounded entirely in real files, no assumptions, no portable re-zip.


#### What the problem is, in one line

The MT terminal runs, but the ZeroMQ EA cannot start because its runtime dependency `libzmq.dll` (and its MQL includes) were never put into the image, so nothing ever binds `:5555` and the pod never goes Ready.

#### What needs to be done (the fix, conceptually)

Add the EA's three missing dependencies into the mt-node image so the EA can load and bind its socket:
1. **`libzmq.dll`** — the ZeroMQ runtime library the EA imports (needs **both** a 64-bit build for MT5 and a 32-bit build for MT4).
2. **The `Zmq` MQL include folder** (the `.mqh` files from mql-zmq).
3. **`JAson.mqh`** (the JSON parser include).

These go into the repo (sha-pinned, deterministic), and the Dockerfile copies them into the baked Wine prefix at the paths MT searches. **The portable MT5/MT4 zips do NOT change** — this is layered on top via the Dockerfile, exactly like the existing `.ex5`/`.ex4`.

---

#### Operator runbook — exact steps

**Step 1 — Obtain the dependency files (one-time, on the workstation).**

Get the two external libraries the EA was built against:

- **mql-zmq** from `https://github.com/dingmaotu/mql-zmq`
  - Provides the `Include/Zmq/` folder (`.mqh` headers) and prebuilt `libzmq.dll` binaries under its `Library/MT5/` and `Library/MT4/` folders.
- **JAson** from `https://github.com/vivazzi/JAson` (or sierkov's fork) — the single file `JAson.mqh`.

You need, specifically:
- `libzmq.dll` **64-bit** (for MT5 / `terminal64.exe`)
- `libzmq.dll` **32-bit** (for MT4 / `terminal.exe`)
- the `Zmq/` include directory (all `.mqh`)
- `JAson.mqh`

**Step 2 — Decide: prebuilt EA vs compile-on-boot.**

There are two valid designs; pick one (this affects what gets committed):

- **Option A — ship source, let MT5 compile it.** Commit the EA **source** (`ZeroMQ_EA.mq5`/`.mq4`) + the `Zmq` includes + `JAson.mqh` + `libzmq.dll` into the prefix. MT5 compiles the EA on first boot. Robust across MT builds (this also explains the "full recompilation" we kept seeing — MT was trying to compile but the includes were missing). **Recommended.**
- **Option B — ship prebuilt `.ex5`/`.ex4`.** Keep the committed compiled EA, just add `libzmq.dll` at runtime. Faster boot, but the `.ex5` must be build-compatible with the baked MT5 (build 5836) or it silently fails to load — a fragility risk.

**Step 3 — Place the files in the repo** (so the build is deterministic and sha-pinned). Proposed layout:
```
docker/mt-node/ea/deps/
  mt5/libzmq.dll          # 64-bit
  mt4/libzmq.dll          # 32-bit
  Include/Zmq/            # mql-zmq .mqh headers
  Include/JAson.mqh
```
(For Option A also ensure the EA source is available to copy; for Option B the existing `ZeroMQ_EA.ex5/.ex4` stay where they are.)

**Step 4 — Dockerfile change** (engineer/agent does this once the files are committed). The Dockerfile will, inside the baked Wine template (`$WINE_TEMPLATE/.../MetaTrader 5` and `MetaTrader 4`):
- copy `libzmq.dll` into `MQL5/Libraries/` (MT5, 64-bit) and `MQL4/Libraries/` (MT4, 32-bit) — the directory MT searches for `#import` DLLs;
- copy the `Zmq/` includes into `MQL5/Include/Zmq/` and `MQL4/Include/Zmq/`;
- copy `JAson.mqh` into `MQL5/Include/` and `MQL4/Include/`;
- add a **build-time assertion** that `libzmq.dll` exists in both Libraries dirs (mirrors the defect #13 `terminal64.exe` assertion) so a future image can never ship without it.

**Step 5 — Rebuild + roll** (the established defect #13 flow, no portable re-zip):
- push `main` → GitHub → CI builds a new mt-node image → `deploy-bump` pins the new SHA.
- confirm: `kubectl -n etradie-system exec deploy/etradie-engine -c engine -- printenv MT_NODE_IMAGE` shows the new SHA.

**Step 6 — Clean + re-provision + verify on the tenant pod:**
```bash
# remove the manual probe override left on the StatefulSet, and clean the failed tenant
kubectl -n etradie-system set env statefulset/etradie-mt-cf6e2e6b-b80 -c watchdog WATCHDOG_MAX_FAILURES-
kubectl -n etradie-system delete statefulset,svc,sa,configmap,pvc -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE status IN ('failed','provisioning') RETURNING id;"
# re-provision FROM THE DASHBOARD (connection_type=hosted, MT5 Deriv-Demo), then:
CONN=$(kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -t -A -c \
  "SELECT left(id::text,12) FROM broker_connections ORDER BY created_at DESC LIMIT 1;")
POD=etradie-mt-${CONN}-0
kubectl -n etradie-system exec $POD -c mt-node -- sh -c 'find /home/mt/.wine/prefix -iname "libzmq*.dll"'        # must be present
kubectl -n etradie-system exec $POD -c mt-node -- sh -c 'ls "/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs"'  # EA ran
kubectl -n etradie-system exec $POD -c mt-node -- sh -c 'ss -ltn | grep 5555'                                    # socket bound
```

**Success =** `libzmq.dll` present, `MQL5/Logs/` exists with an EA OnInit line, `:5555` LISTEN, watchdog reports `mt5_connected=1` + `authenticated=1`, pod `3/3 Ready`.

---

#### The one decision that unblocks everything

I need you to choose **Option A (compile-on-boot from source)** or **Option B (prebuilt .ex5)**, and provide the mql-zmq + JAson files so they can be committed. My strong recommendation is **Option A** — it's why MT5 keeps doing "full recompilation," it's robust across MT builds, and it removes the build-version fragility of the prebuilt `.ex5`.

Once you tell me A or B and the dep files are in the repo, the Dockerfile change + build-time assertion is a single commit, then the rebuild/re-provision above runs to completion. No portable MT re-zip required.