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
| Frente activo | `platform-post-ci-actions-upgrade`. |
| Fuente exacta | `main` posterior al paquete `ci-node24-actions`, que actualiza Release Gate a acciones oficiales GitHub `v6`. |
| Brecha activa | No queda brecha operativa abierta por advertencias Node20 de acciones antiguas en Release Gate. No reabrir este paquete salvo fallo nuevo de CI o cambio oficial de compatibilidad de GitHub Actions. |
| Motivo de prioridad | Mantener el camino de cierre con CI limpia y sin advertencias operativas repetitivas, sin tocar producto ni gates externos. |
| Worktree | No hay worktree tactico activo esperado para este frente despues del merge. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `main`; abrir un nuevo worktree `codex/...` solo para el siguiente cambio no trivial. |
| Estado | Release Gate conserva Python 3.12, Node 22, caches y comandos existentes, pero usa `actions/checkout@v6`, `actions/setup-python@v6` y `actions/setup-node@v6`. El proof espejo AC2024/AT2025 ya quedo documentado como confirmado en modo controlado y no debe reabrirse por reanudacion. |
| Gate esperado | El paquete es operativo de CI: no declara cierre de etapa, no abre SII real, no usa secretos, no toca `.env`, no usa DB historicas, no ejecuta backfills, no despliega ni habilita integraciones externas. |
| Estado al cerrar paquete | No reabrir prompts de goal, el proof espejo AC2024/AT2025 ni el upgrade de acciones CI salvo evidencia nueva contradictoria. |
| Bloqueos relacionados | Ninguno nuevo. Los cierres productivos futuros siguen sujetos a responsable tributario, autorizacion explicita, fuentes reales/controladas vigentes y gates externos cuando corresponda. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Continuar el proyecto desde el siguiente frente real de producto/arquitectura segun PRD, trazabilidad y stage cards. No crear tareas de goal prompt, no repetir el cierre del proof espejo y no repetir el upgrade CI salvo fallo nuevo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
