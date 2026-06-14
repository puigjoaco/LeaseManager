# Etapa 6 - Dossier de renta anual

## Objetivo

Preparar el dossier anual de renta, DDJJ, F22, certificados y trazabilidad
desde cierres mensuales. LeaseManager organiza datos, reglas, bloqueos y
evidencia; la decision tributaria final requiere revision experta/oficial,
responsable trazado y gate aplicable.

## Alcance

- Proceso de renta anual como expediente revisable.
- Certificados.
- Declaraciones juradas.
- F22 y respaldos.
- Validaciones tributarias.
- Checklist de revision experta/oficial.

## Referencia EDIG AT2026

`docs/product/RENTA_ANUAL_EDIG_AT2026_MAPPING.md` registra la investigacion
local del software EDIG AT2026 como referencia funcional no normativa. El
aprendizaje aceptado para LeaseManager es que renta anual se automatiza mediante
una capa tributaria intermedia: cierres, ledger, F29/PPM, patrimonio, socios,
arriendos, contribuciones y certificados se transforman primero en RLI, CPT,
RAI, SAC, DDJJ y respaldos; recien despues se mapean a F22/export.

EDIG no autoriza reglas fiscales propias, formatos SII finales ni presentacion
automatica. Cualquier ejecucion de EDIG solo puede ocurrir en la VM/sandbox
descrita en `docs/operations/EDIG_AT2026_SANDBOX_RUNBOOK.md`, con datos
ficticios, red controlada y sin credenciales reales.

El inventario estatico read-only de `scripts/analyze-edig-at2026.ps1` clasifica
senales funcionales por administracion, F22, F29/PPM, regimenes 14A/14D3/14D8/
14G, RLI, CPT, RAI, SAC, DDJJ, balance, bienes raices/arriendos,
reportes/respaldo, upload/export y conectividad auxiliar. Las raices de datos
de usuario/licencia/salida quedan excluidas o redactadas; la salida se mantiene
en `local-evidence/` y no se versiona.

`scripts/extract-edig-mdb-schema.ps1` puede extraer metadata de tablas/columnas
de los MDB nucleo desde copias temporales, sin ejecutar EDIG ni leer filas. La
extraccion local confirma bases separadas para maestros, F29/PPM, parametria de
regimen, PRO/F22 y registros RLI/CPT/RAI/SAC. Esa evidencia orienta el motor
anual propio, pero no habilita copiar schema EDIG ni declarar reglas fiscales.

`scripts/build-edig-at2026-leasemanager-coverage.ps1` cruza los inventarios
sanitizados de `local-evidence/` contra componentes propios observables en el
repo. La matriz local confirma que LeaseManager ya cubre la columna vertebral
funcional observada en EDIG: configuracion, F29/PPM, parametria AT, RLI/CPT,
RAI/SAC, bienes raices, matriz DDJJ/F22, dossier y export local. Las brechas
restantes son de fuente oficial/experta, saldos historicos, contribuciones,
formatos/certificacion SII y autorizacion de presentacion; no son razon para
copiar mas EDIG ni abrir una integracion externa.

