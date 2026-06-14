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

```powershell
scripts\run-stage6-readiness-gate.ps1 -PythonExe backend\.venv\Scripts\python.exe
```

## Salida

El dossier anual no queda aprobable si existen meses sin cierre validado,
reglas fiscales sin respaldo o responsable de revision ausente. La renta anual
final no se declara presentada por el core v1; `SII.PresentacionAnualFinal`
sigue podada salvo reemision formal del set activo.
