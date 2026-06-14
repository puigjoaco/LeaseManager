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
| Frente activo | Sin paquete tactico abierto. |
| Fuente exacta | `main` despues del mapeo EDIG AT2026: Etapa 6 alineada con motor anual tributario versionado e inventario estatico con matriz de senales funcionales. |
| Brecha activa | Pendiente elegir el siguiente frente seguro desde plan trazable, stage cards, gates y estado real del repositorio. |
| Motivo de prioridad | Evitar que compactaciones o contexto auxiliar reabran el paquete EDIG ya cerrado o vuelvan a redactar goals/prompts. |
| Worktree | N/A. |
| Rama | `main`. |
| Estado | Mapeo EDIG cerrado: EDIG protegido por Git, matriz EDIG->LeaseManager creada, runbook sandbox creado, script de inventario read-only con matriz de senales funcionales y arquitectura de Renta Anual actualizada. |
| Gate esperado | Antes del proximo paquete, confirmar `git status --short --branch`, `git worktree list` y seleccionar una brecha real que no dependa de secretos, EDIG ejecutado, SII real ni datos productivos. |
| Estado al cerrar paquete | Etapa 6 quedo alineada con normalizador anual RLI/CPT/RAI/SAC/DDJJ/F22 por ano tributario, con EDIG como referencia funcional no normativa y sin apertura del gate SII. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Ejecucion EDIG solo en VM/sandbox con datos ficticios. |
| Politica de reanudacion | No reabrir conversaciones de goal ni repetir el mapeo EDIG ya documentado. Si no hay worktree sucio, continuar por el siguiente frente util y seguro del repo; si un gate externo bloquea cierre, registrar una vez y seguir con preparacion local valida. |
| Siguiente accion | Diagnosticar estado real y avanzar el siguiente paquete tecnico trazable permitido por la arquitectura. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
