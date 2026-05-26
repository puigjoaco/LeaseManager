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
| Frente activo | Ninguno abierto en main; ultimo paquete trabajado: Etapa 1 - Contratos: guard de escritura para contratos con gastos comunes. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna pendiente en cursor. El ultimo paquete hizo que `Contrato.full_clean()` y `ContratoSerializer` bloqueen contratos vigentes/futuros con `tiene_gastos_comunes=True` si la propiedad principal no tiene `ServicioPropiedad` de gasto comun activo. |
| Motivo de prioridad | Paquete local y verificable cerrado como preparacion segura de Etapa 1. |
| Worktree | Ninguno pendiente despues de merge/limpieza. |
| Rama | `main` despues de merge/limpieza. |
| Estado | Paquete validado localmente y listo para PR/CI/merge/limpieza. |
| Gate esperado | Si `main` queda limpio, elegir el siguiente frente seguro por trazabilidad. Si existe worktree sucio, terminarlo o pausarlo aqui antes de abrir otro. |
| Estado al cerrar paquete | No cierra Etapa 1 sin snapshot o fuente real autorizada; solo mueve una regla local de gastos comunes desde readiness a validacion de escritura. |
| Bloqueos relacionados | Ninguno para este paquete. |
| Politica de reanudacion | Confirmar `git status --short --branch` y `git worktree list`; si solo existe `main` limpio, seleccionar el siguiente frente trazable. |
| Siguiente accion | Publicar PR, esperar CI, mergear, limpiar branch/worktree y confirmar `main` limpio. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
