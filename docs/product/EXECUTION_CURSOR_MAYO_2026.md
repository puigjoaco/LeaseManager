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
| Frente activo | Etapa 2 - Canales/WhatsApp. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `Arrendatario.whatsapp_bloqueo_motivo` no rechaza nuevas referencias sensibles ni se redacta al exponer datos heredados. |
| Motivo de prioridad | Continuidad local de Etapa 2: los motivos de bloqueo ya se endurecieron para mensajes salientes y WebPay; falta la superficie equivalente del bloqueo definitivo WhatsApp. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-whatsapp-block-motive-redaction`. |
| Rama | `codex/stage2-whatsapp-block-motive-redaction`. |
| Estado | En desarrollo. |
| Gate esperado | `run-stage2-readiness-gate.ps1` debe permanecer `classification=parcial`, `ready_for_stage2_cobranza=false` sin llamar proveedores. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar solo este worktree hasta PR/CI/merge/limpieza o pausar aqui con estado explicito. |
| Siguiente accion | Validar y documentar el guard/redaccion de motivo sensible de bloqueo WhatsApp. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
