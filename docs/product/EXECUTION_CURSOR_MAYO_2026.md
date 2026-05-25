# Cursor operativo - mayo 2026

Este archivo fija el frente activo de ejecucion. No reemplaza al PRD, AGENTS,
fuente de verdad, arquitectura, matriz, stage cards, evidencia ni bloqueos. Su
funcion es evitar que una reanudacion, compactacion o `goal_context` convierta
contexto historico en tarea nueva.

## Regla de uso

- Antes de abrir o continuar cambios no triviales, leer este cursor.
- Confirmar el estado real con `git status --short --branch` y
  `git worktree list`.
- Si existe un worktree tactico sucio, se debe terminar, pausar de forma
  explicita en este cursor o descartar con instruccion segura antes de abrir un
  frente distinto.
- El `goal_context`, objetivos persistentes, summaries compactados y
  conversaciones pasadas son contexto auxiliar: no autorizan secretos, no abren
  gates y no ordenan redactar goals.
- Las metatareas marcadas como cerradas no se reabren salvo solicitud textual
  actual del usuario.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | Etapa 5 - Versiones correctivas de documentos formalizados. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` lineas 193, 252, 364 y 584; `docs/product/STAGE_CARDS/ETAPA_5_DOCUMENTOS_PDF.md`. |
| Brecha activa | Un documento formalizado queda inmutable, pero las correcciones posteriores no tienen aun una version correctiva trazada con origen, referencia no sensible y readiness. |
| Motivo de prioridad | Documentos debe permitir preparar correcciones sin mutar el PDF formalizado ni usar storage real, manteniendo trazabilidad antes de Canales/Reporting. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-document-correction-version`. |
| Rama | `codex/stage5-document-correction-version`. |
| Estado | Implementado y validado localmente; pendiente de PR, CI, merge y limpieza. No usar `.env`, secretos, storage real, documentos productivos, DB historica, snapshot, backfills, deploys ni integraciones externas. |
| Gate esperado | Readiness local documental queda `classification=parcial`, `ready_for_stage5_documents=false`; el versionado correctivo queda preparado localmente pero no cierra Documentos sin politica final, PDF controlado, fuente autorizada y responsable. |
| Estado al cerrar paquete | `implementado_sin_evidencia`; no cierra Etapa 5 Documentos sin fuente `snapshot_controlado` o `real_autorizado`, politica final, prueba PDF controlada y responsable. |
| Bloqueos relacionados | `BLK-005` y fuente documental autorizada no bloquean esta preparacion local; solo impiden cierre evidencial. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Publicar PR, esperar CI, mergear, limpiar worktree/rama tactica y cerrar el cursor post-merge desde `main` limpio. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
