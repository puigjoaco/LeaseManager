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
| Frente activo | Etapa 0 - Compliance datos sensibles: auditoria de acceso denegado a exportaciones. |
| Fuente exacta | `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `Compliance datos sensibles`; `backend/compliance`; `backend/core/compliance_data_readiness.py`; `scripts/run-compliance-data-readiness-gate.ps1`. |
| Brecha activa | Los accesos fallidos a contenido de exportaciones revocadas o expiradas devuelven error, pero no dejan evento auditable especifico del intento denegado. |
| Motivo de prioridad | Es una brecha local segura de Stage 0 Compliance: todo acceso a datos sensibles debe quedar trazado sin exponer payloads. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-denied-export-audit`. |
| Rama | `codex/compliance-denied-export-audit`. |
| Estado | Paquete tactico abierto desde `main` limpio en `c17a59e`; implementacion y validacion en curso. |
| Gate esperado | `scripts/run-compliance-data-readiness-gate.ps1` debe seguir en `classification=parcial`, `ready_for_compliance_data=false` con fuente local; no cierra Compliance sin fuente autorizada y refs finales. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Falta fuente `snapshot_controlado` o `real_autorizado`, politica aprobada, responsables, controles, evidencia archivada y validacion legal-operativa no sensibles para cierre real de `Compliance.DatosPersonalesChile2026`; no bloquea preparacion local. |
| Politica de reanudacion | Continuar este paquete desde el worktree indicado; si esta cerrado, volver a `main` limpio y seleccionar el siguiente frente trazable. |
| Siguiente accion | Implementar, validar, documentar evidencia/trazabilidad, empaquetar PR, esperar CI, mergear y limpiar worktree/rama. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
