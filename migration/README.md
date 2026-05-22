# Migración read-only desde savegame/legacy LeaseManager

La carpeta `migration/` existe para inventariar y transformar fuentes
historicas o savegames de LeaseManager sin mutarlas. El root limpio activo es
`D:/Proyectos/LeaseManager`; las fuentes legacy se leen como respaldo externo.

## Principios

- el savegame o fuente legacy es solo fuente de lectura;
- no se copian secretos reales al repositorio nuevo;
- el modelo final es el canónico del root limpio activo, no el schema legacy de Supabase;
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
- `bundles/`: salida local no versionada para bundles y reportes generados

Los JSON de `migration/bundles/` estan ignorados por Git. Si contienen datos
legacy, RUTs, cuentas, direcciones o resultados de staging, deben mantenerse
fuera del repo versionado o en almacenamiento seguro autorizado.

El acceptance deterministico ejecuta `scripts/assert-repo-hygiene.ps1` para
bloquear regresiones en el root activo: `.env`, DBs locales/historicas, bundles
generados, dumps, snapshots, certificados y evidencia local no deben quedar
versionados. Este guard no resuelve el historial Git ni savegames sensibles
asociados a `BLK-008`; solo protege el estado vivo del repositorio.

## Flujo recomendado

Configura el contexto sensible del backlog actual fuera del repo antes de
resolver comunidades o ejecutar el runner validado. Usa valores reales solo en
terminal/secret manager autorizado:

```powershell
$env:MIGRATION_CURRENT_COMMUNITY_REPRESENTATIVE_RUT="<rut-representante>"
$env:MIGRATION_CURRENT_COMMUNITY_RECAUDADORA_ACCOUNT_NUMBER="<numero-cuenta>"
$env:MIGRATION_KNOWN_SOCIO_ACCOUNT_OWNER_RUTS="<numero-cuenta-personal>=<rut-socio>"
$bundlePath="<ruta-bundle-controlado-fuera-del-repo-o-local-no-versionada>"
```

1. Exportar bundle canónico read-only:

```powershell
cd "D:/Proyectos/LeaseManager"
$env:LEGACY_DATABASE_URL="postgresql://..."
backend\.venv\Scripts\python.exe migration\scripts\export_legacy_seed_bundle.py --output $bundlePath
```

2. Revisar warnings y `unresolved` del bundle.

3. Importar entidades determinísticas al backend nuevo:

```powershell
cd "D:/Proyectos/LeaseManager"
backend\.venv\Scripts\python.exe migration\scripts\import_seed_bundle.py $bundlePath
```

4. Resolver automáticamente las comunidades actuales del backlog que quedan como `migration.propiedad.owner_manual_required`:

```powershell
cd "D:/Proyectos/LeaseManager"
backend\.venv\Scripts\python.exe migration\scripts\resolve_current_community_resolutions.py
```

5. Reejecutar el import del mismo bundle:

```powershell
cd "D:/Proyectos/LeaseManager"
backend\.venv\Scripts\python.exe migration\scripts\import_seed_bundle.py $bundlePath
```

6. Reejecutar una tercera vez para validar idempotencia.

Alternativa equivalente en un solo comando:

```powershell
cd "D:/Proyectos/LeaseManager"
backend\.venv\Scripts\python.exe migration\scripts\run_current_migration_flow.py $bundlePath
```

Rehearsal completamente automatizado sobre una base PostgreSQL nueva:

```powershell
cd "D:/Proyectos/LeaseManager"
backend\.venv\Scripts\python.exe migration\scripts\rehearse_current_migration_flow.py leasemanager_migration_run_YYYYMMDD_vN --bundle-path $bundlePath --output migration\bundles\rehearse_current_migration_flow.local.json
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
cd "D:/Proyectos/LeaseManager"
$env:DATABASE_URL="postgresql://..."
backend\.venv\Scripts\python.exe migration\scripts\promote_current_migration_flow.py $bundlePath --output migration\bundles\promote_current_migration_flow.local.json
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


