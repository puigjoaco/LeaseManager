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
| Frente activo | `stage2-webpay-fail-endpoint`. |
| Fuente exacta | `main` en `35719d20`, despues del merge confirmado de PR #897 `codex/cursor-after-webpay-failed-audit`. |
| Brecha activa | La transicion WebPay `preparado` -> `fallido` ya existe como servicio auditable, pero falta exponerla por API/backoffice para operacion local controlada sin proveedor externo. |
| Motivo de prioridad | Etapa 2/WebPay ya tiene preparar, confirmar manualmente y auditoria de fallos; el operador necesita registrar el fallo controlado desde la superficie canonica sin mutar modelos manualmente ni tocar Transbank real. |
| Worktree | Paquete en `D:/Proyectos/10_ACTIVOS/LeaseManager-stage2-webpay-fail-endpoint` con rama `codex/stage2-webpay-fail-endpoint`; al cerrar el PR debe eliminarse. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage2-webpay-fail-endpoint` hasta merge; despues volver a `main` limpio. |
| Estado | Implementacion, evidencia y validaciones locales completas: endpoint, backoffice, pruebas focales, suite impactada, `manage.py check`, `makemigrations --check`, gate local Etapa 2, frontend build/lint y acceptance local pasaron. Falta commit, PR, CI, merge y limpieza. |
| Gate esperado | El paquete no declara cierre de Etapa 2; no usa secretos, no toca `.env`, no usa DB historicas, datos reales, snapshots autorizados, Transbank/WebPay real, proveedores externos, backfills, deploys ni integraciones externas. |
| Estado al cerrar paquete | No reabrir prompts de goal, proof espejo AC2024/AT2025, upgrade de acciones CI, matcher CI, guard de cambio de arrendatario, guard de motivo de mensajes, guard de motivo WebPay bloqueado, guard de motivo WebPay fallido ni auditoria WebPay fallida salvo fallo nuevo o evidencia contradictoria. |
| Bloqueos relacionados | Ninguno nuevo. Los cierres productivos futuros siguen sujetos a responsable tributario, autorizacion explicita, fuentes reales/controladas vigentes y gates externos cuando corresponda. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Cerrar con commit, PR, CI, merge y limpieza. No crear tareas de goal prompt, no repetir el cierre del proof espejo, no repetir el upgrade CI, no repetir el ajuste de matcher ni reabrir paquetes ya cerrados salvo fallo nuevo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
