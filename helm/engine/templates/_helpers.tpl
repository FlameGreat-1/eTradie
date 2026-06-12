{{/*
Standard Helm helpers for the etradie-engine chart.
Mirror of helm/gateway/templates/_helpers.tpl with engine names.
*/}}

{{- define "engine.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "engine.fullname" -}}
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

{{- define "engine.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "engine.namespace" -}}
{{- default "etradie-system" .Values.namespace.name -}}
{{- end -}}

{{/*
appName is hard-pinned to etradie-engine so selector labels and
NetworkPolicy podSelectors stay stable regardless of release name.
Gateway/execution/management charts also use a hard-pinned appName.
*/}}
{{- define "engine.appName" -}}
etradie-engine
{{- end -}}

{{- define "engine.labels" -}}
helm.sh/chart: {{ include "engine.chart" . }}
{{ include "engine.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: etradie
{{- end -}}

{{- /*
selectorLabels are the immutable subset used in spec.selector.matchLabels
for Deployments, Services, ServiceMonitors and PodDisruptionBudgets.
Component and version labels MUST NOT live here - they belong in
engine.labels (full label set). Audit ref: X-4, E-M1, E-M2.
*/ -}}
{{- define "engine.selectorLabels" -}}
app.kubernetes.io/name: {{ include "engine.appName" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "engine.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "engine.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "engine.configMapName" -}}
{{ include "engine.fullname" . }}-config
{{- end -}}

{{- define "engine.secretName" -}}
{{ include "engine.fullname" . }}-secrets
{{- end -}}
