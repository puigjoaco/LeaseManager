# ADR 005 - Estrategia documental y PDF canonico

Estado: aprobado  
Fecha: 15/03/2026  
PRD relacionado: [PRD_CANONICO.md](./PRD_CANONICO.md)

## Contexto

El maestro anterior fijaba `DOCX -> PDF` y `python-docx-template`, pero sin resolver bien versionado, determinismo de salida, firma, comparabilidad entre versiones y soporte de evidencia.

## Decision

LeaseManager adopta `PDF` como formato canonico emitido y firmado.

Decisiones aprobadas:

1. Las plantillas canonicas se mantienen como templates versionados en texto estructurado para generar PDF.
2. El artefacto documental canonico emitido, almacenado y firmado es `PDF`.
3. Todo documento emitido guarda:
   - `version_plantilla`
   - `checksum`
   - `storage_ref`
   - `usuario`
   - `fecha`
4. La generacion editable en `DOCX` no forma parte del flujo canonico del v1.
5. Si un caso juridico exige documento externo editable, se trata como excepcion controlada y se archiva dentro del expediente.

## Forma de implementacion

Requisitos del motor documental:

- render deterministico;
- versionado de plantilla;
- soporte de preview;
- trazabilidad entre borrador y emitido;
- exportacion a PDF estable para firma y archivo.

## Consecuencias

- mejora la auditabilidad documental;
- se simplifica firma, almacenamiento y comparacion de versiones;
- se evita volver canonico un pipeline `DOCX-first` mas fragil.

## Alternativas descartadas

- `DOCX` como fuente canonica: descartado por fragilidad y menor control de versionado.
- subir solo PDFs manuales sin plantilla canonica: descartado por baja trazabilidad.

