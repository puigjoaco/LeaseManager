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
| Frente activo | Etapa 4 - SII/DTE: bloqueo de regimen fiscal no soportado para automatizacion tributaria v1. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` escenario transversal 16; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `SII`; `docs/product/STAGE_CARDS/ETAPA_4_SII_DTE.md`; `backend/sii`; `backend/core/stage4_sii_readiness.py`; `scripts/run-stage4-readiness-gate.ps1`. |
| Brecha activa | Los servicios de generacion SII ya rechazan empresas fuera del regimen automatizable, pero la apertura de capacidades SII y readiness de snapshots no bloquean explicitamente una `ConfiguracionFiscalEmpresa` activa con regimen no soportado. |
| Motivo de prioridad | Siguiente brecha local verificable que no depende de SII real, certificados, `.env`, secretos ni snapshot autorizado; reduce riesgo tributario antes de preparar cierres reales. |
| Worktree | `D:/Proyectos/LeaseManager-stage4-unsupported-regime-guard`. |
| Rama | `codex/stage4-unsupported-regime-guard`. |
| Estado | En ejecucion local. |
| Gate esperado | `scripts/run-stage4-readiness-gate.ps1` debe seguir en `classification=parcial`, `ready_for_stage4_sii=false` con fuente local; no cierra Etapa 4 sin ambiente SII/fuente autorizada y regla fiscal validada. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Falta ambiente SII real/controlado autorizado, evidencia de ledger, regla fiscal validada y responsable para cierre real de Etapa 4; no bloquea preparacion local. |
| Politica de reanudacion | Si este worktree existe, continuar y cerrar este paquete antes de abrir otro frente. |
| Siguiente accion | Validar modelo/API/readiness/docs, abrir PR, esperar CI, mergear y limpiar worktree. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
