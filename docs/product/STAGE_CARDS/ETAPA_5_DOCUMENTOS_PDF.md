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

- `storage_ref` debe referenciar PDF canonico.
- Documento emitido debe conservar `version_plantilla`, `checksum`, `usuario`,
  `fecha_carga`, `origen` y expediente.
- Formalizacion requiere politica activa por tipo documental y debe ejecutarse
  desde el endpoint dedicado `formalizar/`, no desde create/update generico,
  para conservar la auditoria especifica del acto de formalizacion.
- Si la politica exige notaria, el comprobante notarial debe pertenecer al
  mismo expediente y estar emitido, formalizado o archivado.
- Auditoria local `audit_document_readiness` debe consolidar politicas activas
  por tipo documental, metadata PDF, evidencia controlada, responsables y
  faltantes antes de declarar cierre.
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
