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
| Frente activo | Etapa 0 - PlataformaBase: errores publicos seguros en login. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | El login publico no debe renderizar `error.message` interno ni nombres de variables/configuracion cuando falla autenticacion, backend o carga publica. |
| Motivo de prioridad | PRD exige errores publicos seguros y superficies anonimas sin detalles internos. |
| Worktree | `D:/Proyectos/LeaseManager-public-login-safe-errors` |
| Rama | `codex/public-login-safe-errors`. |
| Estado | Implementacion en curso. |
| Gate esperado | Build frontend, acceptance local y CI; no cambia gates externos ni usa datos reales. |
| Estado al cerrar paquete | Pendiente de validacion, PR, CI y merge. |
| Bloqueos relacionados | Ningun bloqueo externo nuevo; mejora local de baseline. |
| Politica de reanudacion | Continuar este worktree hasta validar, abrir PR, mergear, limpiar y luego resetear cursor. |
| Siguiente accion | Validar frontend build/lint si aplica, acceptance, higiene y PR. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
