# Auditoria de stack v1 - LeaseManager

Estado: vigente  
Fecha: 15/03/2026  
Boundary evaluado: v1 activo definido por [PRD_CANONICO.md](./PRD_CANONICO.md)

## 1. Objetivo

Evaluar si el stack actualmente recomendado para el v1 sigue siendo la mejor opcion para este dominio: ERP transaccional, auditable, con conciliacion bancaria, ledger contable, cierre mensual, preparacion tributaria, documentos y backoffice operativo.

La auditoria compara:

- candidato A: `Django 5 + DRF + PostgreSQL + Celery + Redis + React + TypeScript + Vite`
- candidato B: `ASP.NET Core + PostgreSQL + Hangfire/Quartz + React + TypeScript + Vite`
- candidato C: `Ruby on Rails + PostgreSQL + Sidekiq/Solid Queue + React o Hotwire`
- candidato D: `FastAPI + PostgreSQL + Celery + React + TypeScript + Vite`

No se evaluan microservicios como arquitectura base del v1. El criterio es monolito modular con prioridad en robustez operativa.

## 2. Metodologia

Ponderaciones usadas:

- fit con ERP transaccional y auditable: `30%`
- robustez operativa y cumplimiento: `25%`
- hiring y maintainability realista: `20%`
- integraciones y ecosistema: `15%`
- velocidad de entrega: `10%`

Escala:

- `5.0`: excelente fit
- `4.0`: muy buen fit
- `3.0`: aceptable con compromisos
- `2.0`: debil para el caso
- `1.0`: no recomendable

Nota importante:

- los criterios de hiring y maintainability son inferencia razonada desde el ecosistema, madurez, documentacion oficial y realidad operativa probable del proyecto, no una metrica oficial cerrada.

## 3. Candidato A - Django + DRF + PostgreSQL + Celery + Redis + React

### Fortalezas

