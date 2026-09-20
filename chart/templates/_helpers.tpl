{{/* Common labels */}}
{{- define "demo-website-chart.labels" -}}
{{ include "demo-website-chart.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* Selector labels */}}
{{- define "demo-website-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ .Values.name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Service account name */}}
{{- define "demo-website-chart.serviceAccountName" -}}
{{ .Values.name }}-service-account
{{- end }}