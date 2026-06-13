# Etapa 7 - Reporting trazable

## Objetivo

Entregar reportes internos revisables solo cuando sus cifras deriven de datos,
ledger, documentos o procesos tributarios trazables. Reporting prueba origen y
consistencia; no convierte un dossier contable o tributario en presentacion
externa final.

## Alcance

- Resumen financiero mensual.
- Libros contables por periodo.
- Resumen tributario anual.
- Visualizacion de trazabilidad en backoffice.
- Vistas de control para revision responsable.

## Gate local

- El resumen financiero mensual requiere cierre mensual aprobado para cada
  empresa incluida, eventos contables con origen y asiento contable posteado y
  cuadrado, con `hash_integridad` presente y vigente.
- La API de resumen financiero mensual bloquea antes de entregar reporte los
  eventos contabilizados sin origen trazable (`reporting.event_origin_missing`)
  y los asientos contabilizados sin `hash_integridad`, con hash desactualizado o
  sin movimientos contables trazables.
- La API de resumen financiero mensual separa los bloqueos de asientos no
  posteados y asientos descuadrados con codigos especificos, alineados con
  `audit_stage7_reporting_readiness`.
- Los libros por periodo requieren `LibroDiario`, `LibroMayor` y
  `BalanceComprobacion` aprobados, resumen no vacio, balance cuadrado y cierre
  mensual aprobado.
- La API de libros por periodo usa codigos alineados con readiness para
  snapshots faltantes (`reporting.books_snapshot_missing_for_close`),
  snapshots sin resumen (`reporting.books_snapshot_summary_missing`) y balances
  no cuadrados (`reporting.books_balance_not_square`).
- El resumen tributario anual requiere `ProcesoRentaAnual` preparado o superior,
  `resumen_anual` con ejercicio y obligaciones, y DDJJ/F22 asociados con resumen
  trazable. Estados aprobados, observados, rectificados o presentados requieren
  referencia externa trazable. Cada empresa incluida debe tener
  `ConfiguracionFiscalEmpresa` activa propia.
- El resumen tributario anual tambien requiere `responsable_revision_ref` no
  sensible para ProcesoRentaAnual, DDJJ y F22 en estados aprobados, observados,
  rectificados o presentados. Si falta o contiene URL/token/credencial, la API
  bloquea el reporte con codigos `reporting.annual_*_responsible_ref_*` sin
  exponer el valor.
- El resumen tributario anual es evidencia interna de trazabilidad del dossier;
  no declara presentacion anual final ni reemplaza revision experta/oficial.
- La API de resumen tributario anual separa la falta de configuracion fiscal
  activa por proceso anual, DDJJ y F22, alineando sus codigos con
  `audit_stage7_reporting_readiness`.
- La API de resumen tributario anual bloquea DDJJ y F22 con capacidad SII de
  otra familia, usando codigos `reporting.annual_ddjj_invalid` y
  `reporting.annual_f22_invalid` alineados con readiness.
- La API de resumen tributario anual trata `obligaciones=[]` en
  `ProcesoRentaAnual.resumen_anual` como resumen incompleto; no entrega reporte
  verificado si el proceso no conserva obligaciones mensuales trazables.
- La API de resumen tributario anual bloquea procesos anuales, DDJJ y F22 que
  aun esten en estados no trazables, aunque conserven resumen heredado.
- La API de resumen tributario anual usa codigos separados para procesos sin
  DDJJ, procesos sin F22, DDJJ sin resumen y F22 sin resumen, alineados con
  `audit_stage7_reporting_readiness`.
- La API de resumen tributario anual bloquea procesos anuales finales sin
  `paquete_ddjj_ref` o `borrador_f22_ref` trazable, y tambien bloquea esas
  referencias cuando contienen URLs, tokens, credenciales o valores sensibles;
  ambos refs finales del proceso anual tienen cobertura focal en API.
- La API de resumen tributario anual trata referencias finales DDJJ/F22 vacias
  o compuestas solo por espacios como faltantes, incluso si provienen de datos
  heredados que saltaron la normalizacion del modelo.
- La API de resumen tributario anual bloquea referencias DDJJ/F22 sensibles
  heredadas en cualquier estado trazable, sin exponer el valor sensible en la
  respuesta.
- La API de resumen tributario anual bloquea payloads sensibles de
  `ProcesoRentaAnual`, DDJJ y F22 en cualquier estado trazable,
  manteniendo respuestas sin URLs, tokens, credenciales ni claves sensibles.
- La API de resumen tributario anual bloquea consultas sin
  `ProcesoRentaAnual` incluido y documentos DDJJ/F22 heredados cuyo proceso
  anual no coincide con la empresa y ano tributario del documento, usando
  codigos separados para DDJJ y F22 alineados con readiness.
