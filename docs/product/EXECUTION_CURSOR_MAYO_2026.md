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
| Frente activo | Ninguno; ultimo paquete cerrado: Etapa 3 - Conciliacion: guard de `referencia` sensible en movimientos bancarios importados. |
| Fuente exacta | PR #215 `Guard Stage 3 bank movement references`; commit `b9ee39c`; merge `9c7e5d9`; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `Conciliacion`; `docs/product/STAGE_CARDS/ETAPA_3_BANCO_CONCILIACION.md`; `backend/conciliacion`; `backend/core/stage3_conciliacion_readiness.py`; `scripts/run-stage3-readiness-gate.ps1`. |
| Brecha activa | Cerrada localmente: `MovimientoBancarioImportado.referencia` queda validada como referencia bancaria no sensible, API/snapshot redactan referencias sensibles heredadas y readiness conserva deteccion bloqueante de snapshots existentes. |
| Motivo de prioridad | Paquete integrado; no hay worktree tactico abierto para este frente. |
| Worktree | Ninguno. |
| Rama | `main` sincronizada tras merge `9c7e5d9`. |
| Estado | PR #215 integrado con CI `acceptance` verde; worktree `D:/Proyectos/LeaseManager-stage3-bank-movement-reference-guard` eliminado y rama tactica local/remota eliminada. |
| Gate esperado | `scripts/run-stage3-readiness-gate.ps1` debe seguir en `classification=parcial`, `ready_for_stage3_conciliacion=false` con fuente local; no cierra Etapa 3 sin banco real o snapshot autorizado. |
| Estado al cerrar paquete | `parcial`; avance local preparado, sin cierre real de Etapa 3. |
| Bloqueos relacionados | Falta banco real o snapshot autorizado, evidencia Etapa 2, prueba bancaria, cuadratura sistema/banco y responsable para cierre real de Etapa 3; no bloquea preparacion local. |
| Politica de reanudacion | Si `main` esta limpio y no hay worktrees tacticos sucios, seleccionar el siguiente frente util, seguro y trazable desde la matriz/PRD/arquitectura. |
| Siguiente accion | Diagnosticar el siguiente paquete local cerrable y abrir worktree `codex/...` solo si el cambio no es trivial. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
