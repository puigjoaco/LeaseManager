# Matriz comparativa de stack v1 - LeaseManager

## 1. Candidatos

| Candidato | Stack |
|---|---|
| `A` | `Django 5 + DRF + PostgreSQL + Celery + Redis + React + TypeScript + Vite` |
| `B` | `ASP.NET Core + PostgreSQL + Hangfire/Quartz + React + TypeScript + Vite` |
| `C` | `Ruby on Rails + PostgreSQL + Sidekiq/Solid Queue + React o Hotwire` |
| `D` | `FastAPI + PostgreSQL + Celery + React + TypeScript + Vite` |

## 2. Ponderaciones

| Criterio | Peso |
|---|---:|
| Fit ERP transaccional y auditable | `30%` |
| Robustez operativa y cumplimiento | `25%` |
| Hiring y maintainability realista | `20%` |
| Integraciones y ecosistema | `15%` |
| Velocidad de entrega | `10%` |

## 3. Scoring

Escala: `1.0` a `5.0`

| Candidato | ERP | Robustez | Hiring | Ecosistema | Velocidad | Score ponderado |
|---|---:|---:|---:|---:|---:|---:|
| `A` | `4.8` | `4.4` | `4.3` | `4.4` | `4.6` | `4.50 / 5` |
| `B` | `4.4` | `4.8` | `3.9` | `4.2` | `3.7` | `4.28 / 5` |
| `C` | `4.1` | `3.8` | `2.8` | `3.5` | `4.4` | `3.70 / 5` |
| `D` | `2.9` | `3.4` | `4.1` | `3.6` | `4.2` | `3.45 / 5` |

## 4. Decision por capa

| Capa | Ganador | Decision |
|---|---|---|
| Arquitectura base | `A` | monolito modular |
| Backend core | `A` | `Django 5` |
| API | `A` | `Django REST Framework` |
| ORM y transacciones | `A` | `Django ORM + PostgreSQL` |
| Jobs y colas | `A` | `Celery + Redis` para v1 |
| Base de datos | `A/B/C/D` | `PostgreSQL` se mantiene |
| Frontend | `A/B/D` | `React + TypeScript + Vite` |
| Documentos | `A/C` | mantener PDF canonico; no cambia ganador del stack |
| Secretos | `A/B` | secret manager/KMS externo + referencias en base |
| Observabilidad | `A/B` | logging estructurado + healthchecks + metricas operativas |

## 5. Razones de descarte resumidas

| Candidato | Razon principal de no seleccion |
|---|---|
| `B` | excelente robustez, pero peor equilibrio global para backoffice/ERP en el v1 |
| `C` | muy productivo, pero hiring y coherencia del stack de jobs quedan peores |
| `D` | demasiado ensamblaje para un ERP operacional y auditable |

## 6. Recomendacion final

Se confirma el stack activo:

- `Django 5`
- `Django REST Framework`
- `PostgreSQL`
- `Celery + Redis`
- `React + TypeScript + Vite`

No se recomienda cambio de stack para el v1.
