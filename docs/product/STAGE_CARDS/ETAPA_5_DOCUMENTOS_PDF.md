# Etapa 5 - Documentos PDF y firma

## Objetivo

Preparar el flujo documental canonico en PDF, con origen, plantilla, checksum,
firma y notaria trazables.

## Alcance

- Expediente documental por entidad operativa.
- Documento emitido como PDF canonico.
- Politica de firma y notaria por tipo documental.
- Formalizacion con firmas requeridas y comprobante notarial cuando aplique.

## Gate

- `storage_ref` debe referenciar PDF canonico con una referencia no sensible:
  no URL, token, credencial, correo ni secreto.
- Documento emitido debe conservar `version_plantilla`, `checksum`, `usuario`,
  `fecha_carga`, `origen` y expediente; `checksum` debe ser un digest
  SHA-256 canonico, no una etiqueta libre. `DocumentoEmitido.clean()` bloquea
  nuevas escrituras sin `usuario` responsable y readiness conserva la deteccion
  de documentos heredados sin responsable.
- La emision de PDF generado por sistema debe usar el endpoint dedicado
  `documentos-emitidos/generar-pdf/`: genera bytes PDF canonicos locales,
  deriva `checksum` y `storage_ref` desde el contenido, rechaza contenido
  sensible, registra auditoria `documentos.documento_emitido.generated_pdf` y
  deja cerrado el endpoint generico para `origen=generado_sistema`.
- Antes de emitir un PDF generado por sistema, el mismo contenido debe haber
  pasado por `documentos-emitidos/previsualizar-pdf/`, que deriva el mismo
  checksum/storage esperado y registra auditoria
  `documentos.documento_emitido.previewed_pdf` sin persistir documento. La
  emision generada queda bloqueada si no existe preview auditada del mismo
  expediente, tipo documental, version de plantilla, checksum y storage_ref.
- Cada documento emitido debe tener politica activa para su tipo documental;
  el dominio/API rechaza nuevas escrituras sin esa politica y evita desactivar
  politicas ya usadas por documentos existentes.
- APIs y snapshot documental deben redactar `storage_ref` sensible heredado
  antes de exponer documentos al backoffice.
- Formalizacion requiere politica activa por tipo documental y debe ejecutarse
  desde el endpoint dedicado `formalizar/`, no desde create/update generico,
  para conservar la auditoria especifica del acto de formalizacion.
- Si la politica exige firma de codeudor, la formalizacion debe verificar si el
  expediente corresponde a un contrato con `CodeudorSolidario` activo. En ese
  caso la firma del codeudor es obligatoria; contratos sin codeudor activo no
  quedan bloqueados solo por el flag de politica.
- Toda formalizacion debe conservar `evidencia_formalizacion_ref` no sensible.
  El dominio/API rechaza referencias faltantes o sensibles, snapshot/backoffice
  redactan valores heredados sensibles y readiness bloquea documentos
  formalizados sin esa evidencia.
- Solo documentos en estado `emitido` pueden entrar al endpoint `formalizar/`;
  los borradores deben emitirse antes de cualquier acto de firma/notaria.
- Un documento ya formalizado queda inmutable frente al endpoint generico y no
  puede re-formalizarse; correcciones posteriores requieren nueva version o un
  flujo auditado dedicado.
- Las versiones correctivas deben apuntar al documento formalizado de origen,
  pertenecer al mismo expediente y tipo documental, tener PDF/checksum propios
  y conservar `correccion_ref` no sensible con evento de auditoria dedicado.
- Auditoria local `audit_document_readiness` debe bloquear cierre si detecta
  documentos formalizados sin evento `documentos.documento_emitido.formalized`.
- Ese evento de formalizacion debe conservar actor y metadata alineada con la
  evidencia, firmas, recepcion y comprobante notarial del documento. Readiness
  debe reportar `documents.formalization_audit_unaligned` para snapshots
  heredados con auditoria incompleta o desalineada.
- Auditoria local `audit_document_readiness` debe bloquear versiones
  correctivas heredadas invalidas o sin evento
  `documentos.documento_emitido.corrective_version_created`.
- Ese evento de version correctiva debe conservar actor y metadata alineada con
  documento origen, expediente, tipo, version de plantilla, checksum,
  `storage_ref` y `correccion_ref`. Readiness debe reportar
  `documents.corrective_version_audit_unaligned` para auditorias incompletas o
  desalineadas.
- Si la politica exige notaria, el comprobante notarial debe pertenecer al
  mismo expediente y estar emitido, formalizado o archivado.
- La readiness documental debe distinguir documentos formalizados con politica
  notarial sin recepcion registrada, sin comprobante, con comprobante de tipo
  incorrecto, de otro expediente o en estado no permitido.
- La readiness documental debe reportar `documents.codebtor_signature_missing`
  cuando encuentre documentos formalizados de contratos con codeudor activo y
  politica que exige codeudor, pero sin firma de codeudor registrada.
- Auditoria local `audit_document_readiness` debe consolidar politicas activas
  por tipo documental, metadata PDF, evidencia controlada, responsables y
  faltantes antes de declarar cierre.
- Auditoria local `audit_document_readiness` debe bloquear cierre si detecta
  documentos emitidos sin `usuario` responsable registrado.
- Auditoria local `audit_document_readiness` debe bloquear cierre si detecta
  documentos `generado_sistema` sin auditoria dedicada de generacion PDF.
- Auditoria local `audit_document_readiness` debe bloquear cierre si detecta
  documentos `generado_sistema` sin preview PDF auditada del mismo contenido.
- Auditoria local `audit_document_readiness` debe bloquear cierre si detecta
  documentos heredados sin politica activa para su tipo documental.
- Auditoria local `audit_document_readiness` debe bloquear cierre si detecta
  checksums heredados no canonicos, sin exponer el valor.
- Auditoria local `audit_document_readiness` debe bloquear cierre si detecta
  `storage_ref` sensible heredado, sin exponer el valor.
- `audit_document_readiness` solo puede cerrar con `--source-kind`
  `snapshot_controlado` o `real_autorizado`; `local`, `fixture` y `demo`
  diagnostican brechas pero no habilitan cierre documental.
- Las fuentes autorizadas deben declarar `SourceLabel` y `AuthorizationRef` no
  sensibles.
- `scripts/run-stage5-documents-readiness-gate.ps1` normaliza la ejecucion del
  gate. En modo local crea SQLite bajo `local-evidence/`, corre migraciones y
  debe quedar `classification=parcial`, `ready_for_stage5_documents=false` y
  issue `documents.source_kind_not_authorized`.
- El comando `audit_document_readiness` rechaza `--output` dentro del repo
  fuera de `local-evidence/` antes de recolectar readiness, para no versionar
  evidencia ni metadatos documentales.
- Para cierre con fuente autorizada, el wrapper exige `-SourceKind
  snapshot_controlado` o `real_autorizado`, `-SourceLabel`,
  `-AuthorizationRef`, `-FinalPolicyRef`, `-ControlledPdfRef`,
  `-ResponsibleRef` y `-RequireReady`.

## Salida

Documentos no cierra sin politica final de firma/notaria, responsables y prueba
PDF controlada. La preparacion local puede avanzar sin usar storage real ni
documentos productivos.

## Ejecucion local segura

```powershell
cd "D:/Proyectos/LeaseManager"
.\scripts\run-stage5-documents-readiness-gate.ps1
```
