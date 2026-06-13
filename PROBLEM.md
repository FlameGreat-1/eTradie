Steps for you (repo owner):

Open docker/mt-node/README.md and follow the snippet to discover the current winehq-stable version (it'll be something like 9.0.0.0~bookworm-1).
In GitHub: Settings → Secrets and variables → Actions → New repository secret
Name: WINEHQ_VERSION, value: the resolved version string.

Optionally, also set MT5_INSTALLER_URL to your internal mirror (Artifactory/S3/Nexus) — the same guard rejects builds that depend on the public mql5.com CDN unless ETRADIE_ALLOW_PUBLIC_INSTALLER_CDN=true is set as a temporary override.


Run set -eu
FATAL: secrets.WINEHQ_VERSION must be set for main-branch mt-node builds.
       The image would otherwise install whatever winehq-stable resolves
       to today (today's 9.x; tomorrow's bump silently lands in prod).
       Discover the current value with the snippet in docker/mt-node/README.md
       and add it as a GitHub Actions repo secret.
Error: Process completed with exit code 1.
