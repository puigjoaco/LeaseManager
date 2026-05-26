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
| Frente activo | Ninguno en `main` despues de integrar el paquete vigente. |
| Fuente exacta | Estado real del repo, `git status --short --branch`, `git worktree list`, matriz de trazabilidad y stage cards. |
| Brecha activa | Ninguna declarada en este cursor; el ultimo paquete preparado corrige justificacion de pagos excepcionales en Etapa 2. |
| Motivo de prioridad | Evitar que reanudaciones o compactaciones reabran paquetes ya preparados/integrados. |
| Worktree | Ninguno esperado en `main` despues de limpieza; si existe un worktree `codex/...`, terminarlo o pausarlo explicitamente antes de abrir otro frente. |
| Rama | `main`; ramas tacticas solo mientras dure un paquete. |
| Estado | Esperando siguiente paquete seguro segun trazabilidad y orden de construccion. |
| Gate esperado | Para el siguiente paquete, definir gate proporcional desde el frente elegido. |
| Estado al cerrar paquete | El paquete Etapa 2 / justificacion de pagos excepcionales debe quedar integrado por PR, CI verde, merge y limpieza. |
| Bloqueos relacionados | Ninguno nuevo; cierres evidenciales siguen dependiendo de fuentes autorizadas cuando corresponda. |
| Politica de reanudacion | Si la rama `codex/stage2-exceptional-payment-justification` aun existe, terminar PR/CI/merge/limpieza; si ya no existe, no reabrir este paquete y seleccionar el siguiente frente seguro. |
| Siguiente accion | Confirmar estado real del repo y continuar con el siguiente paquete trazable, no con tareas auxiliares del chat. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
