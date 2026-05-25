# Etapa 1 - Datos reales y matriz base

## Objetivo

Confirmar entidades, propiedades, contratos, cuentas, facturacion y reglas base
contra datos reales o snapshot controlado.

## Alcance

- Socios, empresas, comunidades y participaciones.
- Propiedades, cuentas recaudadoras y mandatos.
- Arrendatarios, contactos de pago, contratos, periodos, garantias y
  propiedades por contrato.
- Codeudores solidarios cuando existan, con snapshot de identidad trazable.
- Matriz contrato-propiedad-cuenta-facturacion.

## Gate

- Snapshot o fuente real autorizada.
- Extractores read-only.
- Sin secretos versionados.
- Referencias trazables no sensibles de `AuthorizationRef` y `ResponsibleRef`
  en el gate evidencial.
- Guard deterministico de higiene del repo: `scripts/assert-repo-hygiene.ps1`
  debe pasar para evitar reintroducir `.env`, DBs locales/historicas, bundles
  generados, dumps, snapshots, certificados o evidencia local versionada.
- Clasificacion de cada agregado migrable.
- Validacion de participaciones actualmente vigentes: para activar empresas o
  comunidades solo cuentan participaciones activas con `vigente_desde` ya
  alcanzado y sin `vigente_hasta` vencido.
- Validacion de representaciones actualmente vigentes: para activar
  comunidades o bloquear desactivaciones de socios solo cuentan
  representaciones activas con `vigente_desde` ya alcanzado y sin
  `vigente_hasta` vencido; representaciones futuras no sustituyen la
  representacion vigente.
- Validacion de participantes patrimoniales activos: una participacion activa
  solo puede apuntar a un socio activo o a una empresa participante activa con
  participaciones completas.
- Validacion de transiciones de estado patrimonial: socios, empresas y
  comunidades no pueden desactivarse si sostienen propiedades,
  representaciones o participaciones activas vigentes.
- La matriz debe incluir al menos un contrato vigente o futuro; contratos solo
  historicos no constituyen evidencia operativa de Etapa 1.
- Validacion de no duplicar propiedades por rol de avaluo ni identidad
  operativa fuerte; sin hardcodear montos.
- Validacion de que cada contrato vigente o futuro tenga al menos un canal
  operativo activo asignado por su mandato.
- Validacion de que las identidades de envio activas usen `credencial_ref`
  trazable no sensible; la API debe redactar referencias sensibles heredadas.
- Validacion de transiciones operativas: cuentas recaudadoras, mandatos,
  identidades de envio y asignaciones de canal no pueden pausarse,
  suspenderse o inactivarse si dejan contratos vigentes/futuros, mandatos o
  canales activos sin cobertura operativa.
- Validacion de que cada contrato vigente o futuro este cubierto por la
  vigencia del `MandatoOperacion` que define propiedad, cuenta y facturacion;
  un mandato con contratos vigentes/futuros no puede recortar su vigencia fuera
  del rango contractual ya dependiente.
- Autoridad operativa de mandato: un `MandatoOperacion` activo que autoriza
  comunicacion o facturacion de documentos debe conservar nombre, RUT valido
  normalizado y evidencia trazable no sensible de su representante/autoridad;
  API, snapshot, backoffice y auditor Etapa 1 detectan faltantes, RUT invalido
  o referencias sensibles.
- Validacion de que cada propiedad principal o vinculada de contratos vigentes
  o futuros este activa.
- Servicios y gastos comunes estructurados: `ServicioPropiedad` registra tipo
  de servicio, proveedor/administracion, numero de cliente, evidencia opcional
  no sensible y estado; el snapshot de Patrimonio expone la lista redactada y
  el auditor Etapa 1 bloquea contratos vigentes/futuros con gastos comunes si
  la propiedad principal no tiene un gasto comun activo estructurado.
- Validacion de roles contrato-propiedad: exactamente una propiedad principal
  y, si hay pareja, una propiedad vinculada.
- Validacion de que cada contrato vigente o futuro cubra una sola propiedad o
  una pareja propiedad principal + vinculada.
- Validacion de que la pareja propiedad principal + vinculada comparta el
  `CodigoConciliacionEfectivo` de la propiedad principal.
- Validacion de codeudores solidarios: snapshot con nombre/RUT valido desde la
  API anidada y el auditor, sin duplicados activos y maximo 3 activos por
  contrato.
- Validacion de contratos con arrendatario empresa: API/modelo exigen snapshot
  de representante legal con nombre y RUT valido normalizado, y el auditor
  detecta faltantes, incompletos o RUT invalido en datos heredados.
- Contactos de pago estructurados: los arrendatarios pueden registrar contactos
  de pago activos con nombre, rol operativo, email o telefono y evidencia
  opcional no sensible; el auditor Etapa 1 bloquea contratos vigentes/futuros
  cuyo arrendatario no tenga al menos un contacto de pago activo estructurado.
- Validacion de telefonos para mensajeria: si un arrendatario usa WhatsApp
  operativo, el telefono debe estar en formato internacional; numeros locales
  o ambiguos quedan bloqueados para Canales.
