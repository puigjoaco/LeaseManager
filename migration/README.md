# Migración read-only desde LeaseManager

La carpeta `migration/` existe para inventariar y transformar el root actual de LeaseManager sin mutarlo.

## Principios

- el root actual es solo fuente de lectura;
- no se copian secretos reales al repositorio nuevo;
- el modelo final es el canónico de `Produccion 1.0`, no el schema actual de Supabase;
- toda incompatibilidad fuerte pasa por `MigrationDecision` o `ManualResolutionQueue`.

## Artefactos

- `contracts.py`: contratos de inventario y migración
- `readers.py`: extracción read-only desde la BD legacy
- `transformers.py`: transformación legacy -> bundle canónico
- `importers.py`: importación idempotente al modelo nuevo para entidades determinísticas
- `scripts/inventory_root_assets.py`: generador de inventarios sanitizados
- `scripts/export_legacy_seed_bundle.py`: exporta un bundle canónico desde legacy usando `LEGACY_DATABASE_URL`
- `scripts/import_seed_bundle.py`: importa al backend nuevo el bundle exportado
- `inventory/`: salidas generadas del inventario legacy

## Flujo recomendado

1. Exportar bundle canónico read-only:

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
$env:LEGACY_DATABASE_URL="postgresql://..."
backend\.venv\Scripts\python.exe migration\scripts\export_legacy_seed_bundle.py
```

2. Revisar warnings y `unresolved` del bundle.

3. Importar entidades determinísticas al backend nuevo:

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
backend\.venv\Scripts\python.exe migration\scripts\import_seed_bundle.py migration\bundles\legacy_seed_bundle.json
```

4. Resolver automáticamente las comunidades actuales del backlog que quedan como `migration.propiedad.owner_manual_required`:

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
backend\.venv\Scripts\python.exe migration\scripts\resolve_current_community_resolutions.py
```

5. Reejecutar el import del mismo bundle:

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
backend\.venv\Scripts\python.exe migration\scripts\import_seed_bundle.py migration\bundles\legacy_seed_bundle.json
```

6. Reejecutar una tercera vez para validar idempotencia.

Alternativa equivalente en un solo comando:

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
backend\.venv\Scripts\python.exe migration\scripts\run_current_migration_flow.py migration\bundles\legacy_seed_bundle.regenerated.current_2026-04-08.json
```

Rehearsal completamente automatizado sobre una base PostgreSQL nueva:

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
backend\.venv\Scripts\python.exe migration\scripts\rehearse_current_migration_flow.py leasemanager_migration_run_YYYYMMDD_vN --output migration\bundles\rehearse_current_migration_flow.json
```

Ese script:

1. crea la base si no existe;
2. ejecuta `migrate`;
3. ejecuta el runner validado;
4. devuelve el `final_state`.

El runner actual valida automaticamente que el resultado final coincida con el estado esperado del backlog actual:

- `16` comunidades
- `70` participaciones comunitarias activas
- `66` mandatos
- `56` contratos
- `748` periodos
- `0` resoluciones manuales abiertas

Promoción a un PostgreSQL ya existente y vacío:

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
$env:DATABASE_URL="postgresql://..."
backend\.venv\Scripts\python.exe migration\scripts\promote_current_migration_flow.py migration\bundles\legacy_seed_bundle.regenerated.current_2026-04-08.json --output migration\bundles\promote_current_migration_flow.json
```

Ese script:

1. ejecuta `migrate` sobre el target actual;
2. valida que el target quede vacío después de migrar;
3. corre el flujo validado;
4. falla si el `final_state` no coincide con el esperado.

## Alcance actual del import

Importa de forma idempotente:

- `Socio`
- `Empresa`
- `ComunidadPatrimonial`
- `ParticipacionPatrimonial`
- `Propiedad`
- `CuentaRecaudadora`
- `Arrendatario`

Para el backlog comunitario actual ya validado, la secuencia completa queda:

1. `import_seed_bundle.py`
2. `resolve_current_community_resolutions.py`
3. `import_seed_bundle.py`
4. `import_seed_bundle.py` otra vez para idempotencia

Resultado esperado del estado final validado:

- `56` contratos
- `748` periodos
- `66` mandatos operativos
- `0` resoluciones manuales abiertas


