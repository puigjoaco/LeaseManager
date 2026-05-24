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
| Frente activo | Sin paquete tactico abierto; ultimo cierre Etapa 1/2 - Garantias contractuales |
| Fuente exacta | PR #175 `Guard partial guarantee acceptance`, merge `bfa360d`, desde reglas de garantias parciales en Cobranza del PRD canonico |
| Brecha activa | Cerrada localmente: una garantia recibida parcialmente queda visible como incompleta hasta regularizarse o aceptarse formalmente con referencia trazable no sensible. |
| Motivo de prioridad | Evita que reanudaciones intenten cerrar de nuevo el PR #175 o reabrir el worktree ya eliminado. |
| Worktree | Ninguno activo para este paquete; usar solo `D:/Proyectos/LeaseManager` hasta abrir el siguiente `codex/...`. |
| Rama | `main` sincronizada; no hay rama `codex/guarantee-partial-acceptance` activa. |
| Estado | PR #175 integrado en `main`, CI acceptance verde, worktree/rama tactica eliminados. |
| Gate esperado | No hay gate pendiente para este paquete; el siguiente frente debe seleccionarse desde `main` limpio con una brecha local segura y validacion proporcional. |
| Estado al cerrar paquete | `implementado_sin_evidencia`; no cierra Etapa 1/2 sin fuente `snapshot_controlado` o `real_autorizado`. |
| Bloqueos relacionados | `BLK-002` solo bloquea cierre evidencial de Etapa 1; no bloquea esta preparacion local. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Desde `main` limpio, seleccionar el siguiente paquete local seguro por orden de arquitectura y trazabilidad, abrir nuevo worktree `codex/...` y avanzar sin reabrir metatareas cerradas. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
