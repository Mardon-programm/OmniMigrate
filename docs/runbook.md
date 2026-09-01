# OmniMigrate Runbook — Ops, Backup & Disaster Recovery

Операционные процедуры для SRE/on-call. Предполагается деплой через
`docker-compose.yml` (dev/staging) или Helm chart (`deploy/helm/`, prod).

## 1. Health & Probes

| Probe | Endpoint | Ожидание |
|---|---|---|
| Liveness | `GET /healthz` | `{"status":"ok"}`, 200 |
| Readiness | `GET /readyz` | redis+database `ok`, 200 |
| Metrics | `GET /metrics` | Prometheus exposition |

Alert-правила (минимум): `up == 0` 2 мин; p99 latency > 1s 10 мин;
`omnimigrate_jobs_failed_total` растёт 15 мин; redis errors > 0.

## 2. Daily Operations

```bash
# Статус стека
docker compose ps
curl -fsS http://localhost:8003/readyz | jq

# Хвост логов API и воркера
docker compose logs -f --tail=100 backend worker

# Глубина очереди arq (норма < 100; рост = воркеры не успевают)
docker compose exec redis redis-cli LLEN arq:queue
```

Зависшие job: `POST /api/jobs/{id}/cancel`, затем при необходимости retry.

## 3. Backup

### Postgres (RPO ≤ 15 мин)

```bash
# Логический бэкап nightly (cron)
docker compose exec -T postgres \
  pg_dump -U omnimigrate -Fc omnimigrate > backup/omni_$(date +%F).dump

# WAL-архивирование для PITR: в postgres.conf
# archive_mode=on, archive_command='test ! -f /wal/%f && cp %p /wal/%f'
```

### Redis

Очереди arq — переиграемые; персистентность не критична. Достаточно
`save 900 1`. Сессионный blocklist токенов потеряется при рестарте —
приемлемо (см. §6).

### Проверка восстановления (ежемесячно)

Восстановить последний дамп на staging и прогнать smoke-тест:
`k6 run loadtest/smoke.js -e BASE_URL=https://staging…`.

## 4. Restore Procedure (RTO ≤ 1 ч)

```bash
# 1. Остановить writers
docker compose stop backend worker

# 2. Восстановить БД
docker compose exec -T postgres psql -U omnimigrate -c \
  "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
cat backup/omni_2026-08-23.dump | docker compose exec -T postgres \
  pg_restore -U omnimigrate -d omnimigrate --no-owner

# 3. Поднять API, проверить миграции схемы
docker compose up -d postgres backend
docker compose exec backend alembic upgrade head

# 4. Smoke + вернуть воркеров
curl -fsS http://localhost:8003/readyz | jq
docker compose up -d worker
```

## 5. DR Playbook (сценарии)

| Сценарий | Действия |
|---|---|
| **Redis down** | API продолжает отдавать 200 на read-эндпоинтах; постановка job вернёт 503 → клиент ретраит. `docker compose restart redis`; blocklist сбросится — все access token остаются валидны до истечения TTL |
| **Postgres primary loss** | Переключение на реплику (managed PG: promote). Локально: restore из последнего dump+WAL (§4) |
| **LLM провайдер down** | Автоматическая деградация к local-rule-engine уже встроена. Мониторить `omnimigrate_llm_calls_total{status="error"}` |
| **Worker OOM/краш** | Job останется в очереди arq (at-least-once). `docker compose up -d worker`; проверить `arq.worker.WORKER_SERVICES` логи |
| **Компрометация SECRET_KEY** | Ротация ключа инвалидирует все JWT (приемлемо) + Fernet-токены GitHub требуют повторного ввода пользователями. Уведомить клиентов |
| **Compromise GitHub-токена** | Revoke в GitHub → пользователь обновляет токен в Settings; audit log покажет источник изменений |

## 6. Token Blocklist после рестарта Redis

Logout-токены хранятся в Redis. После потери Redis все logout'нутые
access-токены снова валидны до истечения exp (~30 мин). Митигация:
короткий TTL access-токена + ротация refresh. Для Enterprise — вынести
blocklist в Postgres (задача в backlog).

## 7. Масштабирование воркеров

```bash
# Compose: N воркеров
docker compose up -d --scale worker=4

# Kubernetes (Helm): autoscaling по CPU/глубине очереди
helm upgrade omnimigrate deploy/helm/omnimigrate \
  --set worker.autoscaling.minReplicas=2 \
  --set worker.autoscaling.maxReplicas=20
```

## 8. Обновление версии

1. Прочитать CHANGELOG / migration notes.
2. `git pull && docker compose build`.
3. Накатить миграции: `docker compose run --rm backend alembic upgrade head`.
4. Rolling restart: `docker compose up -d backend worker`.
5. Smoke: `/healthz`, `/readyz`, создать тестовый job.
6. Откат: предыдущий image tag + `alembic downgrade -1`.

## 9. Контакты эскалации

S1 → on-call инженер (PagerDuty) → CTO, SLA 30 мин.
S2 → support-дежурный Slack #omnimigrate-incidents.
