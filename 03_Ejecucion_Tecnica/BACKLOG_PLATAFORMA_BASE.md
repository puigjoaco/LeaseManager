# Backlog PlataformaBase - Arranque ejecutable

## 1. Objetivo

Dejar listo el esqueleto tecnico sobre el que se construira el resto del sistema, sin mezclar todavia dominio funcional profundo.

Resultado esperado:

- backend levantando;
- frontend levantando;
- autenticacion y RBAC base definidos;
- configuracion por ambiente;
- auditoria minima;
- secretos y storage segregados;
- cola async y observabilidad minimas;
- convenciones de proyecto fijadas.

## 2. Orden de ejecucion

### PB-01. Bootstrap del repositorio

| ID | Tarea | Salida esperada |
|---|---|---|
| `PB-01-01` | crear estructura raiz de backend | proyecto Django inicial con settings por ambiente |
| `PB-01-02` | crear estructura raiz de frontend | app React + TypeScript + Vite inicial |
| `PB-01-03` | definir convencion de carpetas y modulos | layout estable para apps, API, dominio y shared |
| `PB-01-04` | fijar tooling base | lint, format, typecheck y scripts minimos |

### PB-02. Configuracion y ambientes

| ID | Tarea | Salida esperada |
|---|---|---|
| `PB-02-01` | settings por ambiente (`local`, `test`, `staging`, `prod`) | configuracion desacoplada del codigo |
| `PB-02-02` | manejo de variables de entorno | `env.example` y validacion minima de arranque |
| `PB-02-03` | configuracion de timezone, locale y moneda base | `America/Santiago`, espanol Chile y defaults correctos |
| `PB-02-04` | conexion a PostgreSQL y Redis | servicios base inicializados |

### PB-03. Autenticacion y control de acceso

| ID | Tarea | Salida esperada |
|---|---|---|
| `PB-03-01` | modelo de usuario base | usuario interno con soporte de roles |
| `PB-03-02` | RBAC inicial | `AdministradorGlobal`, `OperadorDeCartera`, `Socio` |
| `PB-03-03` | scope operativo base | filtros por empresa, socio y mandato |
| `PB-03-04` | autenticacion web/API | login funcional para backoffice |

### PB-04. Auditoria y resolucion manual

| ID | Tarea | Salida esperada |
|---|---|---|
| `PB-04-01` | modelo `EventoAuditable` | eventos sensibles persistidos |
| `PB-04-02` | modelo `ResolucionManual` | decisiones manuales trazables |
| `PB-04-03` | hooks de auditoria base | login, cambios de estado y exports sensibles auditados |

### PB-05. Secretos, storage y seguridad operativa

| ID | Tarea | Salida esperada |
|---|---|---|
| `PB-05-01` | abstraccion de secretos | referencias a secretos separadas del dominio |
| `PB-05-02` | storage documental base | bucket o storage local abstraido |
| `PB-05-03` | politica de archivos y checksum | archivos trazables y versionables |
| `PB-05-04` | headers y settings de seguridad web | sesion, CSRF, HTTPS-ready |

### PB-06. Async, observabilidad y salud

| ID | Tarea | Salida esperada |
|---|---|---|
| `PB-06-01` | Celery + Redis operativos | cola y worker funcionales |
| `PB-06-02` | healthchecks backend/worker | estado visible de servicios base |
| `PB-06-03` | logging estructurado minimo | logs utiles para operaciones |
| `PB-06-04` | manejo base de errores | errores transaccionales y de integracion diferenciados |

### PB-07. API y frontend base

| ID | Tarea | Salida esperada |
|---|---|---|
| `PB-07-01` | DRF base y routing inicial | API lista para modulos de negocio |
| `PB-07-02` | layout web de backoffice | shell principal autenticado |
| `PB-07-03` | cliente API y manejo de sesion | frontend listo para consumir backend |
| `PB-07-04` | pantalla inicial de salud y diagnostico | visibilidad del estado del sistema |

## 3. Criterios de cierre

`PlataformaBase` se considera lista solo si:

- backend y frontend arrancan de forma reproducible;
- login y control de acceso funcionan;
- auditoria base registra eventos sensibles;
- cola async y healthchecks estan operativos;
- secretos y archivos no viven mezclados con el dominio;
- existe una pantalla o endpoint de estado para validar ambiente.
