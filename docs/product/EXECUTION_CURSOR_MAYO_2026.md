# Cursor operativo - mayo 2026

Este archivo fija el frente activo de ejecucion. No reemplaza al PRD, AGENTS,
fuente de verdad, arquitectura, matriz, stage cards, evidencia ni bloqueos. Su
funcion es evitar que una reanudacion convierta contexto auxiliar en tarea
nueva.

## Regla de uso

- Antes de abrir o continuar cambios no triviales, leer este cursor.
- Confirmar el estado real con `git status --short --branch` y
  `git worktree list`.
- Si existe un worktree tactico sucio, se debe terminar, pausar de forma
  explicita en este cursor o descartar con instruccion segura antes de abrir un
  frente distinto.
- Solo el estado real del repo y este cursor definen la siguiente accion
  operativa.
- El contexto auxiliar no autoriza secretos, no abre gates y no crea tareas
  nuevas salvo solicitud textual actual del usuario.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | Etapa 5 - Documentos PDF: responsable obligatorio en documento emitido. |
| Fuente exacta | `docs/product/STAGE_CARDS/ETAPA_5_DOCUMENTOS_PDF.md`; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `Documentos`; `backend/documentos/models.py`; `backend/documentos/serializers.py`; `backend/documentos/readiness.py`; tests de Documentos/readiness. |
| Brecha activa | `audit_document_readiness` bloquea documentos emitidos sin `usuario`, pero `DocumentoEmitido.clean()` aun no impide nuevas escrituras sin responsable de carga. |
| Motivo de prioridad | Brecha local trazable de Documentos; alinea dominio con readiness y evita nuevos documentos sin responsable sin usar storage real, `.env`, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-document-user-domain-guard`. |
| Rama | `codex/stage5-document-user-domain-guard`. |
| Estado | En implementacion. `main` queda limpio en `D:/Proyectos/LeaseManager`. |
| Gate esperado | Etapa 5 Documentos local queda como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, politica final, prueba PDF controlada y responsable. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Politica final, prueba PDF controlada y fuente autorizada siguen siendo condicion de cierre, no freno para este hardening local. |
| Politica de reanudacion | Retomar este worktree hasta cerrar, pausar explicitamente en este cursor o limpiar con instruccion segura. |
| Siguiente accion | Exigir `usuario` en `DocumentoEmitido.clean()`, ajustar validacion API para considerar el request user en create, cubrir con pruebas y actualizar evidencia/trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
