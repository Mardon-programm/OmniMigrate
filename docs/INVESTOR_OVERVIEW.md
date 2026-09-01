# OmniMigrate — Investor Overview

> **Autonomous AI-powered code migration and modernization engine.**
>
> OmniMigrate превращает устаревший код в современный автоматически: AST-анализ,
> LLM-рефакторинг, самопроверка в песочнице и self-healing цикл — до рабочего
> результата с готовым unified diff. Enterprise-платформа: мульти-тенантность,
> RBAC, биллинг, observability, Helm-развёртывание.

---

## 1. Проблема

Мировой парк legacy-кода огромен: миллионы проектов на Python 2, снятых с
поддержки фреймворков, deprecated API (distutils удалён из Python 3.12,
datetime.utcnow объявлен устаревшим и т.д.). Миграция вручную:

- стоит **дорого** — недели/месяцы работы senior-инженеров;
- **рискованна** — регрессии обнаруживаются на проде;
- **не масштабируется** — спрос на модернизацию превышает предложение инженеров.

Существующие инструменты либо делают «косметику» (codemod'ы), либо требуют
постоянного ручного контроля LLM-ассистента.

## 2. Решение

OmniMigrate — **автономный конвейер**, а не ассистент:

```
Legacy код → AST-парсинг (LibCST) → Карта проблем → LLM-рефакторинг
     → Песочница (compile + изолированный запуск) → Self-healing цикл
     → Современный код + unified diff + метрики
```

Ключевые отличия:

| Возможность | Что это даёт клиенту |
|---|---|
| **AST-анализ (LibCST)** | Детерминированная карта находок до обращения к LLM: deprecated imports, Python 2 конструкции, security issues, N+1 |
| **Self-healing loop** | Неудачная миграция автоматически уходит на починку с текстом ошибки песочницы (до N попыток) — без человека в контуре |
| **Изолированная песочница** | Сгенерированный код проверяется компиляцией и запуском в отдельном процессе до попадания к клиенту |
| **Живой прогресс** | Redis-backed статус пайплайна в реальном времени, приоритетные очереди (urgent/normal/bulk) |
| **Git-пайплайн UI** | repo/token/branch → диф → просмотр до пуша; автономный режим для целых репозиториев |

## 3. Что реализовано сегодня (рабочий продукт)

### Движок миграции
- Парсер LibCST с детекцией: deprecated импортов, `datetime.utcnow`, `xrange`,
  `== None`, хардкод-секретов, N+1 паттернов;
- LLM-конвейер (OpenAI SDK, настраиваемая модель) со строгим промптом:
  только код, сохранение сигнатур;
- Верификация: `compile()` + изолированный subprocess;
- Self-healing: автоматические раунды починки по ошибкам песочницы;
- Unified diff, метрики, история статусов каждой задачи.

### Платформа
- Организации → проекты → задачи (мульти-тенантность);
- RBAC: owner/admin/member/viewer на уровне организации и ресурсов;
- Приглашения в организацию, онбординг;
- Job management: cancel/retry/pause, webhook-уведомления;
- Метрики использования: jobs, LLM-токены, файлы, минуты — дашборд клиента и админа;
- Audit log: кто/что/когда, API + UI;
- i18n (EN/RU), a11y, тёмная Cyber-Industrial дизайн-система.

### Безопасность
- JWT access/refresh, ротация токенов, blocklist при logout;
- MFA/TOTP (Google Authenticator-совместимый): setup/enable/disable;
- Fernet-шифрование GitHub-токенов (ключ = SHA-256 derived); секреты никогда
  не попадают в Redis/очереди в открытом виде;
- SSRF-харденинг: DNS-rebinding защита, блокировка RFC1918/link-local/metadata IP;
- Rate limiting на организацию.

### Бизнес-слой
- Stripe-биллинг: планы Free / Team / Enterprise;
- Metered billing по фактическим метрикам использования;
- Лимиты и квоты по планам (jobs/мес, файлы, токены);
- Usage-дашборды для клиента и администратора.

### Enterprise-readiness
- Observability: OpenTelemetry, Prometheus `/metrics`, structlog JSON-логи;
- Graceful degradation: отказ LLM → правила → очередь → уведомление;
- Нагрузочные тесты k6 (smoke/load/stress);
- SLA-документ, runbook (backup/PITR/DR), SOC 2 readiness-политики;
- Helm chart для Kubernetes (HPA воркеров, миграции как pre-install job).

## 4. Архитектура и стек

```
React 18 + TS ──► Nginx ──► FastAPI ──► Services (Parser/LLM/Sandbox/Engine)
                                │                    │
                          SQLAlchemy (async)    arq + Redis (очереди)
                                │                    │
                            PostgreSQL 15 ◄──────────┘
```

- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy async, Alembic,
  LibCST, arq, pyotp, structlog, OpenTelemetry;
- **Frontend:** React 18, TypeScript, Tailwind CSS, Vite, Vitest, i18n;
- **Инфраструктура:** Docker Compose (5 сервисов), Nginx reverse proxy,
  Kubernetes/Helm, GitHub Actions CI.

Горизонтальное масштабирование воркеров по трём приоритетным очередям;
API stateless — масштабируется репликами.

## 5. Качество

| Показатель | Значение |
|---|---|
| Backend-тестов | **350+** (30 файлов): unit + integration |
| Frontend-тестов | Vitest suite + строгий typecheck (`tsc --noEmit`) в build |
| CI | GitHub Actions: ruff, mypy/pyright, pytest+coverage, vitest, docker build — гейт на каждый PR |
| Coverage gate | ≥ 85% backend / frontend |
| Live E2E | Интеграционные тесты против реального стека (opt-in через env) |

## 6. Развёртывание

```bash
cp backend/.env.example backend/.env   # SECRET_KEY, OPENAI_API_KEY
docker compose up --build              # весь стек за одну команду
```

- Frontend: http://localhost · API: http://localhost:8003 · Swagger: `/api/docs`
- Kubernetes: `helm install omnimigrate deploy/helm/omnimigrate`
- Миграции схемы применяются автоматически при старте (`alembic upgrade head`)

**Демо-доступ:** `admin@test.com` / `Admin123!`

## 7. Бизнес-модель

SaaS-подписка + metered billing:

| План | Целевая аудитория | Монетизация |
|---|---|---|
| Free | Пробование, indie | Лимит jobs/мес — воронка апгрейда |
| Team | Стартапы/команды | Подписка + оплата сверх лимита |
| Enterprise | Корпорации | Подписка + volume-тарификация, SSO/SLA/on-prem |

Юнит-экономика строится на разнице «стоимость LLM-токенов < стоимость часов
senior-инженера» — маржа контролируется квотами планов и metered billing.

## 8. Roadmap (следующие шаги)

- Sandbox в ephemeral-контейнере (жёсткая изоляция cgroups/no-egress);
- SSO (SAML/OIDC), SCIM-провижининг;
- PR-интеграция: draft-PR, комментарии к строкам дифа, review-флоу;
- Мультиязычность движка: JS/TS, Java, Go; Django→FastAPI, jQuery→React;
- Marketing-сайт, on-prem/air-gapped поставка.

Полный план с оценками — `ROADMAP.md` (~105 человеко-дней до полного enterprise-контура).

## 9. Почему мы выиграем

1. **Автономность, а не подсказки**: self-healing цикл доводит миграцию до
   работающего кода без человека в контуре.
2. **Инженерная строгость**: 350+ тестов, coverage-гейт, live-E2E — не прототип.
3. **Enterprise-готовность из коробки**: тенанты, RBAC, audit, MFA, шифрование
   секретов, SLA/SOC2-документы, Helm.
4. **Деньги встроены**: Stripe + metered billing + квоты — продукт продаётся
   сразу, без доработок бэк-офиса.
5. **Скорость выхода на новые языки**: конвейер движка не привязан к Python —
   парсер и промпты заменяемы модульно.

---

*Контакты: [ваша контактная информация]*
*Демо-стенд: [URL] · admin@test.com / Admin123!*
