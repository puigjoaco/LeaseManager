# Etapa 6 - Dossier de renta anual

## Objetivo

Preparar y generar la renta anual, DDJJ, F22, certificados y trazabilidad desde
cierres mensuales. LeaseManager organiza datos, reglas, bloqueos y evidencia, y
puede actuar como software tributario deterministico si el formato/canal SII del
Ano Tributario esta versionado y certificado. La decision tributaria final
requiere regla verificable, responsable trazado, gate aplicable y aprobacion.

## Alcance

- Proceso de renta anual como expediente revisable.
- Motor tributario anual versionado por Ano Tributario.
- Certificados.
- Declaraciones juradas.
- F22, archivo/export compatible y respaldos.
- Validaciones tributarias.
- Certificacion o canal SII/casa de software cuando exista presentacion
  automatizable.
- Checklist de revision experta/oficial.

## Gate

- Cierres mensuales completos.
- Reglas tributarias validadas.
- Cada campo/codigo F22 automatizado debe estar mapeado a dato, cierre,
  obligacion, DDJJ, certificado o regla versionada del Ano Tributario vigente.
  Lo no mapeado o ambiguo queda como bloqueo de revision, no como calculo
  inferido.
- Responsable de revision anual trazado antes de tratar el paquete como
  aprobado.
- Presentacion final automatizada solo si existe canal SII, certificacion de
  software, formato de archivo o API habilitada para el Ano Tributario, con
  aprobacion responsable y evidencia no sensible de envio/recepcion. Sin ese
  gate, LeaseManager entrega dossier y archivo preparatorio para carga manual.
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
  cierre; solo declara presentacion anual final si existe source autorizada,
  gate/canal SII certificado y evidencia de responsable. No sustituye criterio
  tributario en casos interpretativos.
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

```powershell
scripts\run-stage6-readiness-gate.ps1 -PythonExe backend\.venv\Scripts\python.exe
```

## Salida

El dossier anual no queda aprobable si existen meses sin cierre validado,
reglas fiscales sin respaldo o responsable de revision ausente. La renta anual
final no se declara presentada por el core si falta gate SII/certificacion,
canal autorizado, regla versionada o responsable. `SII.PresentacionAnualFinal`
solo se habilita mediante reemision formal del set activo o capacidad
equivalente certificada.
