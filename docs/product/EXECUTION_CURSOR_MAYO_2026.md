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
| Frente activo | API Reporting Etapa 7 - auditoria anual `status_updated` acotada al reporte. |
| Fuente exacta | `main` limpio tras mergear PR #785 (`38777a13`); rescue queda pausado fuera de alcance. |
| Brecha activa | `_assert_annual_tax_traceability()` valida procesos/DDJJ/F22, refs y payloads, pero no bloquea eventos `sii.ddjj_preparacion.status_updated` o `sii.f22_preparacion.status_updated` incompletos cuando pertenecen a documentos incluidos en el reporte anual. Readiness ya reporta esa brecha en Etapa 7. |
| Motivo de prioridad | Alinear API y readiness para que Reporting no entregue estado `verificado` sobre auditoria anual heredada sin `campo_estado`, `estado_anterior` y `estado_nuevo`. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-annual-status-audit-api`. |
| Rama | `codex/stage7-annual-status-audit-api`. |
| Estado | En implementacion local segura; no requiere `.env`, secretos, DB historica, datos reales, snapshots autorizados ni SII real. |
| Gate esperado | Focal Reporting API para auditoria anual; suite impactada `reporting core.tests_stage7_reporting_readiness`; `manage.py check`; migraciones dry-run; gate Etapa 7 parcial esperado; frontend build/lint; acceptance local; higiene y `git diff --check`; CI GitHub antes de merge. |
| Estado al cerrar paquete | Pendiente de validacion y PR. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo endurece rutas locales de Reporting. |
| Politica de reanudacion | Si este worktree queda sucio, terminarlo o pausarlo explicitamente en este cursor antes de abrir otro frente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Validar focalmente el nuevo guard de auditoria anual, actualizar stage card/trazabilidad/evidencia y cerrar con PR/CI/merge si todo pasa. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
