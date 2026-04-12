# Contexto Maestro

## 1. Proyecto, raiz activa y alcance actual

Proyecto activo: `LeaseManager` greenfield  
Root activo: [D:/Proyectos/LeaseManager/Produccion 1.0](/D:/Proyectos/LeaseManager/Produccion%201.0)  
Root legacy read-only: [D:/Proyectos/LeaseManager](/D:/Proyectos/LeaseManager)

El root activo contiene simultaneamente:

- el set canonico vigente del producto y la arquitectura;
- la codebase greenfield funcional;
- el pipeline de migracion ya validado;
- el paquete `HANDOFF/` para continuidad;
- la topologia publica actualmente operativa del greenfield.

Rectificacion vigente:

- dentro del root activo, el nombre correcto es `LeaseManager`;
- `LeaseControl` es historico y no debe reintroducirse dentro de `Produccion 1.0`.

## 2. Que esta cerrado y que cambio desde el handoff previo

### 2.1 Tramo cerrado antes de esta actualizacion

Ya estaba cerrado antes de este refresh:

- diseno comunitario final;
- implementacion de comunidades/recaudacion/atribucion;
- validacion del pipeline local y staging;
- formalizacion del repo nuevo y separacion del legacy.

### 2.2 Que cambio materialmente en este thread largo

Desde el handoff de `2026-04-11`, el trabajo ya no se quedo en “seed + hardening inicial” ni en “seguir extrayendo workspaces”.

Se ejecuto una secuencia verificable adicional:

- se completo una modularizacion mucho mas amplia del frontend:
  - [api.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/api.ts)
  - [shell.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/shell.tsx)
  - [view-config.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/view-config.ts)
  - workspaces extraidos para `Canales`, `Reporting`, `Contabilidad`, `SII` y otros bloques operativos;
- se corrigieron detalles finos de UX/RBAC:
  - accesos restringidos en tabs y shortcuts;
  - banners readonly visibles para perfiles de control;
  - mensaje explicito de backend faltante fuera de entorno local;
