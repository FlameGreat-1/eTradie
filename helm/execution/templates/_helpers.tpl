{{/*
Standard Helm helpers for the etradie-execution chart.
Mirror of helm/gateway/templates/_helpers.tpl with execution names.
*/}}

{{- define "execution.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "execution.fullname" -}}
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

{{- define "execution.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "execution.namespace" -}}
{{- default "etradie-system" .Values.namespace.name -}}
{{- end -}}

{{- define "execution.appName" -}}
etradie-execution
{{- end -}}

{{- define "execution.labels" -}}
helm.sh/chart: {{ include "execution.chart" . }}
{{ include "execution.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: etradie
{{- end -}}

{{- /* Audit ref: X-4. */ -}}
{{- define "execution.selectorLabels" -}}
app.kubernetes.io/name: {{ include "execution.appName" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "execution.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "execution.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "execution.configMapName" -}}
{{ include "execution.fullname" . }}-config
{{- end -}}

{{- define "execution.secretName" -}}
{{ include "execution.fullname" . }}-secrets
{{- end -}}
