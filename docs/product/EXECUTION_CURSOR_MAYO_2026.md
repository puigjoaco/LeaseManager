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
| Frente activo | Sin worktree tactico activo; ultimo paquete cerrado: Etapa 0 - PlataformaBase, errores publicos seguros en login. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna brecha abierta en curso. El paquete #353 cerro la superficie publica de login para no renderizar `error.message` interno ni nombres de variables/configuracion. |
| Motivo de prioridad | Paquete cerrado por PRD de errores publicos seguros y baseline anonimo sin detalles internos. |
| Worktree | Ninguno; solo debe existir el worktree principal despues de limpiar `D:/Proyectos/LeaseManager-public-login-safe-errors`. |
| Rama | `main`. |
| Estado | Paquete #353 validado, integrado y limpiado. |
| Gate esperado | Para el siguiente paquete: diagnosticar desde trazabilidad y ejecutar validaciones proporcionales. |
| Estado al cerrar paquete | PR #353 mergeado en `main` con merge commit `2fc5b78`; CI acceptance remoto OK. |
| Bloqueos relacionados | Ningun bloqueo externo nuevo; mejora local de baseline. |
| Politica de reanudacion | Si no hay worktree tactico sucio, seleccionar el siguiente paquete pequeno, seguro y trazable desde el estado real del repo. |
| Siguiente accion | Confirmar `main` limpio y elegir el proximo frente desbloqueado por trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
