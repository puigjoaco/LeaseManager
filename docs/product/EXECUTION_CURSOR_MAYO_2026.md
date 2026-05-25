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
| Frente activo | Compliance datos sensibles: guard de servicio para preparar exportaciones sensibles solo con categoria canonica y politica de retencion activa. |
| Fuente exacta | `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `Compliance datos sensibles`; `backend/compliance/services.py`; `backend/compliance/serializers.py`; `backend/compliance/tests.py`; `backend/core/compliance_data_readiness.py`; `scripts/run-compliance-data-readiness-gate.ps1`. |
| Brecha activa | La API de Compliance ya rechaza exportaciones con categoria incompatible o sin politica activa, pero `prepare_sensitive_export` puede invocarse directo sin ese guard central. |
| Motivo de prioridad | Frente transversal de seguridad en Etapa 0, local, verificable y sin depender de secretos, `.env`, datos reales, snapshots, backfills, deploys ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-export-service-guard`. |
| Rama | `codex/compliance-export-service-guard`. |
| Estado | En ejecucion local. |
| Gate esperado | `scripts/run-compliance-data-readiness-gate.ps1` debe seguir en `classification=parcial`, `ready_for_compliance_data=false` con fuente local; no cierra Compliance sin fuente autorizada, politica aprobada, responsables y validacion legal-operativa. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Falta fuente autorizada, politica aprobada, responsables, controles, evidencia archivada y validacion legal-operativa para cierre real de `Compliance.DatosPersonalesChile2026`; no bloquea el guard local. |
| Politica de reanudacion | Si este worktree existe, continuar y cerrar este paquete antes de abrir otro frente. |
| Siguiente accion | Centralizar validacion de categoria/politica activa en el servicio, cubrir tests focales, ejecutar gate local, acceptance, PR, CI, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
