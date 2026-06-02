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
| Frente activo | Contabilidad / Etapa 5 - liquidacion mensual con saldo final trazable. |
| Fuente exacta | `main` en `334c57c` despues de PR #635, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | `LiquidacionMensual` con `saldo_final_clp` distinto de cero exige explicacion/evidencia, pero no exigia una `LineaLiquidacionMensual` `saldo_final_explicado` que cuadrara con ese saldo. |
| Motivo de prioridad | PRD Etapa 5 exige que las liquidaciones mensuales no dejen saldos operativos pendientes sin balance final explicado, conciliado y trazable. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-liquidation-final-balance-line`. |
| Rama | `codex/stage5-liquidation-final-balance-line`. |
| Estado | Paquete tactico abierto; dominio, readiness y tests focales en progreso. |
| Gate esperado | Tests focales, suite impactada Contabilidad/Etapa 5, `manage.py check`, `makemigrations --check --dry-run`, gate local Etapa 5, frontend build/lint si aplica, acceptance local, higiene, `git diff --check` y CI antes de merge. |
| Estado al cerrar paquete | Pendiente de PR, CI, merge y limpieza. |
| Bloqueos relacionados | Etapa 5 no cierra sin Conciliacion cerrada, fuente `snapshot_controlado` o `real_autorizado`, ledger/reportes controlados y responsable. |
| Politica de reanudacion | Si este worktree existe, continuar y cerrar este paquete antes de abrir otro frente. |
| Siguiente accion | Completar validaciones, registrar evidencia, abrir PR, esperar CI, mergear y limpiar worktree/rama. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
