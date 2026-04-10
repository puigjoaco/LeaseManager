# Supabase Staging Playbook

Fecha: 2026-04-10
Estado: ejecutado y validado sobre un target Supabase staging real

## Objetivo

Repetir el flujo validado del backlog actual sobre un PostgreSQL remoto en Supabase sin cambiar el pipeline del greenfield.

Resultado esperado:

- `56` contratos
- `748` periodos
- `66` mandatos
- `0` resoluciones manuales abiertas
- `16` comunidades
- `70` participaciones comunitarias activas

## Regla de conexion

Segun la documentacion oficial de Supabase:

- usar **Direct connection** solo si el host desde el que correra Django soporta IPv6;
- usar **Supavisor session mode** si el entorno es IPv4 normal o no hay certeza de soporte IPv6;
- no usar **transaction mode** para este flujo de migracion persistente.

## Fuente oficial

- Connect to your database:
  - direct connection para clientes persistentes y migraciones si hay IPv6
  - Supavisor session mode como alternativa para IPv4
- IPv4/IPv6 compatibility:
  - las conexiones directas son IPv6 por defecto
  - session mode soporta IPv4 y IPv6

## Que pedir del proyecto Supabase

En el Dashboard del proyecto:

1. abrir `Connect`
2. obtener la cadena PostgreSQL adecuada

Preferencia:

- `Session pooler` en puerto `5432` si no hay confirmacion de IPv6
- `Direct connection` en puerto `5432` solo si el entorno realmente soporta IPv6

## Target staging ya creado

Estado actual:

- organizacion: `Puig Projects`
- proyecto staging: `leasemanager-staging`
- project ref: `ubccvzaklmkiavppnzcf`
- region: `South America (São Paulo)` / `sa-east-1`

Metodo de conexion validado:

- `Session pooler` / `Shared Pooler`
- host: `aws-1-sa-east-1.pooler.supabase.com`
- puerto: `5432`
- usuario: `postgres.ubccvzaklmkiavppnzcf`

## Variables necesarias

Solo para esta promocion:

- `DATABASE_URL`

Ejemplo con session pooler:

```powershell
$env:DATABASE_URL="postgresql://postgres.<project_ref>:[PASSWORD]@aws-0-<region>.pooler.supabase.com:5432/postgres"
```

Ejemplo con direct connection:

```powershell
$env:DATABASE_URL="postgresql://postgres:[PASSWORD]@db.<project_ref>.supabase.co:5432/postgres"
```

## Comando recomendado

Usar el script pensado para un PostgreSQL ya existente:

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
$env:DATABASE_URL="postgresql://..."
backend\.venv\Scripts\python.exe migration\scripts\promote_current_migration_flow.py migration\bundles\legacy_seed_bundle.regenerated.current_2026-04-08.json --output migration\bundles\promote_current_migration_flow_supabase.json
```

## Que hace el script

1. ejecuta `migrate`
2. valida que el target quede vacio despues de migrar
3. corre el flujo validado:
   - import
   - resolucion automatica de comunidades actuales
   - rerun
   - rerun de idempotencia
4. falla con codigo no-cero si el `final_state` no coincide con el esperado

## Cuando NO correrlo

- si el proyecto Supabase ya tiene datos de negocio cargados;
- si no estas seguro de que el target debe quedar dedicado a esta migracion;
- si no tienes la cadena de conexion correcta desde `Connect`.

## Verificacion minima

El JSON final debe mostrar:

- `pre_validation.ok = true`
- `runner_result.validation.ok = true`

Y dentro de `runner_result.final_state`:

- `contratos = 56`
- `periodos = 748`
- `mandatos = 66`
- `manual_resolutions_abiertas = 0`

## Verificacion real ejecutada

Artefacto de verificacion:

- [supabase_staging_verification_2026-04-10.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/supabase_staging_verification_2026-04-10.json)
- [verify_current_migration_target_supabase.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/verify_current_migration_target_supabase.json)

Resultado validado:

- `56` contratos
- `748` periodos
- `66` mandatos
- `0` resoluciones manuales abiertas
- `16` comunidades
- `70` participaciones comunitarias activas

## Comando reusable de verificacion

```powershell
cd "D:/Proyectos/LeaseManager/Produccion 1.0"
$env:DATABASE_URL="postgresql://..."
backend\.venv\Scripts\python.exe migration\scripts\verify_current_migration_target.py --output migration\bundles\verify_current_migration_target.json
```

Ese script falla con codigo no-cero si el target no coincide con el estado esperado.
