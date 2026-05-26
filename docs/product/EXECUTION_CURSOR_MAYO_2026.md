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
| Frente activo | Ninguno. |
| Fuente exacta | `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`, stage cards vigentes y estado real del repo. |
| Brecha activa | Ninguna abierta en cursor. Ultimo paquete preparado: Etapa 2 / CobranzaActiva - trazabilidad de UF manual. |
| Motivo de prioridad | Mantener el siguiente frente gobernado por trazabilidad y worktree limpio, no por memoria de conversacion. |
| Worktree | Root principal `D:/Proyectos/LeaseManager` cuando main quede sincronizado. |
| Rama | `main`. |
| Estado | Esperando siguiente paquete seguro despues de integracion/limpieza. |
| Gate esperado | Definirlo al abrir el siguiente frente, segun modulo afectado. |
| Estado al cerrar paquete | UF manual validada localmente: focales, suite impactada, readiness Etapa 1/2, build frontend, acceptance local, higiene y whitespace OK. |
| Bloqueos relacionados | Integraciones UF reales siguen bajo `BLK-003`; no bloquean preparacion local y solo condicionan cierre evidencial. |
| Politica de reanudacion | Si existe un worktree `codex/...` sucio, terminarlo o pausarlo aqui antes de abrir otro frente. Si main esta limpio, tomar el siguiente frente desde trazabilidad. |
| Siguiente accion | Tras merge y limpieza, seleccionar el siguiente paquete seguro por matriz trazable. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