- Override explicito de `IdentidadDeEnvio` por contrato: si existe, debe estar
  activo y pertenecer a la entidad facturadora o al administrador operativo
  autorizado por el mandato; Canales lo usa antes de la asignacion del mandato
  cuando coincide con el canal solicitado.
- Politica documental contractual: cada contrato vigente o futuro debe
  referenciar una `PoliticaFirmaYNotaria` activa de tipo
  `contrato_principal`; API, snapshot y auditor Etapa 1 detectan politicas
  faltantes, inactivas o de tipo documental incorrecto.
- Perfil documental de arrendatario persona natural: cuando la politica
  documental contractual lo exige, contratos vigentes/futuros requieren
  nacionalidad, estado civil y profesion; API, snapshot y auditor Etapa 1
  detectan datos faltantes en fuentes heredadas o controladas.
- Validacion de periodos contractuales existentes: cada tramo debe quedar
  dentro de la vigencia del contrato, iniciar el dia 1, cerrar el ultimo dia
  del mes y respetar numeracion cronologica antes de calcular cobranza.
- Validacion de garantias: montos/estado coherentes, fechas de recepcion y
  cierre consistentes, y saldos recibidos, devueltos o aplicados conciliados
  contra `HistorialGarantia`, incluyendo cronologia de movimientos derivados
  contra su movimiento origen. Si una garantia fue recibida parcialmente y
  sigue abierta, debe tener aceptacion formal trazable no sensible o quedar
  marcada como incompleta.
- Validacion de ajustes contractuales existentes: contrato, moneda, rango de
  meses normalizado al primer dia del mes dentro de la vigencia contractual y
  justificacion deben ser coherentes antes de usarlos en cobranza.
- Validacion de avisos de termino existentes: la fecha efectiva debe quedar
  dentro del rango del contrato asociado.
- Validacion de pagos y distribuciones existentes en el snapshot: si existen,
  deben cuadrar devengo, conciliacion, porcentaje y entidad facturadora.
- Validacion de que pagos mensuales existentes queden dentro de la vigencia
  del contrato y del periodo contractual referenciado, tengan vencimiento
  alineado al mes operativo y al dia de pago contractual, y conserven
  `CodigoConciliacionEfectivo` en rango operativo `001-999` y alineado con la
  propiedad principal del contrato.
- Validacion de que pagos mensuales existentes en estado pagado efectivo tengan
  monto pagado mayor que cero y fecha trazable de deposito, WebPay o deteccion.
- Contratos retroactivos registrados despues del dia 5 del mes operativo
  generan alerta de posible notificacion manual, y Cobranza bloquea la
  reconstruccion automatica de cobros vencidos antes del registro operativo.
  El auditor Etapa 1 reporta la alerta como advertencia y marca como defecto
  pagos existentes que reconstruyan esos cobros pasados.
- Validacion de respaldo UF para pagos existentes: si el pago mensual depende
  de periodo o ajuste en UF, debe existir `ValorUFDiario` para el primer dia
  del mes operativo.
- Verificacion segura sin fuente autorizada:

```powershell
cd "D:/Proyectos/LeaseManager"
.\scripts\run-stage1-local-readiness.ps1
```

La verificacion local diagnostica preparacion segura y debe quedar
`implementado_sin_evidencia`; no reemplaza el gate evidencial.

- Auditor reproducible de matriz, solo cuando exista autorizacion explicita
  actual para una fuente `snapshot_controlado` o `real_autorizado`:

```powershell
cd "D:/Proyectos/LeaseManager"
$env:DATABASE_URL="<snapshot-controlado-o-db-real-autorizada>"
.\scripts\run-stage1-snapshot-gate.ps1 `
  -SourceKind snapshot_controlado `
  -SourceLabel "<etiqueta-no-sensible>" `
  -AuthorizationRef "<autorizacion-no-sensible>" `
  -ResponsibleRef "<responsable-no-sensible>" `
  -RunMigrations
```

## Salida

La etapa no cierra si no existe evidencia de datos reales/controlados. Codigo
preparado sin esa evidencia queda `implementado_sin_evidencia`.

El bloqueo por falta de fuente autorizada no forma parte de la arquitectura del
producto: solo impide declarar cierre de Etapa 1. Si `BLK-002` ya esta
registrado y no hay autorizacion nueva, no se debe repetir la misma solicitud
en bucle; corresponde avanzar en preparacion segura o dejar una unica pregunta
concreta.

El release gate deterministico ejecuta esta verificacion local dentro de
`scripts/run-acceptance-workflows.ps1` para proteger la regla anti-bucle: sin
fuente autorizada, la ruta local queda `implementado_sin_evidencia`, nunca se
presenta como `snapshot_controlado` y no cierra la etapa. El estado
`bloqueado_dato_real` queda reservado para el gate evidencial contra
`snapshot_controlado` o `real_autorizado`.

Procedimiento operativo: `docs/product/STAGE1_SNAPSHOT_INTAKE_MAYO_2026.md`.
