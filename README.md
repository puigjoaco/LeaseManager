# LeaseManager - Root limpio

Este root contiene dos cosas al mismo tiempo:

1. El set canonico que define el sistema.
2. La codebase greenfield del proyecto nuevo.

## Regla principal

- Este repositorio es el root limpio activo del proyecto nuevo.
- La rama activa normal es `main`, sincronizada con `origin/main`.
- Las ramas `codex/...` y worktrees hermanos son laboratorios tacticos.
- El root historico/sucio quedo preservado como savegame read-only para
  inventario, migracion y extraccion. No se trabaja encima de ese respaldo.
- El PRD Canonico Mayo 2026 ya esta aceptado y vive en
  `01_Set_Vigente/PRD_CANONICO.md`.

## Que leer primero

1. [AGENTS.md](./AGENTS.md)
2. [ORDEN_DE_LECTURA.md](./ORDEN_DE_LECTURA.md)
3. [docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md](./docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md)
4. [01_Set_Vigente/PRD_CANONICO.md](./01_Set_Vigente/PRD_CANONICO.md)
5. [01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md](./01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md)
6. [docs/architecture/ARQUITECTURA_MAESTRA_LEASEMANAGER.md](./docs/architecture/ARQUITECTURA_MAESTRA_LEASEMANAGER.md)
7. [docs/product/PLAN_EJECUCION_TRAZABLE_CIERRE_MAYO_2026.md](./docs/product/PLAN_EJECUCION_TRAZABLE_CIERRE_MAYO_2026.md)

## Estructura

### Set canonico y gobierno

- `01_Set_Vigente`: producto, reglas, boundary y gates vigentes.
- `02_ADR_Activos`: decisiones tecnicas activas.
- `03_Ejecucion_Tecnica`: orden tecnico de construccion.
- `04_Auditoria_y_Cierre`: cierre del set activo.
- `08_Auditoria_Stack`: auditoria comparativa y ADR final del stack.
- `docs/governance`: fuente de verdad y protocolo operativo.
- `docs/architecture`: arquitectura de producto.
- `docs/product`: anexos, plan trazable, etapas, evidencia y bloqueos.
- `docs/operations`: runbooks de operacion y cutover.

### Trazabilidad historica

- `05_Contexto_Historico`: historico consolidado.
- `06_Fuentes_PRD_1_26`: PRD crudos.
- `07_ADR_Historicos_o_Podados`: decisiones historicas fuera del boundary
  activo.

### Codebase greenfield

- `backend/`: Django 5 + DRF + Celery.
- `frontend/`: React + TypeScript + Vite.
- `infra/`: PostgreSQL y Redis locales.
- `migration/`: inventarios read-only y mapeos legacy -> canonico.

## Arranque rapido

### Infra local

```powershell
docker compose -f "infra/docker-compose.yml" up -d
```

### Backend

```powershell
cd backend
.\\.venv\\Scripts\\python.exe manage.py check
.\\.venv\\Scripts\\python.exe manage.py migrate
.\\.venv\\Scripts\\python.exe manage.py seed_demo_access
.\\.venv\\Scripts\\python.exe manage.py runserver 127.0.0.1:8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

### Smoke checks

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/v1/health/"
npm run build
```

### Inventario legacy

```powershell
backend\\.venv\\Scripts\\python.exe migration\\scripts\\inventory_root_assets.py
```

## Estado actual

Ya existe una `PlataformaBase` operable y un backoffice usable.

Hoy estan abiertos y operables en la app local:

- `Patrimonio`
- `Operacion`
- `Contratos`
- `Cobranza`
- `Conciliacion`
- `Contabilidad`
- `SII`
- `Reporting`

Ademas, el backend ya incorpora:

- auth por token;
- RBAC efectivo por rol;
- seed reproducible de perfiles demo;
- filtrado inicial por scope para lectura;
- hardening inicial de writes y acciones por scope.

## Perfiles demo locales

Despues de correr `manage.py seed_demo_access`, quedan disponibles estos
usuarios:

- `demo-admin` / `demo12345`
- `demo-operador` / `demo12345`
- `demo-revisor` / `demo12345`
- `demo-socio` / `demo12345`

Uso recomendado:

- `demo-operador`: validar modulos operativos y navegacion transversal.
- `demo-revisor`: validar `Contabilidad`, `SII` y `Reporting` en solo lectura.
- `demo-socio`: validar resumen propio y restricciones de acceso.

## Validacion recomendada

Antes de dar por cerrado un bloque de trabajo:

1. levantar backend y frontend locales;
2. resembrar perfiles demo con `manage.py seed_demo_access`;
3. probar al menos `demo-operador`, `demo-revisor` y `demo-socio`;
4. confirmar que backend responde coherente con tests y no con un proceso viejo
   en memoria;
5. actualizar trazabilidad, evidencia y bloqueos si el bloque afecta cierre de
   producto.

## Regla de conflicto

Si hay conflicto entre documentacion o implementacion:

1. manda `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md` para estado de fuentes;
2. manda `PRD_CANONICO` para producto vigente;
3. luego `MATRIZ_GATES_EXTERNOS`;
4. luego ADRs activos;
5. luego arquitectura y plan trazable;
6. luego el codigo greenfield;
7. lo historico nunca prevalece sobre el set activo.
