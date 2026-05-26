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
| Frente activo | Etapa 0 - Compliance datos sensibles: clasificacion explicita de refs sensibles en readiness. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `audit_compliance_data_readiness` no debe confundir referencias finales/de fuente sensibles con referencias faltantes genericas. |
| Motivo de prioridad | Compliance es frente base transversal; distinguir refs sensibles mejora diagnostico y cierre sin usar datos reales ni integraciones. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-sensitive-readiness-refs` |
| Rama | `codex/compliance-sensitive-readiness-refs`. |
| Estado | Implementacion en curso. |
| Gate esperado | Readiness Compliance sigue `parcial` en local; no cerrar `Compliance.DatosPersonalesChile2026` sin fuente autorizada y evidencia legal-operativa no sensible. |
| Estado al cerrar paquete | Pendiente de validacion, PR, CI y merge. |
| Bloqueos relacionados | `BLK-010` sigue como condicion de cierre externo. |
| Politica de reanudacion | Continuar este worktree hasta validar, abrir PR, mergear, limpiar y luego resetear cursor. |
| Siguiente accion | Validar tests focales/impactados, gate Compliance local, acceptance proporcional, higiene y PR. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
