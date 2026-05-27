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
| Frente activo | SII / superficies administrativas. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | El admin Django de SII expone y busca referencias tributarias crudas en capacidades y DTE, y no registra vistas administrativas redactadas para F29, Proceso Renta, DDJJ ni F22. |
| Motivo de prioridad | Tras cerrar superficies admin de modulos previos, SII es el siguiente frente en orden con refs/payloads tributarios sensibles ya cubiertos por API/snapshot/readiness pero no por admin. |
| Worktree | `D:/Proyectos/LeaseManager-stage4-sii-admin-redaction`. |
| Rama | `codex/stage4-sii-admin-redaction`. |
| Estado | Paquete implementado y validado localmente; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Etapa 4 local diagnostica/parcial; no cierre sin fuente autorizada, ambiente SII/regla fiscal/evidencia externa. |
| Estado al cerrar paquete | Validacion local completada: prueba focal SII admin, suite SII/readiness Etapa 4, `manage.py check`, `makemigrations --check --dry-run`, gate Etapa 4 local diagnostico/parcial, `npm ci`, `npm run build`, `npm run lint`, acceptance workflows e higiene previa. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si se reanuda esta sesion, continuar este worktree antes de abrir otro paquete. |
| Siguiente accion | Ejecutar higiene final, commit, PR, CI, merge, limpieza del worktree tactico y reset del cursor. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
