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
| Frente activo | Reporting Etapa 7: alinear API financiera mensual con readiness para separar asientos no posteados y descuadrados. |
| Fuente exacta | `main` limpio tras mergear PR #790 (`cdd422bb`); rescue queda pausado fuera de alcance. |
| Brecha activa | `_assert_financial_monthly_traceability()` mezcla asientos no posteados y descuadrados bajo `reporting.accounting_entry_invalid`, mientras `audit_stage7_reporting_readiness` los clasifica con codigos especificos `stage7.reporting.accounting_entry_not_posted` y `stage7.reporting.accounting_entry_unbalanced`. |
| Motivo de prioridad | Cierra una discrepancia local, pequena y verificable entre API Reporting financiero mensual y readiness Etapa 7, sin datos reales, banco, SII, snapshots ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-financial-entry-state-alignment`. |
| Rama | `codex/stage7-financial-entry-state-alignment`. |
| Estado | En implementacion. |
| Gate esperado | Focal Reporting financiero mensual + readiness Etapa 7; suite impactada Reporting/readiness; `manage.py check`; migraciones dry-run; gate Etapa 7 local parcial; frontend build/lint; acceptance local; higiene y `git diff --check`; CI GitHub antes de merge. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo endurece rutas locales de Reporting. |
| Politica de reanudacion | Si se reanuda con este worktree activo, terminar este paquete antes de abrir otro frente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Separar codigos API para asientos no posteados y descuadrados, agregar pruebas focales, actualizar stage card/trazabilidad/evidencia y validar. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
