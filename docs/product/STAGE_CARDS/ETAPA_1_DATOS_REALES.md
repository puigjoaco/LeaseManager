# Etapa 1 - Datos reales y matriz base

## Objetivo

Confirmar entidades, propiedades, contratos, cuentas, facturacion y reglas base
contra datos reales o snapshot controlado.

## Alcance

- Socios, empresas, comunidades y participaciones.
- Propiedades, cuentas recaudadoras y mandatos.
- Arrendatarios, contratos, periodos, garantias y propiedades por contrato.
- Matriz contrato-propiedad-cuenta-facturacion.

## Gate

- Snapshot o fuente real autorizada.
- Extractores read-only.
- Sin secretos versionados.
- Clasificacion de cada agregado migrable.
- Validacion de no duplicar propiedades por rol de avaluo ni identidad
  operativa fuerte; sin hardcodear montos.
- Auditor reproducible de matriz:

```powershell
cd "D:/Proyectos/LeaseManager"
$env:DATABASE_URL="<snapshot-controlado-o-db-real-autorizada>"
.\scripts\run-stage1-snapshot-gate.ps1 -SourceKind snapshot_controlado -SourceLabel "<etiqueta-no-sensible>" -RunMigrations
```

## Salida

La etapa no cierra si no existe evidencia de datos reales/controlados. Codigo
preparado sin esa evidencia queda `implementado_sin_evidencia`.

Procedimiento operativo: `docs/product/STAGE1_SNAPSHOT_INTAKE_MAYO_2026.md`.
