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
| Frente activo | Contabilidad. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | El admin Django de Contabilidad expone o busca refs/payloads crudos en efectos de reapertura, libros, mayores y balances, mientras las APIs ya redactan esas superficies. |
| Motivo de prioridad | Etapa 5 exige no exponer URLs, tokens, credenciales, correos ni referencias sensibles en `storage_ref`, payloads, motivos o evidencias; el backoffice admin local sigue siendo una superficie abierta. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-contabilidad-admin-redaction`. |
| Rama | `codex/stage5-contabilidad-admin-redaction`. |
| Estado | Validacion local completa; pendiente PR, CI, merge y limpieza. |
| Gate esperado | Etapa 5 local diagnostica/parcial, sin declarar cierre de etapa. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no hay worktree tactico sucio, seleccionar el siguiente paquete pequeno, seguro y trazable desde el estado real del repo. |
| Siguiente accion | Redactar refs/payloads contables en admin, cubrir con prueba focal, validar impacto y cerrar con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