`docs/product/RENTA_ANUAL_AT2026_ENGINE_BLUEPRINT.md` traduce esa evidencia a
componentes propios de LeaseManager: source bundle anual, rule set por AT,
normalizador, workbooks RLI/CPT, registros RAI/SAC, seccion bienes raices,
paquetes DDJJ, draft F22, dossier y export gate.
`TaxYearRuleSet` y `TaxCodeMapping` materializan la primera parte de esa capa
propia: reglas versionadas por ano tributario/regimen y mapeos trazables hacia
RLI/CPT/RAI/SAC/DDJJ/F22/Dossier, sin copiar reglas EDIG ni declarar formulas
fiscales finales.
`AnnualTaxSourceBundle` materializa la siguiente capa: congela fuentes anuales
no sensibles desde cierres mensuales, obligaciones PPM/F29 y configuracion
fiscal, conserva hash SHA-256 del payload anual normalizado y se enlaza al
`ProcesoRentaAnual` para que DDJJ/F22 partan desde un dossier revisable, no
desde inferencia libre ni automatizacion tributaria autonoma.
`MonthlyTaxFact` materializa la capa mensual anualizable: por cada empresa,
ano comercial y mes normaliza el cierre aprobado, obligaciones mensuales,
F29 si existe, distribuciones de arriendo y liquidacion de empresa, con
`hash_hecho` del resumen mensual, refs no sensibles y exposicion redactada en
API/snapshot/admin. Esto mantiene la union contabilidad -> renta como
transformacion trazable, no como salto directo desde asientos a F22.
`AnnualTaxWorkbook` y `AnnualTaxWorkbookLine` materializan el primer esqueleto
RLI/CPT: para cada `ProcesoRentaAnual` se preparan workbooks RLI y CPT desde
`TaxCodeMapping` aprobado y `MonthlyTaxFact`, con hashes por linea/workbook,
warnings revisables y exposicion redactada. Esta capa no declara calculo
tributario final; deja importes, origenes y advertencias listos para revision
antes de avanzar a RAI/SAC/DDJJ/F22.
`AnnualEnterpriseRegisterSet` y `AnnualEnterpriseRegisterMovement` materializan
la siguiente capa: registros RAI, SAC, retiros y dividendos por proceso anual,
con saldos iniciales/finales, movimientos trazados a RLI/CPT o participaciones
activas, hashes por movimiento/registro y exposicion redactada. Esta capa
mantiene `final_tax_calculation=false`; no reemplaza revision tributaria ni
presentacion SII.
`AnnualRealEstateSection` y `AnnualRealEstateItem` materializan la seccion
anual de bienes raices/arriendos: preparan items por propiedad desde
`Propiedad`, `DistribucionCobroMensual` y `ContratoPropiedad`, distribuyen
arriendos por porcentaje interno, congelan snapshots anuales con hash y dejan
contribuciones como fuente `not_loaded_v1` hasta contar con respaldo oficial o
experto. Esta capa alimenta el dossier y la matriz DDJJ/F22, pero no
declara calculo fiscal final ni presentacion SII.
`AnnualTaxArtifactMatrix` y `AnnualTaxArtifactMatrixItem` materializan la
matriz anual DDJJ/F22: conectan configuracion fiscal, mapeos tributarios,
source bundle, resumen anual, RLI/CPT, registros empresariales y bienes
raices con destinos DDJJ/F22 revisables. Cada item conserva fuente, medio SII,
responsable, payload no sensible, hash, estado de revision y
`final_tax_calculation=false`; no declara formato final SII ni presentacion
autonoma.
`AnnualTaxDossier` materializa el paquete anual revisable: consolida source
bundle, hechos mensuales, RLI/CPT, registros empresariales, bienes raices y
matriz DDJJ/F22 en un resumen hasheado con responsable y referencias no
sensibles. El dossier conserva `final_tax_calculation=false` y
`sii_submission=false`; sirve para revision experta/oficial antes de cualquier
export o presentacion, no para que LeaseManager decida la renta final.
`AnnualTaxExport` materializa el preview/export local controlado: empaqueta el
dossier y la matriz DDJJ/F22 en un payload hasheado, con refs no sensibles,
responsable, conteos DDJJ/F22 y flags obligatorios `official_format=false`,
`sii_submission=false` y `final_tax_calculation=false`. Es una salida revisable
del motor anual, no un formato oficial SII ni una presentacion.
`RENTA_ANUAL_OFFICIAL_SOURCE_GAPS_AT2026.md` fija la matriz de brechas
oficiales: DTE queda como integracion tecnica separada bajo gate; F29, DDJJ,
DJ1847/RLI/CPT, F22, bienes raices/contribuciones y automatizacion por
navegador quedan limitados a preparacion revisable hasta fuente SII/experta,
formato/certificacion, responsable y autorizacion explicita. La prioridad
posterior al mapeo EDIG es bajar fuentes SII AT2026 a reglas versionadas,
partiendo por balance de 8 columnas/DJ1847, RLI/CPT, DDJJ por formulario,
contribuciones y formato/certificacion F22; no seguir copiando ni ejecutando
EDIG.
`AnnualTaxOfficialSource` materializa ese registro de fuentes oficiales o
expertas: conserva ano tributario, tipo, URL publica SII segura cuando aplica,
referencia no sensible, hash SHA-256, fecha de recuperacion, responsable,
alcance y destino RLI/CPT/RAI/SAC/DDJJ/F22/Dossier. API, snapshot y admin
redactan refs, notas y metadata sensibles; readiness bloquea fuentes invalidas
sin exponer valores.

## Gate

- Cierres mensuales completos.
- Reglas tributarias validadas.
- `TaxYearRuleSet` aprobado para el ano tributario y regimen fiscal de la
  empresa, con `hash_normativo`, fuente y responsable no sensibles.
