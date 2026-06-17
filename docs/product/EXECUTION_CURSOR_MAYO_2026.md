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
| Frente activo | Ningun paquete tactico abierto. |
| Fuente exacta | `main` en `5e41d11a`, despues del merge confirmado de PR #898 `codex/stage2-webpay-fail-endpoint`. |
| Brecha activa | Ninguna brecha en curso. La API y backoffice para registrar fallos WebPay controlados quedaron integrados en PR #898. |
| Motivo de prioridad | Mantener el cursor coherente con el estado real evita que una reanudacion recree worktrees eliminados o repita commit, PR, CI, merge y limpieza de paquetes ya cerrados. |
| Worktree | No hay worktree tactico activo para producto. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `main` limpio y sincronizado con `origin/main`; abrir una nueva rama `codex/...` solo cuando se seleccione el siguiente frente. |
| Estado | PR #898 cerrado y validado: focal 4 tests OK, suite impactada 233 tests OK, `manage.py check` OK, `makemigrations --check` OK, gate local Etapa 2 parcial esperado, frontend build/lint OK, acceptance local 1505 tests OK, CI PR OK, Release Gate main OK, branch/worktree tactico eliminado. |
| Gate esperado | El paquete cerrado no declara cierre de Etapa 2; no uso secretos, no toco `.env`, no uso DB historicas, datos reales, snapshots autorizados, Transbank/WebPay real, proveedores externos, backfills, deploys ni integraciones externas. |
| Estado al cerrar paquete | No reabrir prompts de goal, proof espejo AC2024/AT2025, upgrade de acciones CI, matcher CI, guard de cambio de arrendatario, guard de motivo de mensajes, guard de motivo WebPay bloqueado, guard de motivo WebPay fallido, auditoria WebPay fallida ni endpoint/backoffice WebPay fallido salvo fallo nuevo o evidencia contradictoria. |
| Bloqueos relacionados | Ninguno nuevo. Los cierres productivos futuros siguen sujetos a responsable tributario, autorizacion explicita, fuentes reales/controladas vigentes y gates externos cuando corresponda. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Si este cursor contradice el estado real porque nombra una rama/worktree ya eliminado y `main` contiene el merge correspondiente, tratar el paquete como cerrado, corregir el cursor y continuar con el siguiente frente seguro; no recrear el paquete anterior. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Seleccionar el siguiente frente real de producto/arquitectura desde PRD, trazabilidad y stage cards, abrir worktree `codex/...` y avanzar con paquete pequeno, verificable y sin secretos. No crear tareas de goal prompt, no repetir el cierre del proof espejo, no repetir el upgrade CI, no repetir el ajuste de matcher ni reabrir paquetes ya cerrados salvo fallo nuevo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
