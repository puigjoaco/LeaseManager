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
| Frente activo | Ninguno abierto en `main`; ultimo paquete trabajado: Etapa 4 / SII - claves sensibles en payloads tributarios locales. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna pendiente en cursor. El ultimo paquete endurece SII para rechazar claves sensibles en `ultimo_resultado`, `resumen_formulario`, `resumen_anual`, `resumen_paquete` y `resumen_f22`. |
| Motivo de prioridad | La stage card Etapa 4 exige refs/payloads no sensibles y el paquete se cerro localmente sin SII, certificados, `.env`, datos reales ni integraciones externas. |
| Worktree | Ninguno tactico debe quedar activo tras merge/limpieza. |
| Rama | `main` tras merge/limpieza. |
| Estado | Paquete validado localmente; al reanudar, confirmar `git status --short --branch` y `git worktree list`. |
| Gate esperado | Si `main` esta limpio, seleccionar el siguiente frente seguro desde trazabilidad; si aparece worktree sucio, terminarlo o pausarlo aqui antes de abrir otro. |
| Estado al cerrar paquete | No cierra Etapa 4; solo endurece escritura/readiness local de payloads tributarios. |
| Bloqueos relacionados | Ambiente SII real/controlado, evidencia de ledger, regla fiscal validada y responsable siguen siendo condiciones de cierre, no requisitos para este paquete local. |
| Politica de reanudacion | Si `main` sigue limpio y no hay worktree tactico sucio, tomar el siguiente frente seguro por trazabilidad. |
| Siguiente accion | Diagnosticar `main` real y elegir el siguiente paquete util sin depender de secretos, datos reales ni integraciones externas. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
