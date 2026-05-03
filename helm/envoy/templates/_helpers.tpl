{{/*
Standard Helm helpers for the etradie-envoy chart. These are referenced
by every other template under helm/envoy/templates/.
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "envoy.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Fully qualified app name. Truncated at 63 chars (Kubernetes label limit).
If release name contains the chart name, do not duplicate it.
*/}}
{{- define "envoy.fullname" -}}
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

{{/*
Chart label as required by helm.sh/chart.
*/}}
{{- define "envoy.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
AppName used as the canonical pod selector. The base manifests use
`app: etradie-envoy`; preserve that exact string so this chart and the
kustomize tree produce interchangeable resources.
*/}}
{{- define "envoy.appName" -}}
etradie-envoy
{{- end -}}

{{/*
Common labels applied to every resource.
*/}}
{{- define "envoy.labels" -}}
helm.sh/chart: {{ include "envoy.chart" . }}
{{ include "envoy.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: etradie
app.kubernetes.io/component: proxy
{{- end -}}

{{/*
Selector labels - the strict subset used in selector blocks. Must NOT
include version / chart labels (those break selector matching across
upgrades).
*/}}
{{- define "envoy.selectorLabels" -}}
app: {{ include "envoy.appName" . }}
app.kubernetes.io/name: {{ include "envoy.appName" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Namespace name - sourced from values.namespace.name, which defaults to
envoy-system to match the kustomize base.
*/}}
{{- define "envoy.namespace" -}}
{{- default "envoy-system" .Values.namespace.name -}}
{{- end -}}

{{/*
ServiceAccount name. If serviceAccount.create is false, the user is
responsible for ensuring an SA of this name exists.
*/}}
{{- define "envoy.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "envoy.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}
