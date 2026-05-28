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
| Frente activo | Etapa 3 / Conciliacion - alineacion de periodo en clasificacion manual de cargos bancarios. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, `docs/product/STAGE_CARDS/ETAPA_3_BANCO_CONCILIACION.md`, trazabilidad y evidencia vigentes. |
| Brecha activa | Las resoluciones manuales de cargos bancarios validan formato de `periodo_economico`, pero no fuerzan que coincida con el mes del movimiento bancario que queda conciliado. |
| Motivo de prioridad | Paquete pequeno y verificable de Etapa 3; evita metadata contable/bancaria desalineada sin requerir banco real, secretos, `.env`, DB historica ni snapshot autorizado. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-charge-period-alignment`. |
| Rama | `codex/stage3-charge-period-alignment`. |
| Estado | Validado localmente; pendiente PR, CI remoto, merge y limpieza. |
| Gate esperado | Gate local Etapa 3 como diagnostico: `classification=parcial`, `ready_for_stage3_conciliacion=false`, sin declarar cierre por falta de fuente autorizada. |
| Estado al cerrar paquete | Pendiente confirmar PR/CI/merge/limpieza, main limpio y cursor cerrado o actualizado. |
| Bloqueos relacionados | BLK-003 sigue impidiendo cierre de banco/Conciliacion sin fuente `snapshot_controlado` o `real_autorizado`; no bloquea este hardening local. |
| Politica de reanudacion | Si no existe worktree tactico sucio, seleccionar el siguiente frente seguro desde estado real del repo y documentos rectores. |
| Siguiente accion | Publicar PR del paquete, esperar CI, mergear y limpiar worktree/rama; luego cerrar o actualizar cursor. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