- `TaxCodeMapping` activo y trazable para el rule set antes de preparar
  ProcesoRentaAnual/DDJJ/F22.
- `AnnualTaxSourceBundle` congelado por empresa/ano tributario antes de
  preparar ProcesoRentaAnual/DDJJ/F22; debe tener doce cierres aprobados,
  obligaciones mensuales trazables, refs no sensibles y `hash_fuentes`
  coherente con `resumen_fuentes`.
- `MonthlyTaxFact` normalizado por empresa/ano/mes antes de tratar un proceso
  anual como trazable. Deben existir doce meses normalizados para el ano
  comercial y `ProcesoRentaAnual.resumen_anual.annual_tax_monthly_facts` debe
  coincidir con esos hechos.
- `AnnualTaxWorkbook` preparado para RLI y CPT antes de tratar un proceso anual
  como trazable. Ambos workbooks deben pertenecer al mismo proceso, rule set,
  bundle y empresa, conservar `hash_workbook` coherente y aparecer en
  `ProcesoRentaAnual.resumen_anual.annual_tax_workbooks`.
- `AnnualTaxWorkbookLine` activa requiere `TaxCodeMapping` del mismo rule set,
  origen, monto, `formula_ref`, `evidencia_ref`, `source_payload` y
  `hash_linea` coherente. Lineas con warnings bloquean readiness hasta revision
  tributaria; no se transforman en cierre automatico.
- `AnnualEnterpriseRegisterSet` preparado requiere proceso anual, bundle y rule
  set coherentes, saldos iniciales/finales trazables, `resumen_registro` y
  `hash_registro` coherentes. Para tratar un proceso anual como trazable deben
  existir registros RAI, SAC, retiros y dividendos.
- `AnnualEnterpriseRegisterMovement` activo requiere origen, monto, signo,
  `formula_ref`, `evidencia_ref`, `source_payload` y `hash_movimiento`
  coherente. Movimientos con warnings bloquean readiness hasta revision
  tributaria; retiros/dividendos pueden conservar movimientos cero trazados a
  participaciones activas mientras no existan eventos propios.
- `AnnualRealEstateSection` preparada requiere proceso anual, bundle y rule
  set coherentes, `resumen_seccion` y `hash_seccion` coherentes. Para tratar un
  proceso anual como trazable debe existir una seccion preparada y su resumen
  debe coincidir con `ProcesoRentaAnual.resumen_anual.annual_real_estate_sections`.
- `AnnualRealEstateItem` activo requiere snapshot anual completo de propiedad,
  montos no negativos, `formula_ref`, `evidencia_ref`, `source_payload` y
  `hash_item` coherente. El snapshot anual queda congelado: cambios posteriores
  en la ficha maestra de la propiedad no invalidan evidencia ya preparada,
  siempre que el hash del item se mantenga vigente.
- `AnnualTaxArtifactMatrix` preparada requiere proceso anual, bundle, rule set,
  configuracion fiscal activa, refs no sensibles, conteos DDJJ/F22, resumen e
  `hash_matriz` coherentes. Para tratar un proceso anual como trazable debe
  existir una matriz preparada y su resumen debe coincidir con
  `ProcesoRentaAnual.resumen_anual.annual_tax_artifact_matrices`.
- `AnnualTaxArtifactMatrixItem` activo requiere destino DDJJ/F22, codigo,
  medio SII, fuente, modelo origen, `formula_ref`, `evidencia_ref`,
  `responsible_ref`, `source_payload` y `hash_item` coherente. Items con
  warnings o estado `bloqueado` bloquean readiness hasta revision tributaria.
- `AnnualTaxDossier` preparado requiere proceso anual, source bundle, rule set,
  matriz DDJJ/F22 y configuracion fiscal activa coherentes; refs no sensibles,
  responsable, `dossier_ref`, conteos anuales, `resumen_dossier` y
  `hash_dossier` alineados. Para tratar un proceso anual como trazable debe
  existir un dossier preparado y su resumen debe coincidir con
  `ProcesoRentaAnual.resumen_anual.annual_tax_dossiers`.
- Un dossier con warnings o estado `requiere_revision` puede alimentar un
  export local de revision, pero bloquea readiness hasta revision tributaria
  responsable; un dossier `bloqueado` no se convierte en export ni presentacion
  SII por conveniencia.
- `AnnualTaxExport` preparado requiere proceso anual, source bundle, rule set,
  matriz DDJJ/F22 y dossier coherentes; refs no sensibles, responsable,
  `export_ref`, payload exportable, `hash_export`, conteos DDJJ/F22 y resumen
  en `ProcesoRentaAnual.resumen_anual.annual_tax_exports` alineados.
