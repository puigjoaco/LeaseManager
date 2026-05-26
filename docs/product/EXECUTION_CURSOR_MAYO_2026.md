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
| Frente activo | Sin paquete tactico activo tras preparar match exacto residual acotado a cuenta recaudadora. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna fijada en cursor. |
| Motivo de prioridad | El paquete actual ya dejo preparado el guard para que referencias residuales de otra cuenta queden como ingreso desconocido/resolucion manual y no como cierre exacto. |
| Worktree | Ninguno esperado tras merge y limpieza. |
| Rama | Ninguna rama tactica esperada tras merge y limpieza. |
| Estado | Listo para PR/CI/merge/limpieza del paquete actual; luego seleccionar el siguiente frente desde `main`. |
| Gate esperado | Confirmar `git status --short --branch`, `git worktree list` y tomar el siguiente paquete seguro por trazabilidad vigente. |
| Estado al cerrar paquete | Etapa 3 no queda cerrada; solo queda mas estricto el matching exacto local para que codigos residuales respeten cuenta recaudadora. |
| Bloqueos relacionados | Banco real o snapshot autorizado, evidencia Etapa 2, prueba bancaria, cuadratura y responsable siguen siendo condiciones de cierre, no requisitos para este paquete local. |
| Politica de reanudacion | Si el worktree tactico aun existe, terminar PR/CI/merge/limpieza; si no existe, operar solo desde el estado real de `main` y este cursor. |
| Siguiente accion | Cerrar PR/CI/merge/limpieza del paquete actual y luego escoger el siguiente frente seguro. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
