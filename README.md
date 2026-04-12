# Produccion 1.0 - LeaseManager

Este root ya no es solo un paquete documental. Ahora contiene dos cosas al mismo tiempo:

1. El **set canónico** que define el sistema (`01` a `08`)
2. La **codebase greenfield** del proyecto nuevo (`backend`, `frontend`, `infra`, `migration`, `docs`)

## Regla principal

- `D:/Proyectos/LeaseManager/Produccion 1.0` es el root activo del proyecto nuevo.
- `D:/Proyectos/LeaseManager` queda como sistema **legacy read-only** para inventario, migración y extracción.

## Qué leer primero

1. [AGENTS.md](./AGENTS.md)
2. [ORDEN_DE_LECTURA.md](./ORDEN_DE_LECTURA.md)
3. [01_Set_Vigente/PRD_CANONICO.md](./01_Set_Vigente/PRD_CANONICO.md)
4. [01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md](./01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md)
5. [08_Auditoria_Stack/ADR_STACK_FINAL.md](./08_Auditoria_Stack/ADR_STACK_FINAL.md)

## Estructura

### Set canónico

- `01_Set_Vigente`: producto, reglas, boundary y gates
- `02_ADR_Activos`: decisiones técnicas activas
- `03_Ejecucion_Tecnica`: orden de construcción
- `04_Auditoria_y_Cierre`: cierre del set activo
- `05_Contexto_Historico`: histórico consolidado
- `06_Fuentes_PRD_1_26`: PRD crudos
- `07_ADR_Historicos_o_Podados`: decisiones históricas fuera del boundary activo
- `08_Auditoria_Stack`: auditoría comparativa y ADR final del stack

### Codebase greenfield

- `backend/`: Django 5 + DRF + Celery
- `frontend/`: React + TypeScript + Vite
- `infra/`: PostgreSQL y Redis locales
- `migration/`: inventarios read-only y mapeos legacy -> canónico
- `docs/`: bootstrap y runbooks del greenfield

## Arranque rápido

### Infra local

```powershell
docker compose -f "D:/Proyectos/LeaseManager/Produccion 1.0/infra/docker-compose.yml" up -d
```

### Backend

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0/backend"
.\\.venv\\Scripts\\python.exe manage.py check
.\\.venv\\Scripts\\python.exe manage.py migrate
.\\.venv\\Scripts\\python.exe manage.py seed_demo_access
.\\.venv\\Scripts\\python.exe manage.py runserver 127.0.0.1:8000
```

### Frontend

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0/frontend"
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
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
backend\\.venv\\Scripts\\python.exe migration\\scripts\\inventory_root_assets.py
```

## Estado actual

Ya existe una `PlataformaBase` operable y un backoffice usable.

Hoy están abiertos y operables en la app local:

- `Patrimonio`
- `Operacion`
- `Contratos`
- `Cobranza`
- `Conciliacion`
- `Contabilidad`
- `SII`
- `Reporting`

Además, el backend ya incorpora:

- auth por token;
- RBAC efectivo por rol;
- seed reproducible de perfiles demo;
- filtrado inicial por scope para lectura;
- hardening inicial de writes y acciones por scope.

## Perfiles demo locales

Después de correr `manage.py seed_demo_access`, quedan disponibles estos usuarios:

- `demo-admin` / `demo12345`
- `demo-operador` / `demo12345`
- `demo-revisor` / `demo12345`
- `demo-socio` / `demo12345`

Uso recomendado:

- `demo-operador`: validar módulos operativos y navegación transversal;
- `demo-revisor`: validar `Contabilidad`, `SII` y `Reporting` en solo lectura;
- `demo-socio`: validar resumen propio y restricciones de acceso.

## Validación recomendada

Antes de dar por cerrado un bloque de trabajo:

1. levantar backend y frontend locales;
2. resembrar perfiles demo con `manage.py seed_demo_access`;
3. probar al menos `demo-operador`, `demo-revisor` y `demo-socio`;
4. confirmar que backend responde coherente con tests y no con un proceso viejo en memoria.

## Regla de conflicto

Si hay conflicto entre documentación o implementación:

1. manda `PRD_CANONICO`
2. luego `MATRIZ_GATES_EXTERNOS`
3. luego ADRs activos
4. luego el código greenfield
5. lo histórico nunca prevalece sobre el set activo

