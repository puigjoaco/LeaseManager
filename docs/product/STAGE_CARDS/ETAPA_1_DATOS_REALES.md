# Etapa 1 - Datos reales y matriz base

## Objetivo

Confirmar entidades, propiedades, contratos, cuentas, facturacion y reglas base
contra datos reales o snapshot controlado.

## Alcance

- Socios, empresas, comunidades y participaciones.
- Propiedades, cuentas recaudadoras y mandatos.
- Arrendatarios, contratos, periodos, garantias y propiedades por contrato.
- Codeudores solidarios cuando existan, con snapshot de identidad trazable.
- Matriz contrato-propiedad-cuenta-facturacion.

## Gate

- Snapshot o fuente real autorizada.
- Extractores read-only.
- Sin secretos versionados.
- Clasificacion de cada agregado migrable.
- La matriz debe incluir al menos un contrato vigente o futuro; contratos solo
  historicos no constituyen evidencia operativa de Etapa 1.
- Validacion de no duplicar propiedades por rol de avaluo ni identidad
  operativa fuerte; sin hardcodear montos.
- Validacion de que cada contrato vigente o futuro tenga al menos un canal
  operativo activo asignado por su mandato.
- Validacion de que cada contrato vigente o futuro este cubierto por la
  vigencia del `MandatoOperacion` que define propiedad, cuenta y facturacion.
- Validacion de codeudores solidarios: snapshot con nombre/RUT valido, sin
  duplicados activos y maximo 3 activos por contrato.
- Validacion de garantias: montos/estado coherentes y saldos recibidos,
  devueltos o aplicados conciliados contra `HistorialGarantia`.
- Validacion de ajustes contractuales existentes: contrato, moneda, rango de
  meses y justificacion deben ser coherentes antes de usarlos en cobranza.
- Validacion de pagos y distribuciones existentes en el snapshot: si existen,
  deben cuadrar devengo, conciliacion, porcentaje y entidad facturadora.
- Validacion de que pagos mensuales existentes conserven
  `CodigoConciliacionEfectivo` en rango operativo `001-999` y alineado con la
  propiedad principal del contrato.
- Validacion de respaldo UF para pagos existentes: si el pago mensual depende
  de periodo o ajuste en UF, debe existir `ValorUFDiario` para el primer dia
  del mes operativo.
- Auditor reproducible de matriz:

```powershell
cd "D:/Proyectos/LeaseManager"
$env:DATABASE_URL="<snapshot-controlado-o-db-real-autorizada>"
.\scripts\run-stage1-snapshot-gate.ps1 -SourceKind snapshot_controlado -SourceLabel "<etiqueta-no-sensible>" -RunMigrations
```

## Salida

La etapa no cierra si no existe evidencia de datos reales/controlados. Codigo
preparado sin esa evidencia queda `implementado_sin_evidencia`.

El bloqueo por falta de fuente autorizada no forma parte de la arquitectura del
producto: solo impide declarar cierre de Etapa 1. Si `BLK-002` ya esta
registrado y no hay autorizacion nueva, no se debe repetir la misma solicitud
en bucle; corresponde avanzar en preparacion segura o dejar una unica pregunta
concreta.

Verificacion segura sin fuente autorizada:

```powershell
cd "D:/Proyectos/LeaseManager"
.\scripts\run-stage1-local-readiness.ps1
```

El release gate deterministico ejecuta esta verificacion local dentro de
`scripts/run-acceptance-workflows.ps1` para proteger la regla anti-bucle: sin
fuente autorizada, el resultado esperado es `bloqueado_dato_real`, no cierre.

Procedimiento operativo: `docs/product/STAGE1_SNAPSHOT_INTAKE_MAYO_2026.md`.
