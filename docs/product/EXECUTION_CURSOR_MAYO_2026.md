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
| Frente activo | Contabilidad / Etapa 5: guard de liquidacion mensual antes de aprobar cierre contable. |
| Fuente exacta | Estado real de `main` en `1fa1944`, matriz de trazabilidad, `docs/product/STAGE_CARDS/ETAPA_5_CIERRE_MENSUAL_CONTABILIDAD.md` y readiness Etapa 5 vigentes. |
| Brecha activa | `approve_monthly_close()` permite aprobar un `CierreMensualContable` sin `LiquidacionMensual` de empresa preparada/aprobada para el mismo periodo, aunque `audit_stage5_contabilidad_readiness` ya clasifica ese snapshot como `stage5.close_company_liquidation_missing`. |
| Motivo de prioridad | Es una brecha local verificable entre servicio operacional y readiness: el cierre aprobado debe conservar liquidacion de empresa antes de alimentar reporting/cierre, sin usar banco real, SII, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-close-liquidation-guard`. |
| Rama | `codex/stage5-close-liquidation-guard`. |
| Estado | Paquete abierto; implementar guard en servicio/API, ajustar flujos demo/tests necesarios y actualizar evidencia/trazabilidad. |
| Gate esperado | Focal Contabilidad para aprobacion de cierre; suite impactada `contabilidad` + `core.tests_stage5_contabilidad_readiness`; `manage.py check`; `makemigrations --check --dry-run --noinput`; gate local Etapa 5 como diagnostico parcial; validaciones frontend/acceptance proporcionales antes de PR. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Etapa 5 sigue parcial para cierre real por Conciliacion/fuente autorizada/evidencia externa. Este paquete no requiere `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si este worktree queda sucio, continuar o pausar este paquete antes de abrir otro frente. |
| Siguiente accion | Implementar guard de liquidacion mensual en aprobacion de cierre y validar con pruebas proporcionales. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
