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
| Frente activo | Sin paquete tactico abierto despues del merge de Etapa 5 backoffice liquidaciones. |
| Fuente exacta | Paquete Etapa 5 `codex/stage5-liquidation-backoffice` validado localmente desde `main` limpio en `bea8047e`; al quedar mergeado, retomar desde `main` sincronizado. |
| Brecha activa | Ninguna en este cursor. El siguiente frente debe diagnosticarse desde PRD, trazabilidad, stage cards y estado real del repo. |
| Motivo de prioridad | Evitar que reanudaciones reabran metatareas o paquetes ya cerrados; el siguiente avance nace del repo limpio y no de contexto auxiliar. |
| Worktree | N/A; eliminar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage5-liquidation-backoffice` tras merge. |
| Rama | `main` tras merge. |
| Estado | El paquete deja el backoffice mostrando liquidaciones y lineas de liquidacion, condicionando aprobacion con liquidacion responsable visible y usando formulario trazable para reapertura. |
| Gate esperado | Para el siguiente paquete: diagnosticar frente seguro y proporcional desde repo limpio; no repetir esta brecha. |
| Estado al cerrar paquete | PR de Etapa 5 mergeado, CI verde, main limpio/sincronizado y worktree tactico eliminado. |
| Bloqueos relacionados | Etapa 5 no cierra sin Conciliacion cerrada, fuente `snapshot_controlado` o `real_autorizado`, ledger/reportes controlados y responsables finales. Es condicion de cierre, no freno para este paquete local. |
| Politica de reanudacion | Si el worktree tactico existe y esta sucio, terminar su PR o limpiar con instruccion segura. No reabrir PR #806/#807 ni este paquete, no reescribir goal, no pedir .env ni datos reales. |
| Siguiente accion | Tras merge/limpieza, elegir el siguiente frente util por trazabilidad y estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
