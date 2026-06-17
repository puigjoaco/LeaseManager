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
| Frente activo | `stage2-webpay-block-reason`. |
| Fuente exacta | `main` en `4263647f` como base del worktree, mas paquete `codex/stage2-webpay-block-reason` hasta merge. |
| Brecha activa | Intentos WebPay en estado `bloqueado_gate` no deben quedar sin `motivo_bloqueo` operativo, normalizado, no vacio y no sensible. |
| Motivo de prioridad | Etapa 2/WebPay ya redactaba motivos sensibles, pero faltaba impedir o detectar snapshots con bloqueos WebPay sin razon trazable. |
| Worktree | Paquete en `D:/Proyectos/10_ACTIVOS/LeaseManager-stage2-webpay-block-reason` con rama `codex/stage2-webpay-block-reason`; al cerrar el PR debe eliminarse. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage2-webpay-block-reason` hasta merge; despues volver a `main` limpio. |
| Estado | Dominio, readiness, pruebas focales, suite impactada, checks, gate local Etapa 2, frontend build/lint y acceptance local pasaron como preparacion segura. Falta commit, PR, CI, merge y limpieza. |
| Gate esperado | El paquete no declara cierre de Etapa 2; no usa secretos, no toca `.env`, no usa DB historicas, datos reales, snapshots autorizados, proveedores externos, backfills, deploys ni integraciones externas. |
| Estado al cerrar paquete | No reabrir prompts de goal, proof espejo AC2024/AT2025, upgrade de acciones CI, matcher CI, guard de cambio de arrendatario, guard de motivo de mensajes ni este guard de motivo WebPay salvo fallo nuevo o evidencia contradictoria. |
| Bloqueos relacionados | Ninguno nuevo. Los cierres productivos futuros siguen sujetos a responsable tributario, autorizacion explicita, fuentes reales/controladas vigentes y gates externos cuando corresponda. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Cerrar este paquete con commit, PR, CI, merge y limpieza; despues continuar el proyecto desde el siguiente frente real de producto/arquitectura segun PRD, trazabilidad y stage cards. No crear tareas de goal prompt, no repetir el cierre del proof espejo, no repetir el upgrade CI, no repetir el ajuste de matcher ni reabrir paquetes ya cerrados salvo fallo nuevo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