- `AnnualTaxExport` bloquea readiness si falta, si esta desalineado, si contiene
  refs/payloads sensibles, si hay revision pendiente o si intenta declarar
  formato oficial SII, presentacion SII o calculo fiscal final autonomo.
- La matriz `stage6-official-source-gaps` debe mantenerse alineada con fuentes
  SII vigentes antes de promover cualquier warning de regla, medio DDJJ,
  mapping DJ1847/RLI/CPT, contribucion o formato F22 a estado cerrable.
- `AnnualTaxOfficialSource` revisada/aprobada requiere `source_url` publica SII
  segura si la fuente es SII, `source_ref`, `source_hash`, `retrieved_on` y
  `responsible_ref` no sensibles. Fuentes invalidas o con URLs/refs/payloads
  sensibles bloquean readiness.
- Una certificacion tecnica F22, F29 o DDJJ acredita formato/recepcion en el
  alcance descrito por SII; no reemplaza validacion tributaria del contenido ni
  revision responsable.
- `generate_annual_preparation()` sincroniza bienes raices/arriendos despues
  de RLI/CPT y registros empresariales, antes de emitir DDJJ/F22 locales. La
  readiness bloquea procesos trazables sin seccion inmobiliaria, sin items
  activos, con resumen desalineado, invalidos o con warnings pendientes.
- `generate_annual_preparation()` sincroniza la matriz DDJJ/F22 despues de
  RLI/CPT, registros empresariales y bienes raices, antes de emitir DDJJ/F22
  locales. La readiness bloquea procesos trazables sin matriz, sin items DDJJ
  o F22, con resumen desalineado, invalidos, con warnings pendientes o items
  bloqueados.
- `generate_annual_preparation()` sincroniza `AnnualTaxDossier` despues de la
  matriz DDJJ/F22 y antes de emitir DDJJ/F22 locales. La readiness bloquea
  procesos trazables sin dossier, con resumen desalineado, refs faltantes,
  invalidos o con revision pendiente.
- `generate_annual_preparation()` sincroniza `AnnualTaxExport` despues de crear
  DDJJ/F22 locales. La readiness bloquea procesos trazables sin export/preview
  controlado, con resumen desalineado, invalidos, refs faltantes o cualquier
  intento de presentacion/formato oficial/calculo final.
- Responsable de revision anual trazado antes de tratar el paquete como
  aprobado.
- Documentos generados desde datos trazables.
- Evidencia sin datos sensibles expuestos.
- Capacidades DDJJ/F22, ProcesoRentaAnual, DDJJ y F22 pertenecen a empresas
  con `ConfiguracionFiscalEmpresa` activa propia; el dominio/API rechaza
  nuevas escrituras que no cumplan esa regla.
- `audit_stage6_renta_anual_readiness` consolida configuracion fiscal,
  capacidades DDJJ/F22, doce cierres, obligaciones mensuales, proceso anual,
  respaldos tributarios PDF y referencias finales no sensibles sin conectar SII
  ni leer certificados reales.
- El readiness de Etapa 6 puede declarar preparacion local, brecha o bloqueo de
  cierre; no declara presentacion anual final ni sustituye criterio tributario.
- `ProcesoRentaAnual.resumen_anual`, `DDJJPreparacionAnual.resumen_paquete`
  y `F22PreparacionAnual.resumen_f22` deben trazar al ano comercial
  inmediatamente anterior al `anio_tributario`; el dominio rechaza nuevas
  escrituras desalineadas y readiness bloquea snapshots heredados.
- El dominio SII rechaza F29, ProcesoRentaAnual, DDJJ y F22 en estados
  aprobados, presentados, observados o rectificados si falta la referencia
  final trazable correspondiente.
- El dominio SII rechaza ProcesoRentaAnual, DDJJ y F22 en estados aprobados,
  presentados, observados o rectificados si falta `responsable_revision_ref` no
  sensible. El responsable de revision queda separado de la referencia externa
  del paquete para reforzar que LeaseManager prepara dossiers revisables, no
  decide ni presenta renta final de forma autonoma.
- Las APIs que generan ProcesoRentaAnual/DDJJ/F22 o actualizan estados DDJJ/F22
  persisten la mutacion y su auditoria de vista en una misma transaccion. Si
  falla la auditoria, no debe quedar proceso anual, preparacion ni referencia
  final mutada sin traza de endpoint.
