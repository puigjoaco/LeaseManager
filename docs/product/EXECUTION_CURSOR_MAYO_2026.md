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
| Frente activo | Etapa 0 / scripts externos seguros. |
| Fuente exacta | `main` `5f329db0` verificado al abrir el paquete con `git status --short --branch`, `git worktree list` y `git log -1 --oneline`; no usar este SHA como sustituto del estado real en futuras reanudaciones. |
| Brecha activa | `railway-backend-bootstrap.ps1` solo usa `backend/railway.env.example` por defecto, pero podia aceptar `-BackendEnvPath backend\.env` y leer un `.env` real en modo plan antes de cualquier autorizacion de apply. |
| Motivo de prioridad | Brecha de seguridad operativa vinculada al problema de reanudaciones/bloqueos: los scripts externos no deben leer `.env` reales ni fuentes sensibles por parametro. |
| Worktree | `D:/Proyectos/LeaseManager-stage0-railway-env-guard`; rescue pausado permitido: `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` solo para decision posterior de limpieza, no para trabajo activo. |
| Rama | `codex/stage0-railway-env-guard`. |
| Estado | Paquete tactico abierto. |
| Gate esperado | `scripts/tests/external-script-policy.test.ps1`, `manage.py check`, `makemigrations --check --dry-run --noinput`, `npm ci`, `npm run lint`, `npm run build`, acceptance local sin smoke, higiene repo y CI remoto. |
| Estado al cerrar paquete | Ultimo paquete cerrado debe confirmarse contra `git log -1 --oneline`, registro de evidencia y PR/CI remoto; si el cursor contradice Git, gana Git y se corrige el cursor en el siguiente paquete trazable. |
| Bloqueos relacionados | Los cierres evidenciales que dependan de fuentes externas siguen condicionados por autorizacion/fuente controlada y no bloquean trabajo local seguro. |
| Politica de reanudacion | Si no hay worktree tactico de producto abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; si solo aparece el rescue pausado, continuar con el siguiente paquete pequeno, local, verificable y cerrable sin tocar esos archivos. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
