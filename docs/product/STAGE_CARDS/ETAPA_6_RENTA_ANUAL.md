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

## Gate

- Cierres mensuales completos.
- Reglas tributarias validadas.
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
final no se declara presentada por el core v1; `SII.PresentacionAnualFinal`
sigue podada salvo reemision formal del set activo.
