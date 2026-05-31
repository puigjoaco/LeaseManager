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
| Frente activo | Etapa 2 / Canales: alinear servicio `prepare_message()` con el guard de dominio que exige gate del mismo canal del mensaje. |
| Fuente exacta | Estado real de `main` en `6e12d45` tras cerrar cursor de Compliance, `docs/product/STAGE_CARDS/ETAPA_2_COBRANZA_CANALES.md`, trazabilidad y readiness vigentes. |
| Brecha activa | `MensajeSaliente.clean()` rechaza mensajes preparados/enviados cuyo `canal_mensajeria.canal` no coincide con `MensajeSaliente.canal`, pero `prepare_message()` no valida ese cruce antes de persistir y puede crear un mensaje preparado desde una llamada interna con gate de otro canal. |
| Motivo de prioridad | Es una brecha local verificable en el siguiente frente seguro: evita bypass de servicio sobre el gate de Canales sin depender de Email/WebPay/WhatsApp reales. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-message-gate-channel-guard`. |
| Rama | `codex/stage2-message-gate-channel-guard`. |
| Estado | Implementacion y validaciones locales completadas; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Tests focales de Canales/readiness, suite impactada Stage 2/Canales/Cobranza, `manage.py check`, `makemigrations --check --dry-run --noinput`, readiness local Etapa 2 como `classification=parcial`, frontend build/lint segun impacto, higiene repo y `git diff --check`. |
| Estado al cerrar paquete | Focal Canales 4 tests OK; suite impactada Canales/Stage2 143 tests OK; `manage.py check` OK; `makemigrations --check --dry-run --noinput` sin cambios; readiness local Etapa 2 `classification=parcial`, `ready_for_stage2_cobranza=false`; `npm ci`, `npm run build`, `npm run lint` OK; acceptance local 1124 tests OK; higiene repo y `git diff --check` OK. |
| Bloqueos relacionados | Etapa 2 sigue parcial para cierre externo por falta de fuente autorizada y pruebas controladas de Email/WebPay. Este paquete no requiere `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Implementar guard en servicio, cubrirlo con tests y validar sin usar integraciones externas. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
