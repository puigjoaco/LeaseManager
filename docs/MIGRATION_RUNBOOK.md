# Migration Runbook

## Read-only policy

- No modificar los savegames historicos durante extraccion.
- No ejecutar backfills ni promociones reales sin preflight, backup y
  confirmacion explicita.
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
cd "D:/Proyectos/LeaseManager"
backend\\.venv\\Scripts\\python.exe migration\\scripts\\inventory_root_assets.py
```

## Flujo validado de migración local del backlog actual

Secuencia validada al `2026-04-08` sobre PostgreSQL local del greenfield:

Antes de resolver comunidades actuales o correr el runner, declara el contexto
sensible fuera del repo. No versionar estos valores:

```powershell
$env:MIGRATION_CURRENT_COMMUNITY_REPRESENTATIVE_RUT="<rut-representante>"
$env:MIGRATION_CURRENT_COMMUNITY_RECAUDADORA_ACCOUNT_NUMBER="<numero-cuenta>"
$env:MIGRATION_KNOWN_SOCIO_ACCOUNT_OWNER_RUTS="<numero-cuenta-personal>=<rut-socio>"
$bundlePath="<ruta-bundle-controlado-fuera-del-repo-o-local-no-versionada>"
```

```powershell
cd "D:/Proyectos/LeaseManager"
backend\.venv\Scripts\python.exe migration\scripts\import_seed_bundle.py $bundlePath
backend\.venv\Scripts\python.exe migration\scripts\resolve_current_community_resolutions.py
backend\.venv\Scripts\python.exe migration\scripts\import_seed_bundle.py $bundlePath
backend\.venv\Scripts\python.exe migration\scripts\import_seed_bundle.py $bundlePath
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
cd "D:/Proyectos/LeaseManager"
backend\.venv\Scripts\python.exe migration\scripts\run_current_migration_flow.py $bundlePath --output migration\bundles\run_current_migration_flow.local.json
```

Este runner ejecuta internamente:

1. `import_seed_bundle.py`
2. `resolve_current_community_resolutions.py`
3. `import_seed_bundle.py`
4. `import_seed_bundle.py`

Por defecto, el runner falla con código no-cero si `final_state` no coincide con el estado esperado del backlog actual.

Rehearsal local totalmente automatizado:

```powershell
cd "D:/Proyectos/LeaseManager"
backend\.venv\Scripts\python.exe migration\scripts\rehearse_current_migration_flow.py leasemanager_migration_run_YYYYMMDD_vN --bundle-path $bundlePath --output migration\bundles\rehearse_current_migration_flow.local.json
```

Validación operativa realizada:

- script: [rehearse_current_migration_flow.py](/D:/Proyectos/LeaseManager/migration/scripts/rehearse_current_migration_flow.py)
- base creada automáticamente: `leasemanager_migration_run_20260410_v9`
- artefacto historico: `rehearse_current_migration_flow_v9.json` disponible solo en savegame/historial Git; no versionar en el root activo.

Promoción al siguiente target PostgreSQL ya existente:

```powershell
cd "D:/Proyectos/LeaseManager"
$env:DATABASE_URL="postgresql://..."
backend\.venv\Scripts\python.exe migration\scripts\promote_current_migration_flow.py $bundlePath --output migration\bundles\promote_current_migration_flow.local.json
```

Validación operativa realizada contra target PostgreSQL vacío:

- script: [promote_current_migration_flow.py](/D:/Proyectos/LeaseManager/migration/scripts/promote_current_migration_flow.py)
- base de prueba: `leasemanager_migration_run_20260410_v10`
- artefacto historico: `promote_current_migration_flow_v10.json` disponible solo en savegame/historial Git; no versionar en el root activo.


