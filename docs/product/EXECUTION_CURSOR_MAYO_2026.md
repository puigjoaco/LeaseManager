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
| Frente activo | Etapa 2 - CobranzaActiva/Canales. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | API y snapshot de Canales exponen `NotificacionCobranzaProgramada.motivo_estado` heredado sin redaccion aunque dominio, admin y readiness tratan motivos sensibles como superficie cerrada. |
| Motivo de prioridad | Es una brecha local y verificable de Etapa 2; no requiere datos reales, secretos ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-notification-reason-redaction`. |
| Rama | `codex/stage2-notification-reason-redaction`. |
| Estado | Implementado y validado localmente; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Etapa 2 local debe seguir `classification=parcial`, `ready_for_stage2_cobranza=false`. |
| Estado al cerrar paquete | Focal 1 test OK; suite impactada 125 tests OK; `manage.py check`, `makemigrations --check --dry-run`, gate local Etapa 2 `classification=parcial`, `npm ci`, `npm run build`, `npm run lint`, acceptance local 960 tests OK, higiene repo y `git diff --check` OK. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, tomar el siguiente frente seguro desde trazabilidad y abrirlo explicitamente en este cursor. |
| Siguiente accion | Crear PR, esperar CI, mergear y limpiar worktree/ramas. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
