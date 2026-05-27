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
| Frente activo | Etapa 5 - Documentos PDF y firma. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Auditorias documentales de PDF generado, preview, formalizacion y versiones correctivas pueden conservar refs sensibles heredadas solo como metadata desalineada, sin clasificacion explicita ni redaccion defensiva en builders. |
| Motivo de prioridad | Completar el control de Documentos para que eventos auditables no conserven storage/evidencia/correccion sensibles y readiness los clasifique sin exponer valores. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-document-audit-metadata-redaction`. |
| Rama | `codex/stage5-document-audit-metadata-redaction`. |
| Estado | Validado localmente; pendiente PR, CI, merge y limpieza. |
| Gate esperado | Etapa 5 Documentos local debe seguir como diagnostico parcial: `classification=parcial`, `ready_for_stage5_documents=false`, sin fuente documental autorizada. |
| Estado al cerrar paquete | Focal 2 tests OK; suite impactada 204 tests OK; `manage.py check`, `makemigrations --check --dry-run`, gate local Etapa 5 Documentos `classification=parcial`, `npm ci`, `npm run build`, `npm run lint`, acceptance local 973 tests OK, higiene repo y `git diff --check` OK; CI GitHub pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta validar, integrar y limpiar; no abrir otro frente mientras siga activo. |
| Siguiente accion | Ejecutar higiene final, abrir PR, esperar CI, mergear y limpiar worktree. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
