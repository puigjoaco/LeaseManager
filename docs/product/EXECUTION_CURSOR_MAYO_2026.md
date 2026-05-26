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
| Frente activo | Ninguno abierto en `main`; ultimo paquete integrado: PR #317 Etapa 2 / Cobranza y Canales - claves sensibles en restricciones operativas de gates. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna registrada en cursor. El ultimo paquete integrado endurecio `restricciones_operativas` de gates Canales/WebPay para detectar claves sensibles como `api_key`, `access_token` o `credential`, preservando claves canonicas de referencia no sensible. |
| Motivo de prioridad | PR #317 quedo mergeado; no cierra Etapa 2 sin fuente autorizada ni pruebas externas/controladas. |
| Worktree | Ninguno tactico activo. |
| Rama | `main`. |
| Estado | Main sincronizado con PR #317; siguiente paquete aun no seleccionado. |
| Gate esperado | Para el siguiente paquete, seleccionar frente seguro desde trazabilidad, abrir worktree `codex/...`, validar proporcionalmente y cerrar con PR/merge/limpieza. |
| Estado al cerrar paquete | No cierra Etapa 2; solo endurece gates locales para bloquear claves sensibles en restricciones operativas. |
| Bloqueos relacionados | Fuente autorizada Etapa 1, prueba Email/WebPay controlada y responsables siguen siendo condiciones de cierre, no requisitos para este paquete local. |
| Politica de reanudacion | Si `main` sigue limpio, tomar el siguiente frente seguro por trazabilidad. Si aparece un worktree sucio, terminarlo o pausarlo aqui antes de abrir otro. |
| Siguiente accion | Diagnosticar `main` real y elegir el siguiente paquete util sin depender de secretos, datos reales ni integraciones externas. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
