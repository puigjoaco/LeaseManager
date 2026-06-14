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
| Frente activo | Ninguno abierto. Ultimo paquete: `stage6-ddjj-media-layouts`. |
| Fuente exacta | `main` en `11df1e53`, posterior al merge de PR #841. |
| Brecha cerrada localmente | Etapa 6 incorpora `AnnualTaxDDJJFormLayout` para declarar formularios DDJJ aplicables con medio SII, vencimiento, layout/certificado, fuente oficial/experta, hash y resumen trazable antes de la matriz DDJJ/F22. |
| Motivo de prioridad | Materializa `stage6-ddjj-official-media-layouts` desde `RENTA_ANUAL_OFFICIAL_SOURCE_GAPS_AT2026.md` como preparacion local revisable, no presentacion SII. |
| Worktree | Cerrado y removido: `D:/Proyectos/LeaseManager-stage6-ddjj-media-layouts`. |
| Rama | Cerrada: `codex/stage6-ddjj-media-layouts`. |
| Estado | PR #841 mergeado; main sincronizado. Queda solo este cierre de cursor operativo. |
| Gate esperado | `scripts/run-stage6-readiness-gate.ps1` queda en `classification=parcial`; no cierra Etapa 6 ni presenta DDJJ/F22 sin fuente final, certificacion/formato, responsable, autorizacion y evidencia no sensible. |
| Estado al cerrar paquete | Paquete DDJJ cerrado. Reanudar desde main limpio y elegir siguiente brecha segura por trazabilidad. |
| Bloqueos relacionados | DDJJ/F22 final sigue bloqueado sin medios/formato/certificacion SII vigentes, responsable y autorizacion explicita. |
| Politica de reanudacion | No reabrir `stage6-ddjj-media-layouts`; no reabrir goal prompts ni EDIG salvo nueva solicitud concreta. |
| Siguiente accion | Cerrar este cursor y luego tomar el siguiente paquete seguro desde `RENTA_ANUAL_OFFICIAL_SOURCE_GAPS_AT2026.md`, stage cards y trazabilidad vigentes. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
