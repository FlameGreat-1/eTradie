{{/*
Helm helpers for the etradie-mt-node chart. Pattern mirrors
helm/engine/templates/_helpers.tpl and helm/execution/templates/_helpers.tpl
so operator muscle memory transfers.
*/}}

{{- define "mt-node.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "mt-node.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "mt-node.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "mt-node.namespace" -}}
{{- default "etradie-system" .Values.namespace.name -}}
{{- end -}}

{{/*
appName is hard-pinned to etradie-mt-node so the engine NetworkPolicy
egress selector and Prometheus discovery stay stable regardless of
release name (which embeds the per-user connection_id).
*/}}
{{- define "mt-node.appName" -}}
etradie-mt-node
{{- end -}}

{{/*
Full label set. Includes per-tenant connection-id + user-id so an
operator can `kubectl get sts -l etradie.connection-id=<id>`.
Validation of those values lives in mt-node.preflight.
*/}}
{{- define "mt-node.labels" -}}
helm.sh/chart: {{ include "mt-node.chart" . }}
{{ include "mt-node.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: etradie
app.kubernetes.io/component: mt-node
etradie.connection-id: {{ .Values.mtConnection.connectionId | quote }}
etradie.user-id: {{ .Values.mtConnection.userId | quote }}
etradie.platform: {{ .Values.mtConnection.platform | quote }}
{{- end -}}

{{/*
SelectorLabels are the IMMUTABLE subset used in spec.selector. Adding
etradie.connection-id here pins the StatefulSet to exactly this
release's Pods - critical so a label-overlap across releases is
impossible.
*/}}
{{- define "mt-node.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mt-node.appName" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
etradie.connection-id: {{ .Values.mtConnection.connectionId | quote }}
{{- end -}}

{{- define "mt-node.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "mt-node.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "mt-node.platformSecretName" -}}
{{ include "mt-node.fullname" . }}-platform
{{- end -}}

{{- define "mt-node.watchdogConfigMapName" -}}
{{ include "mt-node.fullname" . }}-watchdog
{{- end -}}

{{/*
Vault role bound to this tenant's ServiceAccount. The Kubernetes
auth backend role is created by
infrastructure/cluster/vault-paths/mt_node_tenant_secrets.tf and is
bound to SA names matching the glob etradie-mt-* in the chart's
namespace. Operators may override per-cluster by setting
.Values.vault.role.
*/}}
{{- define "mt-node.vaultRole" -}}
{{- default "mt-node-tenant" .Values.vault.role -}}
{{- end -}}

{{/*
Vault KV-v2 path holding this tenant's broker credentials. Defaults
to tenants/mt-node/<connectionId> (relative to the Vault KV mount,
which the Agent Injector reads from VAULT_ADDR + mount config). The
engine writes here via HostedProvisioner._write_vault_credentials.
*/}}
{{- define "mt-node.vaultTenantPath" -}}
{{- if .Values.vault.tenantPath -}}
{{- .Values.vault.tenantPath -}}
{{- else -}}
{{- printf "tenants/mt-node/%s" .Values.mtConnection.connectionId -}}
{{- end -}}
{{- end -}}

{{/*
Resolve the container image with optional digest pin (preferred over
tag for immutability).

CHECKLIST hardening (Gap #13): repository is REQUIRED. The base
values.yaml leaves image.repository empty so a fork cannot silently
inherit a personal-namespace default; the deployment overlay
(values-staging.yaml / values-production.yaml) must set it.
Without the required-template-function call, an empty repository
would render ":<tag>" or "@<digest>" with an unusable image
reference.
*/}}
{{- define "mt-node.image" -}}
{{- $img := required "helm/mt-node: .Values.image.repository is REQUIRED. Set it in helm/mt-node/values-{staging,production}.yaml to the pinned mt-node image registry path, e.g. ghcr.io/<your-org>/etradie-mt-node." .Values.image.repository -}}
{{- if .Values.image.digest -}}
{{- printf "%s@%s" $img .Values.image.digest -}}
{{- else -}}
{{- printf "%s:%s" $img (.Values.image.tag | default .Chart.AppVersion) -}}
{{- end -}}
{{- end -}}

{{/*
Preflight: hard-fails the render if mtConnection.connectionId or
sealedSecretName are unset. Forces HostedProvisioner to set them.
*/}}
{{- define "mt-node.preflight" -}}
{{- if not .Values.mtConnection.connectionId -}}
{{- fail "helm/mt-node: .Values.mtConnection.connectionId is REQUIRED. The engine's HostedProvisioner must --set this to the canonical broker_connections.id (36-char UUID)." -}}
{{- end -}}
{{- if not .Values.mtConnection.userId -}}
{{- fail "helm/mt-node: .Values.mtConnection.userId is REQUIRED. Engine must --set this from broker_connections.user_id." -}}
{{- end -}}
{{- if not (or (eq .Values.mtConnection.platform "mt4") (eq .Values.mtConnection.platform "mt5")) -}}
{{- fail (printf "helm/mt-node: .Values.mtConnection.platform must be 'mt4' or 'mt5' (got %q)." .Values.mtConnection.platform) -}}
{{- end -}}
{{- if not .Values.mtConnection.server -}}
{{- fail "helm/mt-node: .Values.mtConnection.server is REQUIRED. Engine must --set this from broker_connections.mt5_server." -}}
{{- end -}}
{{- end -}}
