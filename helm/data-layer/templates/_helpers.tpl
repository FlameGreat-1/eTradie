{{/*
Standard Helm helpers for the etradie-data-layer chart.
Each datastore gets distinct selectorLabels so per-datastore
NetworkPolicies, Services, and StatefulSets do not cross-fire.
*/}}

{{- define "data-layer.namespace" -}}
{{- default "etradie-system" .Values.namespace.name -}}
{{- end -}}

{{- define "data-layer.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels shared across the chart's resources.
*/}}
{{- define "data-layer.commonLabels" -}}
helm.sh/chart: {{ include "data-layer.chart" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: etradie
app.kubernetes.io/component: data-layer
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* ===== Postgres ===== */}}
{{- define "postgres.appName" -}}
postgres
{{- end -}}

{{- define "postgres.selectorLabels" -}}
app.kubernetes.io/name: {{ include "postgres.appName" . }}
app.kubernetes.io/component: data-layer-postgres
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "postgres.labels" -}}
{{ include "data-layer.commonLabels" . }}
{{ include "postgres.selectorLabels" . }}
{{- end -}}

{{- define "postgres.secretName" -}}
postgres-credentials
{{- end -}}

{{- define "postgres.initSqlConfigMap" -}}
postgres-init-sql
{{- end -}}

{{- define "postgres.backupName" -}}
postgres-backup
{{- end -}}

{{- define "postgres.backupPVC" -}}
postgres-backups
{{- end -}}

{{/* ===== Redis ===== */}}
{{- define "redis.appName" -}}
redis
{{- end -}}

{{- define "redis.selectorLabels" -}}
app.kubernetes.io/name: {{ include "redis.appName" . }}
app.kubernetes.io/component: data-layer-redis
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "redis.labels" -}}
{{ include "data-layer.commonLabels" . }}
{{ include "redis.selectorLabels" . }}
{{- end -}}

{{- define "redis.secretName" -}}
redis-credentials
{{- end -}}

{{- define "redis.configMap" -}}
redis-config
{{- end -}}

{{/* ===== ChromaDB ===== */}}
{{- define "chromadb.appName" -}}
chromadb
{{- end -}}

{{- define "chromadb.selectorLabels" -}}
app.kubernetes.io/name: {{ include "chromadb.appName" . }}
app.kubernetes.io/component: data-layer-chromadb
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "chromadb.labels" -}}
{{ include "data-layer.commonLabels" . }}
{{ include "chromadb.selectorLabels" . }}
{{- end -}}

{{- define "chromadb.secretName" -}}
chromadb-credentials
{{- end -}}
