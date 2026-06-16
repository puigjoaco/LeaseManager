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
| Frente activo | `company-accounting-review-boundary`, cerrado al merge. |
| Fuente exacta | `main` posterior al paquete AC2024/AT2025 con bienes raices/contribuciones controladas y al merge `1985b744`. |
| Brecha activa | El progreso contable/renta por empresa necesitaba frontera explicita para que `ready_for_company_accounting_review` no pudiera interpretarse como contabilidad autonoma, calculo tributario final ni presentacion SII. |
| Motivo de prioridad | Convierte la decision arquitectonica contable-tributaria asistida en contrato visible de API, Reporting, backoffice, stage cards y trazabilidad. |
| Worktree | Paquete trabajado en `D:/Proyectos/10_ACTIVOS/LeaseManager-company-accounting-review-boundary` con rama `codex/company-accounting-review-boundary`; tras merge no debe quedar activo. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `main` despues del merge. Para el siguiente paquete no trivial abrir worktree hermano `codex/...` desde `main` limpio. |
| Estado | `audit_company_accounting_progress` y Reporting `contabilidad/progreso-empresa/` exponen `review_boundary`: paquete local preparado para revision responsable, `autonomous_accounting=false`, `final_tax_calculation=false`, `sii_submission=false` y validacion responsable/experta requerida. `audit_company_accounting_candidates` y Reporting `contabilidad/candidatos-progreso-empresa/` exponen `selection_boundary`: seleccion empresa/ano con senales locales, sin fuentes externas ni gates externos. |
| Gate esperado | Validacion local con tests focales/impactados de progreso empresa, Reporting y readiness Etapas 5/6/7; gates locales deben seguir como diagnostico parcial cuando no hay fuente autorizada. No usar `.env`, secretos, DB real, SII real ni integraciones externas. |
| Estado al cerrar paquete | No reabrir prompts de goal, EDIG ni paquetes AC2024 mergeados como bloqueo general. `ready_for_company_accounting_review` significa avance revisable por responsable, no cierre contable, renta final ni presentacion SII. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Tras merge/limpieza, continuar con el siguiente frente trazable desbloqueado desde `main` limpio. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
