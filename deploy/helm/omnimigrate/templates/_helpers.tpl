{{/*
Expand the name of the chart.
*/}}
{{- define "omnimigrate.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "omnimigrate.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{ include "omnimigrate.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "omnimigrate.selectorLabels" -}}
app.kubernetes.io/name: {{ include "omnimigrate.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Component labels (pass "component" via dict).
*/}}
{{- define "omnimigrate.componentLabels" -}}
{{ include "omnimigrate.selectorLabels" . }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/*
Fullname.
*/}}
{{- define "omnimigrate.fullname" -}}
{{- default (include "omnimigrate.name" .) .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
App secret name (SECRET_KEY, ENCRYPTION_KEY, provider keys).
*/}}
{{- define "omnimigrate.appSecretName" -}}
{{- default (printf "%s-app" (include "omnimigrate.fullname" .)) .Values.existingSecret }}
{{- end }}

{{/*
Postgres secret name; must contain key `url` (full asyncpg DSN).
*/}}
{{- define "omnimigrate.pgSecretName" -}}
{{- default (printf "%s-postgres" (include "omnimigrate.fullname" .)) .Values.externalPostgres.auth.existingSecret }}
{{- end }}

{{/*
DATABASE_URL assembled from externalPostgres values + secret password.
*/}}
{{- define "omnimigrate.databaseUrl" -}}
postgresql+asyncpg://{{ .Values.externalPostgres.auth.username }}:$(POSTGRES_PASSWORD)@{{ .Values.externalPostgres.host }}:{{ .Values.externalPostgres.port }}/{{ .Values.externalPostgres.database }}
{{- end }}
