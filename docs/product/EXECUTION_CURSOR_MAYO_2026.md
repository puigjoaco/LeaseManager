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
| Frente activo | Etapa 4 / SII. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `stage4-sii-observations-redaction`: observaciones tributarias de DTE/F29/DDJJ/F22 deben rechazar nuevas referencias sensibles, exponerse redactadas y quedar clasificadas por readiness Etapa 4. |
| Motivo de prioridad | Superficie SII local y verificable: el admin ya redacta observaciones heredadas, pero dominio, servicios, API/snapshot y readiness no cierran la misma regla. |
| Worktree | `D:/Proyectos/LeaseManager-stage4-sii-observations-redaction`. |
| Rama | `codex/stage4-sii-observations-redaction`. |
| Estado | Validado localmente; pendiente PR, CI, merge y limpieza. |
| Gate esperado | Gate local Etapa 4 como diagnostico: `classification=parcial`, `ready_for_stage4_sii=false`; no cierra SII sin fuente autorizada. |
| Estado al cerrar paquete | Implementacion, pruebas proporcionales, evidencia y trazabilidad completas localmente; pendiente PR, CI, merge y limpieza. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree tactico hasta cerrarlo, pausarlo explicitamente o limpiarlo tras merge. |
| Siguiente accion | Crear PR del paquete, esperar CI, mergear si pasa y limpiar worktree/rama; luego cerrar el cursor. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
