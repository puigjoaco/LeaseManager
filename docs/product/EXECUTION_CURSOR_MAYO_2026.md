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
| Frente activo | Compliance.DatosPersonalesChile2026. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `ExportacionSensible.encrypted_ref` no valida ni redacta referencias sensibles heredadas aunque se expone en API/backoffice. |
| Motivo de prioridad | PRD exige que datos/payloads/tokens queden fuera de superficies visibles; esta referencia debe ser trazable no sensible como el resto de evidencia controlada. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-encrypted-ref-redaction`. |
| Rama | `codex/compliance-encrypted-ref-redaction`. |
| Estado | Paquete abierto. |
| Gate esperado | Compliance local parcial: `classification=parcial`, `ready_for_compliance_data=false`, sin cierre evidencial. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | BLK-010 sigue siendo condicion de cierre Compliance, no bloquea esta preparacion local. |
| Politica de reanudacion | Si no hay worktree tactico sucio, seleccionar el siguiente paquete pequeno, seguro y trazable desde el estado real del repo. |
| Siguiente accion | Implementar validacion/redaccion/readiness de `encrypted_ref`, evidencia y trazabilidad; cerrar con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
