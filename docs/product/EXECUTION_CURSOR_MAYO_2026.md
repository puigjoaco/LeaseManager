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
| Frente activo | `ac2024-architecture-proof-gate`. |
| Fuente exacta | `main` posterior al merge de PR #859 (`2883fa65`), con boundary explicito para progreso contable/renta y el paquete AC2024 de selector anual, ownership, respaldo tributario, bienes raices y Stage 6 controlado. |
| Brecha activa | Falta un gate unico que conteste si Inmobiliaria Puig AC2024/AT2025 tiene fuente documentada, arquitectura espejo, comparacion de outputs esperados, readiness Etapa 6 y boundary de seguridad sin convertir outputs finales en input. |
| Motivo de prioridad | Evita seguir mirando senales separadas y evita cierres falsos: el resultado debe distinguir fuente lista, arquitectura lista, comparacion lista, readiness lista, seguridad y revision pendiente. |
| Worktree | Paquete actual en `D:/Proyectos/10_ACTIVOS/LeaseManager-ac2024-architecture-proof-gate`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/ac2024-architecture-proof-gate`, rebasada sobre `main` limpio `2883fa65`. |
| Estado | Implementado `audit_annual_tax_mirror_proof` y comando `audit_annual_tax_mirror_proof`: combinan manifiesto/fuente, comparador de outputs esperados, readiness Etapa 6 y boundary de seguridad. El test sintetico demuestra que, si hay artefactos generados con revision pendiente, el gate queda `classification=parcial` y `ready_for_objective_completion=false` aunque la fuente y seguridad esten OK. No usa `.env`, SII real, credenciales, DB historica, EDIG ejecutable ni outputs finales como input. |
| Gate esperado | Ejecutar focal `core.tests_annual_tax_mirror_proof`, suite impactada de comparator/mirror/readiness, `manage.py check`, `makemigrations --check --dry-run`, higiene y diff. Si se aplica contra fuente real/autorizada futura, escribir salida solo bajo `local-evidence/` y usar `--fail-on-incomplete` para impedir cierre falso. |
| Estado al cerrar paquete | No reabrir prompts de goal, boundary contable de PR #859, selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC ni EDIG como bloqueo general salvo bug nuevo. El gate espejo queda como punto unico para decir preparado, parcial o bloqueado. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Completar validacion/documentacion/PR/CI/merge de este gate; despues volver a `main` limpio y continuar el siguiente frente trazable desbloqueado o pedir una unica autorizacion concreta si el usuario quiere revision con fuente real/autorizada. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