- se dejo el frontend del greenfield desplegado en Vercel como proyecto separado:
  - [https://leasemanager-backoffice.vercel.app](https://leasemanager-backoffice.vercel.app);
- se preparo el backend del greenfield para despliegue productivo:
  - Dockerfile;
  - Procfile;
  - `whitenoise`;
  - configuracion Railway;
  - docs y scripts de rollout;
- se conecto el frontend publico con el backend canonico mediante `VITE_API_BASE_URL`;
- se conecto Vercel al repo Git oficial y se fijo `Root Directory=frontend`;
- se conecto Railway al repo Git oficial y se dejo la topologia activa:
  - proyecto `content-friendship`;
  - web service `surprising-balance`;
  - worker `spirited-recreation`;
  - Redis online;
- se levanto el backend publico en:
  - [https://surprising-balance-production.up.railway.app](https://surprising-balance-production.up.railway.app);
- se corrigieron dos bloqueos reales del rollout:
  - `DisallowedHost` para `healthcheck.railway.app`;
  - `Root Directory` incorrecto en Vercel;
- se sembraron usuarios demo en la base remota;
- se validaron smoke checks publicos en navegador real para:
  - `demo-admin`
  - `demo-operador`
  - `demo-revisor`
  - `demo-socio`

## 3. Estado real del repo, del runtime y del codigo

### 3.1 Git y remotos

Estado verificado al momento de este refresh:

- git root activo: [D:/Proyectos/LeaseManager/Produccion 1.0](/D:/Proyectos/LeaseManager/Produccion%201.0)
- remoto oficial: [https://github.com/puigjoaco/LeaseManager.git](https://github.com/puigjoaco/LeaseManager.git)
- remoto legacy: [https://github.com/puigjoaco/LeaseManager-legacy.git](https://github.com/puigjoaco/LeaseManager-legacy.git)
- `HEAD` funcional previo a esta actualizacion documental:
  - `9068f7e` `chore: trigger vercel build with frontend root`
- commits de infraestructura/rollout inmediatamente relevantes:
  - `3850612` `chore: trigger connected deployment rebuilds`
  - `9068f7e` `chore: trigger vercel build with frontend root`
- working tree al iniciar este refresh:
  - los archivos bajo `HANDOFF/` ya venian modificados respecto del commit anterior;
  - este refresh debe tratarse como actualizacion documental consciente, no como sorpresa del arbol.

### 3.2 Entorno local y publico

Estado local/publico validado durante este trabajo:

- Docker Desktop operativo;
- `leasemanager-postgres` y `leasemanager-redis` operativos;
- backend local respondiendo en `127.0.0.1:8000`;
- frontend local respondiendo en `127.0.0.1:5173`;
- `health` local con `database = up` y `redis = up`;
- frontend publico respondiendo en:
  - [https://leasemanager-backoffice.vercel.app](https://leasemanager-backoffice.vercel.app);
- backend publico respondiendo en:
  - [https://surprising-balance-production.up.railway.app/api/v1/health/](https://surprising-balance-production.up.railway.app/api/v1/health/)
  - [https://surprising-balance-production.up.railway.app/api/v1/health/ready/](https://surprising-balance-production.up.railway.app/api/v1/health/ready/)
- `ready` publico validado con:
  - `ready = true`
  - `database = up`
  - `redis = up`

### 3.3 Baseline local, runtime remoto y datos no versionados

El baseline local de referencia sigue siendo:

- `leasemanager_migration_run_20260409_v7`

Y durante este tramo siguio usandose como base local operable sobre PostgreSQL.

Ademas, hoy existen dos capas de datos/estado relevantes:

1. local:
   - usuario local `admin` de desarrollo;
   - usuarios demo reproducibles:
     - `demo-admin`
     - `demo-operador`
     - `demo-revisor`
     - `demo-socio`
   - registros `TEST LOCAL` en cadena operativa, contable y tributaria;
2. remoto/publico:
   - backend publico actualmente apuntando al Postgres de staging Supabase;
   - usuarios demo sembrados en la base remota mediante `seed_demo_access`;
   - data remota todavia escasa, por lo que muchas vistas publicas muestran `0 registros` sin que eso implique fallo funcional.

Regla critica de continuidad:

- esos datos locales y remotos existen hoy;
- no son parte versionada del repositorio;
- un thread nuevo no debe asumir que existiran si la base local o remota se recrea desde cero.

## 4. Jerarquia de verdad hoy

La jerarquia correcta hoy es:

1. fuentes primarias del set activo:
   - [PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md)
   - [ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md](/D:/Proyectos/LeaseManager/Produccion%201.0/02_ADR_Activos/ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md)
   - [ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md](/D:/Proyectos/LeaseManager/Produccion%201.0/02_ADR_Activos/ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md)
2. roadmap y dependencias activas:
   - [ROADMAP_TECNICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md)
   - [MODULOS_Y_DEPENDENCIAS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md)
3. implementacion viva del greenfield:
   - [App.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/App.tsx)
   - [api.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/api.ts)
   - [shell.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/shell.tsx)
   - [view-config.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/view-config.ts)
   - workspaces extraidos del backoffice;
   - [permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/permissions.py)
   - [scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/scope_access.py)
   - [seed_demo_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/seed_demo_access.py)
   - vistas, serializers, scopes y tests de `audit`, `documentos` y `canales`;
   - [health/views.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/health/views.py)
4. topologia de deploy y runtime:
   - [DEPLOY_FRONTEND_VERCEL.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/DEPLOY_FRONTEND_VERCEL.md)
   - [DEPLOY_BACKEND_GREENFIELD.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/DEPLOY_BACKEND_GREENFIELD.md)
   - [ROLL_OUT_BACKEND_FRONTEND.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ROLL_OUT_BACKEND_FRONTEND.md)
   - [connect-frontend-to-backend.ps1](/D:/Proyectos/LeaseManager/Produccion%201.0/scripts/connect-frontend-to-backend.ps1)
   - [railway.web.json](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/railway.web.json)
   - [railway.worker.json](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/railway.worker.json)
   - estado publico actualmente operativo de Vercel y Railway;
5. para el dominio comunitario ya cerrado:
   - [ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md)
   - [migration/enrichments.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/enrichments.py)
   - [migration/importers.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/importers.py)
6. artefactos validados de migracion y verificacion;
7. el paquete `HANDOFF/` actualizado;
8. respuestas externas literales archivadas.

Si hay conflicto:

- manda la fuente primaria;
- luego la implementacion validada;
- luego la topologia de deploy/versionado vigente;
- luego el handoff;
- y la divergencia debe quedar explicitada.

## 5. Divergencias y rectificaciones que deben conocerse

### 5.1 El handoff previo ya quedo materialmente viejo

El paquete anterior seguia centrado en:

- seed demo;
- hardening inicial de RBAC/scope;
- modularizacion todavia parcial;
- necesidad de configurar un backend publico.

Eso ya no representa la foto actual completa.

### 5.2 Divergencia entre handoff viejo y estado real del frontend

A esta altura:

- el frontend ya no esta en “modularizacion inicial”;
- `Canales`, `Reporting`, `Contabilidad` y `SII` ya estan extraidos;
- existe una capa compartida de backoffice mas rica (`api.ts`, `shell.tsx`, `view-config.ts`);
- el sitio publico ya responde.

Aqui manda el codigo vivo y la validacion publica, no el handoff viejo.

### 5.3 Divergencia corregida sobre VITE_API_BASE_URL

El estado viejo dejaba como bloqueo:

- falta de `VITE_API_BASE_URL`
- frontend publico inutilizable fuera de local

Estado actual:

- `VITE_API_BASE_URL` ya quedo configurado en Vercel;
- el frontend publico y el backend publico ya se comunican;
- el login publico quedo validado con `demo-admin`.

### 5.4 Divergencia corregida sobre despliegue Git/Vercel

Durante el rollout aparecio una divergencia real:

- el proyecto Vercel no estaba conectado al repo Git;
- y ademas estaba desplegando desde el root equivocado.

Estado actual:

- Vercel ya esta conectado a [puigjoaco/LeaseManager](https://github.com/puigjoaco/LeaseManager);
- el `Root Directory` quedo fijado a `frontend`;
- los rebuilds productivos ya se disparan desde `main`.

### 5.5 Ruido puntual de browser automation

Durante parte de la validacion publica:

- algunas sesiones de Playwright mostraron falsos negativos transitorios (`unreachable`, `ERR_NO_BUFFER_SPACE`) aun cuando:
  - el backend respondia `200`;
  - CORS respondia correctamente;
  - y el login directo al endpoint funcionaba.

Consecuencia:

- para dudas de conectividad publica, mandan:
  - el `health` publico real;
  - el `ready` publico real;
  - las respuestas HTTP directas con `Origin`;
  - y luego el browser reset si Playwright queda contaminado.

## 6. Como debe leerse el material hoy

La forma correcta de retomar hoy no es:

- volver a abrir el diseno comunitario;
- volver a discutir el nombre del proyecto;
- seguir pensando que el siguiente trabajo real es “terminar de extraer workspaces”;
- ni reabrir bootstrap de Vercel/Railway como si siguiera pendiente.

La forma correcta de retomar hoy es:

1. asumir que el backoffice base ya existe y cubre modulos operativos, de control y secundarios relevantes;
2. asumir que la API ya tiene RBAC por rol y una capa seria de scope;
3. asumir que el frontend y el backend publicos ya estan online;
4. usar PRD + roadmap como guia del sistema;
5. usar el codigo actual y el runtime publico como foto viva del producto;
6. tratar como siguiente trabajo real:
   - mantener el handoff alineado con el estado real;
   - enriquecer la data remota para que el entorno publico sea mas representativo;
   - y luego elegir el siguiente frente funcional del producto sin reabrir infraestructura ya cerrada.