- Los eventos `sii.ddjj_preparacion.status_updated` y
  `sii.f22_preparacion.status_updated` deben conservar metadata minima de
  transicion con `campo_estado`, `estado_anterior` y `estado_nuevo`;
  `audit_stage6_renta_anual_readiness` bloquea snapshots heredados sin esa
  metadata.
- Esos mismos eventos, cuando avanzan DDJJ/F22 a estados aprobados, observados
  o rectificados, deben conservar `responsable_revision_ref` no sensible en la
  metadata auditada. `audit_stage6_renta_anual_readiness` bloquea eventos
  heredados sin responsable auditado o con referencia sensible usando codigos
  `stage6.audit.annual_status_responsible_ref_missing` y
  `stage6.audit.annual_status_responsible_ref_sensitive`, sin exponer valores.
- El backoffice SII solo permite actualizar revision anual DDJJ/F22 mediante
  formulario explicito con artefacto, estado, referencia, observacion no
  sensible y `responsable_revision_ref`; no debe existir accion rapida que
  avance estados anuales sin responsable revisable.
- `audit_stage6_renta_anual_readiness` clasifica explicitamente como
  bloqueantes las referencias finales sensibles en ProcesoRentaAnual, DDJJ y
  F22, sin exponer esos valores.
- `audit_stage6_renta_anual_readiness` clasifica explicitamente como
  bloqueantes ProcesoRentaAnual, DDJJ o F22 avanzados sin
  `responsable_revision_ref`, o con una referencia sensible, usando codigos
  `stage6.*_responsible_ref_missing` y
  `stage6.*_responsible_ref_sensitive`.
- El dominio SII tambien rechaza ProcesoRentaAnual, DDJJ y F22 asociados a
  empresas sin `ConfiguracionFiscalEmpresa` activa propia.
- Los payloads anuales y referencias de DDJJ/F22 heredadas se entregan a
  reporting con redaccion antes de exponerse al backoffice.
- El admin Django de SII expone ProcesoRentaAnual, DDJJ y F22 solo con
  versiones redactadas de refs finales, payloads anuales y observaciones
  heredadas, sin busquedas por los campos crudos ni alta manual desde
  backoffice.
- `audit_stage6_renta_anual_readiness` clasifica como bloqueantes los payloads
  anuales heredados con URLs, tokens, credenciales, correos o claves sensibles
  en `resumen_anual`, `resumen_paquete` o `resumen_f22`, sin imprimir esos
  valores.
- `audit_stage6_renta_anual_readiness` solo puede cerrar con `--source-kind`
  `snapshot_controlado` o `real_autorizado`; `local`, `fixture` y `demo`
  diagnostican brechas pero no habilitan cierre de Etapa 6.
- Una fuente evidencial debe incluir `--source-label` y
  `--authorization-ref` no sensibles. Sin esas refs, el tipo de fuente queda
  reconocido pero no puede cerrar Etapa 6.
- Si `--source-label` o `--authorization-ref` contienen URL, token, credencial
  o valor sensible, readiness debe clasificar `stage6.source_label_sensitive`
  o `stage6.authorization_ref_sensitive`, exponer solo
  `sections.source_trace_sensitive` y no mezclarlo con refs faltantes.
- Las referencias finales de cierre (`Stage5EvidenceRef`,
  `Stage4SiiEvidenceRef`, `FiscalRuleRef`, `CertificatesProofRef` y
  `ResponsibleRef`) tambien deben ser no sensibles. Si contienen URL, token,
  credencial o valor sensible, readiness debe clasificar
  `stage6.*_ref_sensitive`, exponer `sections.final_evidence_sensitive` y no
  mezclarlas con refs faltantes.
- `scripts/run-stage6-readiness-gate.ps1` ejecuta el diagnostico local con
  SQLite efimero bajo `local-evidence/`, no conecta SII, no lee `.env`, no usa
  certificados y reserva `-RequireReady` para fuentes autorizadas con refs
  trazables de Etapa 5, Etapa 4 SII, regla fiscal, certificados y responsable.
- El mapeo anual automatizable debe declarar explicitamente su fuente: dato
  LeaseManager, cierre, ledger, F29/PPM, certificado, regla AT, DDJJ o decision
  responsable. Ningun codigo F22/DDJJ queda automatizado solo por inferencia de
  EDIG o por coincidencia visual de plantilla.
