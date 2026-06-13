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
| Frente activo | Reporting Etapa 7: alinear API tributaria anual con readiness para exigir resumen anual con obligaciones trazables no vacias. |
| Fuente exacta | `main` limpio tras mergear PR #787 (`3c147359`); rescue queda pausado fuera de alcance. |
| Brecha activa | `_assert_annual_tax_traceability()` acepta `ProcesoRentaAnual.resumen_anual` con `obligaciones=[]` porque solo valida que sea lista. `audit_stage7_reporting_readiness` exige lista no vacia mediante `_annual_summary_is_traceable()`, por lo que la API puede marcar verificado un reporte que el readiness bloquearia. |
| Motivo de prioridad | Cierra una discrepancia local, pequena y verificable entre API Reporting anual y readiness Etapa 7, sin datos reales, SII, certificados ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-annual-summary-obligations`. |
| Rama | `codex/stage7-annual-summary-obligations`. |
| Estado | En implementacion. |
| Gate esperado | Focal Reporting anual + readiness Etapa 7; suite impactada Reporting/readiness; `manage.py check`; migraciones dry-run; gate Etapa 7 local parcial; frontend build/lint; acceptance local; higiene y `git diff --check`; CI GitHub antes de merge. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo endurece rutas locales de Reporting. |
| Politica de reanudacion | Si se reanuda con este worktree activo, terminar este paquete antes de abrir otro frente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Implementar guard API para `obligaciones` no vacias, agregar prueba focal, actualizar stage card/trazabilidad/evidencia y validar. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
