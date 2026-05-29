{{/*
  Helpers for the etradie-observability-logs chart.
*/}}

{{- define "olog.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "olog.fullname" -}}
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

{{- define "olog.namespace" -}}
{{- .Values.namespace.name | default .Release.Namespace -}}
{{- end -}}

{{- define "olog.labels" -}}
app.kubernetes.io/name: {{ include "olog.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: etradie
{{- end -}}

{{- define "olog.loki.selectorLabels" -}}
app.kubernetes.io/name: loki
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/part-of: etradie
{{- end -}}

{{- define "olog.promtail.selectorLabels" -}}
app.kubernetes.io/name: promtail
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/part-of: etradie
{{- end -}}

{{- define "olog.loki.fullname" -}}
{{ include "olog.fullname" . }}-loki
{{- end -}}

{{- define "olog.promtail.fullname" -}}
{{ include "olog.fullname" . }}-promtail
{{- end -}}
