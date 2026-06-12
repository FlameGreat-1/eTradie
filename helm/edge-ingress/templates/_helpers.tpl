{{/*
Standard Helm helpers for the edge-ingress chart.
*/}}

{{- define "edge-ingress.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "edge-ingress.fullname" -}}
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

{{- define "edge-ingress.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "edge-ingress.namespace" -}}
{{- default "edge-ingress-system" .Values.namespace.name -}}
{{- end -}}

{{- define "edge-ingress.labels" -}}
helm.sh/chart: {{ include "edge-ingress.chart" . }}
{{ include "edge-ingress.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: etradie
{{- end -}}

{{- define "cloudflared.selectorLabels" -}}
app.kubernetes.io/name: cloudflared
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "cloudflared.labels" -}}
helm.sh/chart: {{ include "edge-ingress.chart" . }}
{{ include "cloudflared.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: etradie
{{- end -}}

{{- define "edge-ingress.selectorLabels" -}}
app.kubernetes.io/name: edge-ingress
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "edge-ingress.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "edge-ingress.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}
