{{/*
Standard Helm helpers for the etradie-billing chart.
*/}}

{{- define "billing.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "billing.fullname" -}}
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

{{- define "billing.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "billing.namespace" -}}
{{- default "etradie-system" .Values.namespace.name -}}
{{- end -}}

{{- define "billing.appName" -}}
etradie-billing
{{- end -}}

{{- define "billing.labels" -}}
helm.sh/chart: {{ include "billing.chart" . }}
{{ include "billing.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: etradie
{{- end -}}

{{- /* Audit ref: X-4. */ -}}
{{- define "billing.selectorLabels" -}}
app.kubernetes.io/name: {{ include "billing.appName" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "billing.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "billing.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/*
Name of the billing non-secret ConfigMap.
*/}}
{{- define "billing.configMapName" -}}
{{ include "billing.fullname" . }}-config
{{- end -}}

{{/*
Name of the billing secret synthesised by the ExternalSecret.
*/}}
{{- define "billing.secretName" -}}
{{ include "billing.fullname" . }}-secrets
{{- end -}}
