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
| Frente activo | Etapa 2 - Cobranza/WebPay. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `IntentoPagoWebPay.motivo_bloqueo` no queda clasificado/redactado explicitamente como superficie sensible heredada en API/snapshot/readiness Etapa 2. |
| Motivo de prioridad | Cerrar una fuga local de WebPay sin depender de Transbank real ni credenciales externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-webpay-block-reason-redaction`. |
| Rama | `codex/stage2-webpay-block-reason-redaction`. |
| Estado | Validado localmente; pendiente PR, CI, merge y limpieza. |
| Gate esperado | Etapa 2 local: `classification=parcial`, `ready_for_stage2_cobranza=false`, sin cierre evidencial. |
| Estado al cerrar paquete | Pendiente de registrar merge y dejar el cursor sin paquete activo. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, tomar el siguiente frente seguro desde trazabilidad y abrirlo explicitamente en este cursor. |
| Siguiente accion | Publicar PR, esperar CI, mergear, limpiar worktree y cerrar el cursor. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
