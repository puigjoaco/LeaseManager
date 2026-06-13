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
| Frente activo | Paquete tactico abierto: alinear codigos de Reporting anual DDJJ/F22 con readiness Etapa 7. |
| Fuente exacta | `main` limpio `39e3b0cc` tras PR #793; brecha detectada al comparar `_assert_annual_tax_traceability()` con `audit_stage7_reporting_readiness`. Rescue queda pausado fuera de alcance. |
| Brecha activa | `_assert_annual_tax_traceability()` agrupa documentos DDJJ/F22 faltantes o sin resumen bajo codigos genericos; readiness ya clasifica esos casos con codigos separados por DDJJ/F22. |
| Motivo de prioridad | Reducir ambiguedad de API/gate en Etapa 7 sin usar secretos, datos reales, SII real ni snapshot autorizado. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-annual-document-code-alignment`. |
| Rama | `codex/stage7-annual-document-code-alignment`. |
| Estado | En implementacion local. |
| Gate esperado | Focal Reporting anual, suite Reporting/readiness Etapa 7, `manage.py check`, migraciones dry-run, gate local Etapa 7 parcial esperado, frontend build/lint, acceptance local, higiene, PR, CI y merge. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo endurece rutas locales de Reporting. |
| Politica de reanudacion | Continuar este worktree si existe sucio. No redactar goal ni pedir autorizaciones externas para este paquete; no usa fuentes sensibles. |
| Siguiente accion | Ejecutar tests focales del endpoint anual, suite impactada y validaciones proporcionales; documentar evidencia final antes de PR. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
