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
| Frente activo | Sin frente activo. |
| Fuente exacta | Confirmar siempre con `git status --short --branch`, `git worktree list` y `git log -1 --oneline` antes de abrir el siguiente paquete; el worktree rescue sigue pausado y fuera de alcance. |
| Brecha activa | Ninguna. Ultimo paquete preparado: Etapa 3 / Conciliacion normaliza refs y motivos antes de `full_clean` en conexiones, movimientos y cuadraturas bancarias. |
| Motivo de prioridad | Paquete cerrado localmente; Etapa 3 conserva valores canonicos antes de validadores de campo, persistencia, snapshot, readiness y auditoria. |
| Worktree | Ninguno de producto activo. |
| Rama | Ninguna de producto activa. |
| Estado | Listo para continuar con el siguiente paquete pequeno, local, verificable y cerrable sin tocar secretos ni fuentes externas. |
| Gate esperado | Para el siguiente paquete, elegir frente pequeno, local y verificable segun orden, trazabilidad y stage cards; no reabrir este paquete salvo regresion real. |
| Estado al cerrar paquete | Ultimo paquete debe confirmarse contra `git log -1 --oneline`, registro de evidencia y PR/CI remoto; si el cursor contradice Git, gana Git y se corrige el cursor en el siguiente paquete trazable. |
| Bloqueos relacionados | Los cierres evidenciales que dependan de fuentes externas siguen condicionados por autorizacion/fuente controlada y no bloquean trabajo local seguro. |
| Politica de reanudacion | Si no hay worktree tactico de producto abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; si solo aparece el rescue pausado, continuar con el siguiente paquete pequeno, local, verificable y cerrable sin tocar esos archivos. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