- `generate_annual_preparation()` rechaza preparar ProcesoRentaAnual/DDJJ/F22
  si falta `TaxYearRuleSet` aprobado o si sus `TaxCodeMapping` activos no pasan
  validacion de dominio. El resumen anual conserva solo metadata no sensible de
  la regla aplicada: AT, regimen, version, hash y conteos por destino.
- `generate_annual_preparation()` congela o reutiliza un
  `AnnualTaxSourceBundle` local antes de crear ProcesoRentaAnual/DDJJ/F22. El
  proceso anual conserva id/hash del bundle, y
  `audit_stage6_renta_anual_readiness` bloquea procesos heredados sin bundle,
  con bundle no congelado, desalineado o con metadata/hash distinta.
- `generate_annual_preparation()` sincroniza `MonthlyTaxFact` desde los cierres
  aprobados antes de construir el resumen anual. La readiness bloquea hechos
  mensuales invalidos, faltantes, sin configuracion fiscal activa o procesos
  cuyo resumen mensual quede desalineado.
- `generate_annual_preparation()` sincroniza workbooks RLI/CPT despues de crear
  el proceso anual y antes de emitir DDJJ/F22 locales. La readiness bloquea
  procesos trazables sin ambos workbooks, sin lineas activas, con warnings,
  invalidos o con resumen RLI/CPT desalineado.
- `generate_annual_preparation()` sincroniza registros empresariales despues de
  RLI/CPT y antes de emitir DDJJ/F22 locales. La readiness bloquea procesos
  trazables sin RAI/SAC/retiros/dividendos, sin movimientos activos, con
  warnings, invalidos o con resumen empresarial desalineado.
- La API/snapshot/admin de SII exponen `TaxYearRuleSet` y `TaxCodeMapping` con
  referencias/payloads redactados y auditoria de creacion/actualizacion; el
  bootstrap demo anual crea parametria demo controlada, no oficial, antes de
  generar artefactos anuales locales.
- La API/snapshot/admin de SII exponen `AnnualTaxSourceBundle` con refs y
  payloads redactados; el admin no busca referencias crudas potencialmente
  sensibles.
- La API/snapshot/admin de SII exponen `MonthlyTaxFact` con `source_ref`,
  `responsible_ref` y `resumen_hecho` redactados; el admin es solo lectura para
  evitar ediciones manuales de hechos derivados.
- La API/snapshot/admin de SII exponen `AnnualTaxWorkbook` y
  `AnnualTaxWorkbookLine` con refs, warnings y payloads redactados; el admin es
  solo lectura para preservar que RLI/CPT provienen del normalizador anual y no
  de edicion manual opaca.
- La API/snapshot/admin de SII exponen `AnnualEnterpriseRegisterSet` y
  `AnnualEnterpriseRegisterMovement` con refs, warnings y payloads redactados;
  el admin es solo lectura para preservar que RAI/SAC/retiros/dividendos
  provienen del motor anual y no de edicion manual opaca.
- La API/snapshot/admin de SII exponen `AnnualRealEstateSection` y
  `AnnualRealEstateItem` con refs, warnings y payloads redactados; el snapshot
  redacta rol/direccion de propiedad y el admin es solo lectura para preservar
  que bienes raices/arriendos provienen del normalizador anual y no de edicion
  manual opaca.
- La API/snapshot/admin de SII exponen `AnnualTaxArtifactMatrix` y
  `AnnualTaxArtifactMatrixItem` con refs, warnings y payloads redactados; el
  admin es solo lectura para preservar que la matriz DDJJ/F22 proviene del
  motor anual y no de edicion manual opaca.
- La API/snapshot/admin de SII exponen `AnnualTaxDossier` con source,
  responsable, dossier ref y payload anual redactados; el admin es solo lectura
  para preservar que el dossier proviene del motor anual y no de edicion manual
  opaca.
- La API/snapshot/admin de SII exponen `AnnualTaxExport` con source,
  responsable, export ref y payload anual redactados; el admin es solo lectura
  y no existe endpoint para presentar a SII desde esta capa.

```powershell
scripts\run-stage6-readiness-gate.ps1 -PythonExe backend\.venv\Scripts\python.exe
```

## Salida

El dossier y su export local no quedan aprobables si existen meses sin cierre
validado, reglas fiscales sin respaldo, responsable de revision ausente,
warnings pendientes o formato/certificacion SII no evidenciado. La renta anual
final no se declara presentada por el core v1; `SII.PresentacionAnualFinal`
sigue podada salvo reemision formal del set activo.
