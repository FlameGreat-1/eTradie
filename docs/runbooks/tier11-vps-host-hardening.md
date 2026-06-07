# Tier 11 (Infrastructure Security) — Self-Managed VPS Host-Hardening Runbook

> Companion to `docs/security/TIER10_11_CONTAINER_INFRA_SECURITY.md` and
> `infrastructure/cluster/bootstrap/README.md`. Applies to the
> SELF-MANAGED cluster path only: Contabo K3s, kubeadm, or bare-metal
> hosts the operator brings. On the OCI OKE path
> (`infrastructure/cluster/oci/`) node hardening is delegated to the
> managed OKE node image and this runbook is not required.
>
> Run every step on EACH host BEFORE installing K3s / kubeadm (step 0
> of the bootstrap README). These controls satisfy the Tier 11
> "Server Hardening" and "VPN admin access" checklist items:
> SSH key-only authentication, password login disabled, fail2ban, host
> firewall, and private (non-public) admin access to the K8s API.

---

## Network model this runbook assumes

The platform publishes exclusively via **Cloudflare Tunnel**
(`infrastructure/README.md`): cloudflared dials OUTBOUND to Cloudflare,
so **no inbound public port is needed for application traffic**. The
only inbound the host must accept from outside is the operator's SSH,
and even that should be restricted. The Kubernetes API (6443) MUST NOT
be exposed to the internet; operator `kubectl` reaches it over an SSH
tunnel or VPN (see section 5).

## 1. SSH key-only authentication + password login disabled

Provision the operator public key before locking down, or you will be
locked out:

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
# paste the operator's public key:
echo 'ssh-ed25519 AAAA... operator@etradie' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Harden `sshd`. Write a drop-in so a package update to the main config
does not silently revert it:

```bash
sudo tee /etc/ssh/sshd_config.d/10-etradie-hardening.conf >/dev/null <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 20
X11Forwarding no
AllowAgentForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

# Validate config BEFORE restarting, then restart.
sudo sshd -t
sudo systemctl restart ssh   # 'sshd' on some distros
```

Verify from a SECOND session (keep the first open) that password auth
is refused and key auth works:

```bash
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no operator@HOST   # must fail
ssh operator@HOST                                                                  # must succeed
```

## 2. fail2ban (sshd jail)

```bash
sudo apt-get update && sudo apt-get install -y fail2ban   # Debian/Ubuntu (Contabo default)

sudo tee /etc/fail2ban/jail.d/sshd.local >/dev/null <<'EOF'
[sshd]
enabled = true
mode = aggressive
maxretry = 3
findtime = 10m
bantime = 1h
bantime.increment = true
bantime.maxtime = 1w
EOF

sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

## 3. Host firewall (nftables)

Default-deny inbound; allow only loopback, established/related, ICMP,
SSH, and the K3s intra-node ports (only required when the cluster has
more than one node — single-node K3s can drop the cluster-port rules).
No application port is opened inbound because Cloudflare Tunnel is
outbound-only.

```bash
sudo tee /etc/nftables.conf >/dev/null <<'EOF'
#!/usr/sbin/nft -f
flush ruleset

table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;

    iif "lo" accept
    ct state established,related accept
    ct state invalid drop
    ip protocol icmp accept
    ip6 nexthdr ipv6-icmp accept

    # SSH (admin). Tighten 'ip saddr' to the operator/VPN CIDR.
    tcp dport 22 ct state new accept

    # ---- K3s intra-node ports (MULTI-NODE clusters only) ----
    # Restrict 'ip saddr' to the node subnet; never leave open to 0.0.0.0/0.
    # 6443 = API server, 8472/udp = flannel VXLAN, 10250 = kubelet,
    # 2379-2380 = etcd (HA only).
    # tcp dport 6443 ip saddr <NODE_CIDR> accept
    # udp dport 8472 ip saddr <NODE_CIDR> accept
    # tcp dport 10250 ip saddr <NODE_CIDR> accept
    # tcp dport { 2379, 2380 } ip saddr <NODE_CIDR> accept
  }
  chain forward { type filter hook forward priority 0; policy drop; }
  chain output  { type filter hook output  priority 0; policy accept; }
}
EOF

sudo systemctl enable --now nftables
sudo nft -f /etc/nftables.conf
sudo nft list ruleset
```

> The CNI (flannel/Calico) manages its own pod-traffic chains; the
> `forward` policy-drop above does not interfere because the CNI inserts
> ACCEPT rules at a higher priority. Verify pod-to-pod traffic after
> applying on a multi-node cluster.

### ufw equivalent (if the host already uses ufw)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw limit 22/tcp                       # rate-limited SSH
# Multi-node only, restricted to the node subnet:
# sudo ufw allow from <NODE_CIDR> to any port 6443 proto tcp
# sudo ufw allow from <NODE_CIDR> to any port 8472 proto udp
# sudo ufw allow from <NODE_CIDR> to any port 10250 proto tcp
sudo ufw enable
sudo ufw status verbose
```

## 4. K8s API must stay private

Do NOT bind the K3s API server to a public address or open 6443 to
`0.0.0.0/0`. On K3s, install with the API advertised on the private
interface only:

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--tls-san <PRIVATE_IP> --advertise-address <PRIVATE_IP> --node-ip <PRIVATE_IP>" sh -
```

If the host has only a public NIC, keep 6443 closed in the firewall
(section 3 leaves it closed by default) and reach the API via section 5.

## 5. VPN / SSH-tunnel admin access (instead of a public API)

Operator `kubectl` reaches the private API without exposing 6443:

- **SSH local-forward** (no extra infra):
  ```bash
  ssh -N -L 6443:127.0.0.1:6443 operator@HOST
  # point KUBECONFIG's server at https://127.0.0.1:6443
  ```
- **Or a WireGuard VPN** terminating on the host/node subnet; then the
  firewall rule in section 3 allows 6443 only from the VPN CIDR.

Either way the API server is never internet-facing, satisfying the
Tier 11 "VPN admin access" control.

## 6. Verification checklist

```bash
sshd -T | grep -E 'passwordauthentication|permitrootlogin|pubkeyauthentication'
# passwordauthentication no / permitrootlogin prohibit-password / pubkeyauthentication yes
sudo fail2ban-client status sshd            # jail active
sudo nft list ruleset | grep 'policy drop'  # input + forward default-deny
ss -tlnp | grep ':6443' || echo 'API not listening publicly'  # must NOT show 0.0.0.0:6443
```