- Django esta disenado para desarrollo rapido, seguridad y escalabilidad, con un admin interno muy fuerte, lo que calza especialmente bien con ERP y backoffice. Fuente: [Django](https://www.djangoproject.com/), [Django admin](https://docs.djangoproject.com/en/4.0/ref/contrib/admin/)
- DRF ofrece una capa API madura, bien integrada con auth, permissions, serializers y testing. Fuente: [DRF Quickstart](https://www.django-rest-framework.org/tutorial/quickstart/)
- PostgreSQL encaja muy bien con este dominio por consistencia transaccional, concurrencia, funciones avanzadas y robustez operacional. Fuente: [PostgreSQL](https://www.postgresql.org/), [PostgreSQL docs](https://www.postgresql.org/docs/)
- Celery sigue siendo una base razonable para tareas operativas, sincronizaciones y procesos recurrentes. Fuente: [Celery docs](https://docs.celeryq.dev/en/stable/getting-started/first-steps-with-celery.html)
- React + TypeScript + Vite sigue siendo un stack fuerte para backoffice denso y pantallas operativas complejas. Fuente: [React Learn](https://react.dev/learn), [Vite Guide](https://vite.dev/guide/)

### Debilidades

- Celery + Redis anade piezas operativas extra frente a colas DB-backed.
- Django Admin ayuda mucho en soporte operacional, pero no sustituye la UI procesual del producto.
- Python/Django puede rendir menos que .NET en algunos escenarios CPU-heavy, aunque ese no es el cuello principal del v1.

### Veredicto

Excelente fit general para el v1. El mejor equilibrio entre dominio transaccional, backoffice, auditabilidad, velocidad y contratacion realista.

## 4. Candidato B - ASP.NET Core + PostgreSQL + Hangfire/Quartz + React

### Fortalezas

- ASP.NET Core destaca por seguridad, rendimiento y madurez enterprise. Fuente: [ASP.NET Core docs](https://learn.microsoft.com/en-us/aspnet/core/)
- EF Core y Npgsql ofrecen una ruta solida sobre PostgreSQL. Fuente: [EF docs hub](https://learn.microsoft.com/en-us/ef/), [Npgsql](https://www.npgsql.org/), [Npgsql EF Core provider](https://www.npgsql.org/efcore/)
- Hangfire es una solucion confiable para background jobs con almacenamiento persistente. Fuente: [Hangfire docs](https://docs.hangfire.io/en/latest/)
- Quartz.NET es muy fuerte para scheduling y escenarios enterprise. Fuente: [Quartz.NET](https://www.quartz-scheduler.net/)

### Debilidades

- el stack de jobs queda menos limpio en el candidato propuesto porque mezcla dos opciones (`Hangfire/Quartz`) con tradeoffs distintos;
- para un ERP/backoffice intensivo, ASP.NET Core necesita mas trabajo inicial para igualar la productividad interna que Django ofrece de salida con admin y convenciones de backoffice;
- el beneficio de robustez adicional no compensa claramente el costo de arranque para este v1, salvo que el equipo ya sea claramente .NET-first.

### Veredicto

Muy buen candidato, especialmente si el equipo ya domina .NET. Aun asi, para este proyecto concreto pierde frente a Django por costo de arranque y fit con backoffice interno.

## 5. Candidato C - Rails + PostgreSQL + Sidekiq/Solid Queue + React o Hotwire

### Fortalezas

- Rails sigue siendo muy productivo y full-stack. Fuente: [Rails](https://rubyonrails.org/), [Getting Started with Rails](https://guides.rubyonrails.org/getting_started.html)
- Active Job con Solid Queue reduce dependencias externas porque Rails 8 lo trae como backend por defecto. Fuente: [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html)
- Sidekiq es muy maduro y eficiente para background jobs. Fuente: [Sidekiq Getting Started](https://sidekiq.org/wiki/Getting-Started)
- Hotwire es atractivo para HTML-over-the-wire y menor JavaScript. Fuente: [Hotwire](https://hotwired.dev/), [Turbo](https://turbo.hotwired.dev/)

### Debilidades

- el candidato queda menos homogeneo porque mezcla `Sidekiq` y `Solid Queue`, que responden a filosofias distintas de operacion;
- el hiring realista para Rails suele ser mas estrecho que para Django o .NET en muchos mercados;
- para este dominio contable/tributario y sus integraciones especificas, no ofrece una ventaja clara suficiente frente a Django.

### Veredicto

Stack atractivo y productivo, pero no el mejor ajuste global para este proyecto. Queda por debajo del candidato A por hiring y por menor ventaja diferencial en el dominio.

## 6. Candidato D - FastAPI + PostgreSQL + Celery + React

### Fortalezas

- FastAPI es muy agradable para construir APIs modernas y simples. Fuente: [FastAPI](https://fastapi.tiangolo.com/tutorial/first-steps/)
- Python mantiene buena sinergia con integraciones, scripting y procesamiento.
- Reutiliza PostgreSQL, Celery y React del stack actual.

### Debilidades

- FastAPI no trae una respuesta integrada tan fuerte para backoffice, admin interno, permisos procesuales y superficie operativa como Django;
- en un ERP auditable con muchos flujos, validaciones y backoffice, obliga a ensamblar mas piezas desde cero;
- esa flexibilidad extra no trae un beneficio equivalente para este v1.

### Veredicto

Muy bueno para API-first products. Mas debil para este caso de ERP operacional y contable.

## 7. Evaluacion por subsistema

| Subsistema | Mejor fit | Razon |
|---|---|---|
| Dominio transaccional y ORM | `Django + PostgreSQL` | equilibrio muy fuerte entre productividad, ORM, validaciones y admin interno |
| Permisos y backoffice | `Django + DRF` | auth, permissions y admin interno mejor alineados con backoffice pesado |
| Conciliacion bancaria y jobs | `Django/Celery` o `.NET/Hangfire` | ambos son viables; gana Django por coherencia global del stack |
| Ledger contable y cierres | `Django + PostgreSQL` | monolito transaccional favorece consistencia y trazabilidad |
| Documentos y PDF | `Django` o `Rails` | ambos buenos; no define solo el stack ganador |
| Integracion SII | `Django` o `.NET` | ambos pueden hacerlo; gana Django por continuidad con dominio y cierre mensual |
| Frontend operativo | `React + TypeScript + Vite` | sigue siendo la mejor opcion practica para consola densa |
| Secretos, auditoria y observabilidad | `Django` o `.NET` | ambos fuertes; no cambia el ganador total |

## 8. Resultado final

Ranking final:

1. Candidato A
2. Candidato B
3. Candidato C
4. Candidato D

Conclusion:

El stack actual recomendado gana la auditoria. No porque sea el mas "moderno", sino porque es el mejor balance para este dominio y este modelo operativo.

## 9. Recomendacion final

Mantener como stack final recomendado para el v1:

- arquitectura: monolito modular
- backend core: `Django 5`
- capa API: `Django REST Framework`
- base de datos: `PostgreSQL`
- jobs y tareas recurrentes: `Celery + Redis`
- frontend: `React + TypeScript + Vite`
- documentos: `PDF` canonico con estrategia definida en ADR documental
- secretos: secret manager o KMS externo + referencias en base transaccional
- observabilidad: logging estructurado, healthchecks, trazabilidad de jobs y metricas operativas

Refinamientos recomendados sin cambiar el stack:

1. Mantener `Django Admin` solo como superficie interna de soporte, no como producto.
2. Mantener `Celery + Redis` para v1, pero revisar workflow durable solo si el proyecto crece hacia procesos de larga vida.
3. No reintroducir `Django Ninja`, `pgvector`, portales ni IA avanzada dentro del boundary activo del v1.

## 10. Fuentes primarias usadas

- Django: [https://www.djangoproject.com/](https://www.djangoproject.com/)
- Django admin: [https://docs.djangoproject.com/en/4.0/ref/contrib/admin/](https://docs.djangoproject.com/en/4.0/ref/contrib/admin/)
- DRF: [https://www.django-rest-framework.org/tutorial/quickstart/](https://www.django-rest-framework.org/tutorial/quickstart/)
- PostgreSQL: [https://www.postgresql.org/](https://www.postgresql.org/)
- PostgreSQL docs: [https://www.postgresql.org/docs/](https://www.postgresql.org/docs/)
- ASP.NET Core: [https://learn.microsoft.com/en-us/aspnet/core/](https://learn.microsoft.com/en-us/aspnet/core/)
- EF docs: [https://learn.microsoft.com/en-us/ef/](https://learn.microsoft.com/en-us/ef/)
- Npgsql: [https://www.npgsql.org/](https://www.npgsql.org/)
- Npgsql EF provider: [https://www.npgsql.org/efcore/](https://www.npgsql.org/efcore/)
- Hangfire docs: [https://docs.hangfire.io/en/latest/](https://docs.hangfire.io/en/latest/)
- Quartz.NET: [https://www.quartz-scheduler.net/](https://www.quartz-scheduler.net/)
- Rails: [https://rubyonrails.org/](https://rubyonrails.org/)
- Rails Getting Started: [https://guides.rubyonrails.org/getting_started.html](https://guides.rubyonrails.org/getting_started.html)
- Rails Active Job / Solid Queue: [https://guides.rubyonrails.org/active_job_basics.html](https://guides.rubyonrails.org/active_job_basics.html)
- Sidekiq: [https://sidekiq.org/wiki/Getting-Started](https://sidekiq.org/wiki/Getting-Started)
- Hotwire: [https://hotwired.dev/](https://hotwired.dev/)
- Turbo: [https://turbo.hotwired.dev/](https://turbo.hotwired.dev/)
- FastAPI: [https://fastapi.tiangolo.com/tutorial/first-steps/](https://fastapi.tiangolo.com/tutorial/first-steps/)
- React: [https://react.dev/learn](https://react.dev/learn)
- Vite: [https://vite.dev/guide/](https://vite.dev/guide/)
