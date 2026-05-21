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
- Validacion de no duplicar propiedades ni hardcodear montos.
- Auditor reproducible de matriz:

```powershell
cd "D:/Proyectos/LeaseManager/backend"
$env:DATABASE_URL="<snapshot-controlado-o-db-real-autorizada>"
.\.venv\Scripts\python.exe manage.py audit_stage1_matrix --source-kind snapshot_controlado --source-label "<etiqueta-no-sensible>" --require-data --fail-on-violations
```

## Salida

La etapa no cierra si no existe evidencia de datos reales/controlados. Codigo
preparado sin esa evidencia queda `implementado_sin_evidencia`.
