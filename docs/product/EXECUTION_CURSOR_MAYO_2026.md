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
| Frente activo | Etapa 2 - fallback WhatsApp: alerta y evento trazable desde servicio. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Los mensajes WhatsApp bloqueados/fallidos podian quedar cubiertos por una `ManualResolution` de fallback sin actor trazable ni evento dedicado; readiness aceptaba alertas heredadas demasiado debiles. |
| Motivo de prioridad | Brecha local y verificable de Etapa 2; fortalece fallback critico sin abrir WhatsApp, Email, WebPay ni proveedores externos. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-whatsapp-fallback-service-audit`. |
| Rama | `codex/stage2-whatsapp-fallback-service-audit`. |
| Estado | Validado localmente; falta PR/CI/merge/limpieza. |
| Gate esperado | `classification=parcial`, `ready_for_stage2_cobranza=false` en gate local Etapa 2; no declara cierre sin fuente autorizada, Etapa 1, Email/WebPay controlados y responsables. |
| Estado al cerrar paquete | Debe quedar integrado en `main` con `prepare_message()` creando fallback WhatsApp con actor y evento dedicado, readiness bloqueando fallback heredado sin actor/evento/motivo alineado, evidencia y trazabilidad actualizadas. |
| Bloqueos relacionados | Ninguno para este paquete. |
| Politica de reanudacion | Confirmar `git status --short --branch` y `git worktree list`; si solo existe `main` limpio, seleccionar el siguiente frente trazable. |
| Siguiente accion | Continuar este worktree hasta validacion, evidencia, PR, CI, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
