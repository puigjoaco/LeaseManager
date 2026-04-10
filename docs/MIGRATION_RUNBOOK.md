# Migration Runbook

## Read-only policy

- No modificar `D:/Proyectos/LeaseManager` durante extracción.
- No persistir secretos reales en archivos versionados.
- Reprovisionar certificados y credenciales desde un manifiesto seguro externo.

## Inventarios esperados

- secretos
- activos sensibles
- schema legacy
- integraciones legacy
- matriz legacy -> canónico

## Comando sugerido

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0/backend"
.\\.venv\\Scripts\\python.exe ..\\migration\\scripts\\inventory_root_assets.py
```

## Flujo validado de migración local del backlog actual

Secuencia validada al `2026-04-08` sobre PostgreSQL local del greenfield:

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
backend\.venv\Scripts\python.exe migration\scripts\import_seed_bundle.py migration\bundles\legacy_seed_bundle.regenerated.current_2026-04-08.json
backend\.venv\Scripts\python.exe migration\scripts\resolve_current_community_resolutions.py
backend\.venv\Scripts\python.exe migration\scripts\import_seed_bundle.py migration\bundles\legacy_seed_bundle.regenerated.current_2026-04-08.json
backend\.venv\Scripts\python.exe migration\scripts\import_seed_bundle.py migration\bundles\legacy_seed_bundle.regenerated.current_2026-04-08.json
```

Resultado esperado:

- `56` contratos
- `748` periodos
- `66` mandatos operativos
- `0` resoluciones manuales abiertas
- `16` comunidades
- `70` participaciones comunitarias activas

Runner equivalente validado en limpio:

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
backend\.venv\Scripts\python.exe migration\scripts\run_current_migration_flow.py migration\bundles\legacy_seed_bundle.regenerated.current_2026-04-08.json --output migration\bundles\run_current_migration_flow.json
```

Este runner ejecuta internamente:

1. `import_seed_bundle.py`
2. `resolve_current_community_resolutions.py`
3. `import_seed_bundle.py`
4. `import_seed_bundle.py`

Por defecto, el runner falla con código no-cero si `final_state` no coincide con el estado esperado del backlog actual.

Rehearsal local totalmente automatizado:

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
backend\.venv\Scripts\python.exe migration\scripts\rehearse_current_migration_flow.py leasemanager_migration_run_YYYYMMDD_vN --output migration\bundles\rehearse_current_migration_flow.json
```

Validación operativa realizada:

- script: [rehearse_current_migration_flow.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/scripts/rehearse_current_migration_flow.py)
- base creada automáticamente: `leasemanager_migration_run_20260410_v9`
- artefacto: [rehearse_current_migration_flow_v9.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/rehearse_current_migration_flow_v9.json)

Promoción al siguiente target PostgreSQL ya existente:

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
$env:DATABASE_URL="postgresql://..."
backend\.venv\Scripts\python.exe migration\scripts\promote_current_migration_flow.py migration\bundles\legacy_seed_bundle.regenerated.current_2026-04-08.json --output migration\bundles\promote_current_migration_flow.json
```

Validación operativa realizada contra target PostgreSQL vacío:

- script: [promote_current_migration_flow.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/scripts/promote_current_migration_flow.py)
- base de prueba: `leasemanager_migration_run_20260410_v10`
- artefacto: [promote_current_migration_flow_v10.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/promote_current_migration_flow_v10.json)

