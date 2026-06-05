# Etapa 7 - Reporting trazable

## Objetivo

Entregar reportes internos solo cuando sus cifras deriven de datos, ledger,
documentos o procesos tributarios trazables.

## Alcance

- Resumen financiero mensual.
- Libros contables por periodo.
- Resumen tributario anual.
- Visualizacion de trazabilidad en backoffice.

## Gate local

- El resumen financiero mensual requiere cierre mensual aprobado para cada
  empresa incluida, eventos contables con origen y asiento contable posteado y
  cuadrado, con `hash_integridad` presente y vigente.
- Los libros por periodo requieren `LibroDiario`, `LibroMayor` y
  `BalanceComprobacion` aprobados, resumen no vacio, balance cuadrado y cierre
  mensual aprobado.
- El resumen tributario anual requiere `ProcesoRentaAnual` preparado o superior,
  `resumen_anual` con ejercicio y obligaciones, y DDJJ/F22 asociados con resumen
  trazable. Estados aprobados, observados, rectificados o presentados requieren
  referencia externa trazable. Cada empresa incluida debe tener
  `ConfiguracionFiscalEmpresa` activa propia.
- La API de resumen tributario anual bloquea procesos anuales finales sin
  `paquete_ddjj_ref` o `borrador_f22_ref` trazable, y tambien bloquea esas
  referencias cuando contienen URLs, tokens, credenciales o valores sensibles.
- La API de resumen tributario anual bloquea consultas sin
  `ProcesoRentaAnual` incluido y documentos DDJJ/F22 heredados cuyo proceso
  anual no coincide con la empresa y ano tributario del documento.
- El `fiscal_year` reportado por `ProcesoRentaAnual`, DDJJ y F22 debe
  corresponder al ano comercial inmediatamente anterior al `anio_tributario`;
  la API bloquea reportes desalineados y readiness los marca como brecha.
- El resumen tributario anual redacta `paquete_ref`, `borrador_ref` y payloads
  anuales sensibles heredados antes de exponerlos al backoffice.
- `audit_stage7_reporting_readiness` reporta payloads anuales sensibles en
  `resumen_anual`, `resumen_paquete` y `resumen_f22` como brecha bloqueante de
  reporting, manteniendo solo conteos/codigos y sin exponer valores.
- `audit_stage7_reporting_readiness` tambien clasifica explicitamente como
  bloqueantes las referencias finales sensibles de ProcesoRentaAnual, DDJJ y
  F22, sin exponer esos valores.
- `audit_stage7_reporting_readiness` clasifica explicitamente como bloqueantes
  DDJJ/F22 heredados asociados a un proceso anual de otra empresa o ano
  tributario.
- Los eventos `sii.ddjj_preparacion.status_updated` y
  `sii.f22_preparacion.status_updated` que sustentan reporting tributario anual
  deben conservar metadata minima de transicion con `campo_estado`,
  `estado_anterior` y `estado_nuevo`; readiness bloquea snapshots heredados
  sin esa auditoria trazable.
- Si falta alguno de esos origenes, la API responde con bloqueo de
  trazabilidad y no entrega el reporte como valido.
- `audit_stage7_reporting_readiness` consolida readiness local de resumen
  financiero mensual, libros por periodo, tributario anual, prueba API,
  visualizacion backoffice y responsables sin ejecutar smoke publico ni leer
  datos reales.
- El dashboard operativo expone en API y backoffice los contadores PRD de
  pagos pendientes, movimientos sin clasificar, diferencias banco/sistema,
  contratos por vencer, avisos de termino, garantias incompletas, fallas de
  integracion y cierres bloqueados, respetando scope de acceso.
- El resumen financiero mensual expone en API y backoffice
  `control_cierre_mensual`, unificando por empresa cierre contable, banco
  cuadrado, obligaciones mensuales, F29 cuando aplica y bloqueadores del
  periodo sin llamar bancos ni SII.
- `audit_stage7_reporting_readiness` solo puede cerrar con `--source-kind`
  `snapshot_controlado` o `real_autorizado`; `local`, `fixture` y `demo`
  diagnostican brechas pero no habilitan cierre de Reporting.
- Una fuente autorizada debe declarar `--source-label` y `--authorization-ref`
  no sensibles. El guard `run-stage7-readiness-gate.ps1` reenvia
  `ReportingSourceLabel` y `ReportingAuthorizationRef` al auditor y mantiene el
  diagnostico local como no cerrable.

## Salida

Reporting sigue sin cierre final mientras falte evidencia con cierres completos,
snapshot controlado o datos reales autorizados. El gate local evita reportes sin
origen verificable, pero no reemplaza la evidencia externa/controlada requerida
por etapas anteriores.
