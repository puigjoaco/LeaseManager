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
| Frente activo | Ninguno abierto en main; ultimo paquete trabajado: Etapa 0 - Compliance: eventos de exportacion sensible vinculados a exportacion existente. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna pendiente en cursor. El ultimo paquete hizo que `audit_compliance_data_readiness` clasifique eventos de exportacion sensible `prepared`/`accessed`/`access_denied`/`revoked` con `entity_type` incorrecto, `entity_id` vacio o `entity_id` sin `ExportacionSensible` existente como `compliance.audit_target_invalid`. |
| Motivo de prioridad | Paquete local, verificable y sin dependencia de `.env`, datos reales, secretos ni integraciones externas. |
| Worktree | Ninguno pendiente despues de merge/limpieza; durante el paquete se uso `D:/Proyectos/LeaseManager-compliance-export-audit-target`. |
| Rama | `main` despues de merge/limpieza; durante el paquete se uso `codex/compliance-export-audit-target`. |
| Estado | Paquete validado localmente y listo para cierre con PR/merge/limpieza. |
| Gate esperado | Si `main` esta limpio, elegir el siguiente frente por trazabilidad. Si aparece un worktree tactico sucio, terminarlo o pausarlo aqui antes de abrir otro frente. |
| Estado al cerrar paquete | No cierra Compliance.DatosPersonalesChile2026; mejora trazabilidad local de eventos de auditoria de exportaciones sensibles. |
| Bloqueos relacionados | Politica aprobada, responsables, controles, evidencia archivada, validacion legal-operativa y fuente autorizada siguen siendo condiciones de cierre, no requisitos para este paquete. |
| Politica de reanudacion | Confirmar `git status --short --branch` y `git worktree list`; con `main` limpio, tomar el siguiente paquete local seguro segun trazabilidad. |
| Siguiente accion | Cerrar PR/merge/limpieza de este paquete; luego diagnosticar `main` y elegir el siguiente frente util sin depender de secretos, datos reales ni integraciones externas. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
