{{/*
Standard Helm helpers for the etradie-management chart.
*/}}

{{- define "management.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "management.fullname" -}}
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

{{- define "management.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "management.namespace" -}}
{{- default "etradie-system" .Values.namespace.name -}}
{{- end -}}

{{- define "management.appName" -}}
etradie-management
{{- end -}}

{{- define "management.labels" -}}
helm.sh/chart: {{ include "management.chart" . }}
{{ include "management.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: etradie
app.kubernetes.io/component: management
{{- end -}}

{{- /* Audit ref: X-4. */ -}}
{{- define "management.selectorLabels" -}}
app.kubernetes.io/name: {{ include "management.appName" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "management.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "management.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "management.configMapName" -}}
{{ include "management.fullname" . }}-config
{{- end -}}

{{- define "management.secretName" -}}
{{ include "management.fullname" . }}-secrets
{{- end -}}
