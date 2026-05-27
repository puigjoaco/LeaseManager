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
| Frente activo | Etapa 1 - auditoria de telefono WhatsApp operativo. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | El modelo y Canales bloquean opt-in WhatsApp con telefono no internacional, pero el auditor Etapa 1 no emite un codigo especifico para snapshots heredados con esa condicion. |
| Motivo de prioridad | La stage card Etapa 1 exige validacion de telefonos para mensajeria; el cierre debe distinguir la brecha de datos heredados sin depender solo de `stage1.arrendatario.validacion_modelo`. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-whatsapp-phone-audit`. |
| Rama | `codex/stage1-whatsapp-phone-audit`. |
| Estado | Implementado y validado localmente; pendiente PR/CI/merge. |
| Gate esperado | Diagnostico Etapa 1 local debe permanecer no evidencial/parcial salvo fuente autorizada; el nuevo caso debe clasificar snapshot heredado defectuoso. |
| Estado al cerrar paquete | Focal 1 test OK; suite impactada 223 tests OK; `manage.py check`, `makemigrations --check --dry-run`, gate local Etapa 1 diagnostico, `npm ci`, `npm run build`, `npm run lint` y acceptance local 960 tests OK. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, tomar el siguiente frente seguro desde trazabilidad y abrirlo explicitamente en este cursor. |
| Siguiente accion | Publicar PR, esperar CI, mergear y limpiar worktree/ramas. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
