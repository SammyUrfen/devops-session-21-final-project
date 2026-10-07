{{- define "ib.labels" -}}
app.kubernetes.io/part-of: incidentboard
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}
