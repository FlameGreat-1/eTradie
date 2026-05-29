"""Engine maintenance / operator entry points.

Modules in this package are invoked as `python -m engine.admin.<name>`
from Kubernetes Jobs / CronJobs. They share the engine image so we do
not maintain a second container, but run with their OWN ServiceAccount
and RBAC (see helm/mt-node/templates/role-snapshotter.yaml etc).
"""
