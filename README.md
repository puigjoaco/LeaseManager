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

### Backend

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0/backend"
.\\.venv\\Scripts\\python.exe manage.py check
```

### Frontend

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0/frontend"
npm run build
```

### Infra local

```powershell
docker compose -f "D:/Proyectos/LeaseManager/Produccion 1.0/infra/docker-compose.yml" up -d
```

### Inventario legacy

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
backend\\.venv\\Scripts\\python.exe migration\\scripts\\inventory_root_assets.py
```

## Estado actual

Ya existe una `PlataformaBase` mínima:
- auth por token
- roles/scopes base
- auditoría
- healthchecks
- shell inicial de backoffice
- inventarios sanitizados del sistema legacy

## Regla de conflicto

Si hay conflicto entre documentación o implementación:

1. manda `PRD_CANONICO`
2. luego `MATRIZ_GATES_EXTERNOS`
3. luego ADRs activos
4. luego el código greenfield
5. lo histórico nunca prevalece sobre el set activo

