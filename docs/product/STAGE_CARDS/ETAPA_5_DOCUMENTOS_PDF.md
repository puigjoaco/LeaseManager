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
- Formalizacion requiere politica activa por tipo documental.
- Si la politica exige notaria, el comprobante notarial debe pertenecer al
  mismo expediente y estar emitido, formalizado o archivado.
- Auditoria local `audit_document_readiness` debe consolidar politicas activas
  por tipo documental, metadata PDF, evidencia controlada, responsables y
  faltantes antes de declarar cierre.

## Salida

Documentos no cierra sin politica final de firma/notaria, responsables y prueba
PDF controlada. La preparacion local puede avanzar sin usar storage real ni
documentos productivos.
