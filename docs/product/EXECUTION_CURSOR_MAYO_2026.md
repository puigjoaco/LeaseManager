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
| Frente activo | `stage1-post-tenant-replacement-common-expense`. |
| Fuente exacta | `main` posterior al paquete `stage1-tenant-replacement-common-expense` cuando el PR quede mergeado. |
| Brecha activa | El flujo guiado de cambio de arrendatario queda alineado con el guard de gastos comunes estructurados: no debe permitir contrato futuro con `tiene_gastos_comunes=True` si la propiedad principal heredada no tiene `ServicioPropiedad` activo de tipo gasto comun. |
| Motivo de prioridad | Etapa 1/Contratos ya exigia el guard en altas/ediciones directas, pero el flujo guiado creaba un candidato pre-save antes de copiar relaciones de propiedad; el paquete evita que ese camino persista contratos futuros incompletos. |
| Worktree | Paquete trabajado en `D:/Proyectos/10_ACTIVOS/LeaseManager-stage1-tenant-replacement-common-expense` con rama `codex/stage1-tenant-replacement-common-expense`; al cerrar el PR debe eliminarse. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage1-tenant-replacement-common-expense` hasta merge; despues volver a `main` limpio. |
| Estado | `Contrato.full_clean()` valida gastos comunes pre-save cuando recibe `_common_expense_primary_property_id`, y `execute_tenant_replacement` pasa la propiedad principal heredada al contrato futuro antes de `full_clean()`. Tests focales e impactados, checks, gate local Etapa 1, frontend y acceptance local pasaron como preparacion segura. |
| Gate esperado | El paquete no declara cierre de Etapa 1; no usa secretos, no toca `.env`, no usa DB historicas, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Estado al cerrar paquete | No reabrir prompts de goal, proof espejo AC2024/AT2025, upgrade de acciones CI, matcher CI ni este guard de cambio de arrendatario salvo fallo nuevo o evidencia contradictoria. |
| Bloqueos relacionados | Ninguno nuevo. Los cierres productivos futuros siguen sujetos a responsable tributario, autorizacion explicita, fuentes reales/controladas vigentes y gates externos cuando corresponda. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Cerrar este paquete con commit, PR, CI, merge y limpieza; despues continuar el proyecto desde el siguiente frente real de producto/arquitectura segun PRD, trazabilidad y stage cards. No crear tareas de goal prompt, no repetir el cierre del proof espejo, no repetir el upgrade CI, no repetir el ajuste de matcher ni reabrir este guard salvo fallo nuevo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