- El `fiscal_year` reportado por `ProcesoRentaAnual`, DDJJ y F22 debe
  corresponder al ano comercial inmediatamente anterior al `anio_tributario`;
  la API bloquea reportes desalineados con codigos separados para proceso,
  DDJJ y F22, incluyendo el documento afectado, ano observado y ano esperado.
- El resumen tributario anual bloquea `paquete_ref`, `borrador_ref` y payloads
  anuales sensibles heredados antes de exponerlos al backoffice como reporte
  valido.
- `audit_stage7_reporting_readiness` reporta payloads anuales sensibles en
  `resumen_anual`, `resumen_paquete` y `resumen_f22` como brecha bloqueante de
  reporting, manteniendo solo conteos/codigos y sin exponer valores.
- `audit_stage7_reporting_readiness` tambien clasifica explicitamente como
  bloqueantes las referencias finales sensibles de ProcesoRentaAnual, DDJJ y
  F22, sin exponer esos valores.
- `audit_stage7_reporting_readiness` y la API anual clasifican como bloqueantes
  los responsables de revision faltantes o sensibles en ProcesoRentaAnual,
  DDJJ y F22 avanzados, manteniendo el reporte anual como evidencia interna
  revisable, no como presentacion tributaria final.
- `audit_stage7_reporting_readiness` clasifica explicitamente como bloqueantes
  DDJJ/F22 heredados asociados a un proceso anual de otra empresa o ano
  tributario.
- Los eventos `sii.ddjj_preparacion.status_updated` y
  `sii.f22_preparacion.status_updated` que sustentan reporting tributario anual
  deben conservar metadata minima de transicion con `campo_estado`,
  `estado_anterior` y `estado_nuevo`; readiness bloquea snapshots heredados
  sin esa auditoria trazable.
- La API de resumen tributario anual tambien bloquea esos eventos
  `status_updated` incompletos cuando pertenecen a DDJJ/F22 incluidos en la
  respuesta solicitada, sin exponer metadata cruda ni ids fuera del alcance.
- Los eventos `status_updated` de DDJJ/F22 incluidos en reporting tambien deben
  conservar `responsable_revision_ref` no sensible cuando el estado nuevo es
  aprobado, observado, rectificado o presentado. La API anual bloquea eventos
  en alcance sin responsable auditado o con referencia sensible usando codigos
  `reporting.annual_status_responsible_ref_missing` y
  `reporting.annual_status_responsible_ref_sensitive`, y readiness los alinea
  con `stage7.reporting.audit_annual_status_responsible_ref_*`.
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
  cuadrado, movimientos bancarios no resueltos, obligaciones mensuales, F29
  cuando aplica y bloqueadores del periodo sin llamar bancos ni SII.
- Los endpoints de Reporting normalizan parametros de consulta antes de
  filtrar, validar o decidir cache: `periodo`, `mode`, `refresh`, `status`,
  `empresa_id`, `anio`, `mes` y `anio_tributario`. Esto evita que espacios
  crudos conviertan reportes existentes en faltantes, impidan un refresh
  solicitado o filtren estados de resoluciones manuales con valores no
  canonicos.
- `audit_stage7_reporting_readiness` solo puede cerrar con `--source-kind`
  `snapshot_controlado` o `real_autorizado`; `local`, `fixture` y `demo`
  diagnostican brechas pero no habilitan cierre de Reporting.
- Una fuente autorizada debe declarar `--source-label` y `--authorization-ref`
  no sensibles. El guard `run-stage7-readiness-gate.ps1` reenvia
  `ReportingSourceLabel` y `ReportingAuthorizationRef` al auditor y mantiene el
  diagnostico local como no cerrable.
- Si `ReportingSourceLabel` o `ReportingAuthorizationRef` contienen URL,
  token, credencial o valor sensible, readiness debe clasificar
  `stage7.reporting.source_label_sensitive` o
  `stage7.reporting.authorization_ref_sensitive`, exponer solo
  `sections.source_trace_sensitive` y no mezclarlo con refs faltantes.
- Las referencias finales de Reporting (`Stage5EvidenceRef`,
  `Stage6EvidenceRef`, `ReportingApiProofRef`, `BackofficeVisualRef` y
  `ResponsibleRef`) tambien deben ser no sensibles. Si contienen URL, token,
  credencial o valor sensible, readiness debe clasificar
  `stage7.reporting.*_ref_sensitive`, exponer
  `sections.final_evidence_sensitive` y no mezclarlas con refs faltantes.
- El guard `run-stage7-readiness-gate.ps1` rechaza evidencia JSON de restore,
  smoke publico o aceptacion final que conserve payload sensible o claves de
  credenciales, aunque las referencias esperadas y el `source_kind` parezcan
  autorizados.

## Salida

Reporting sigue sin cierre final mientras falte evidencia con cierres completos,
snapshot controlado o datos reales autorizados. El gate local evita reportes sin
origen verificable, pero no reemplaza la evidencia externa/controlada ni la
revision responsable requerida por etapas contables o tributarias.
