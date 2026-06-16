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
| Frente activo | `main-clean-next-traceable-front`. |
| Fuente exacta | `main` posterior al merge de PR #860 (`5fecfd2f`) y PR #859 (`2883fa65`). |
| Brecha activa | No hay paquete tactico abierto. La prueba espejo Inmobiliaria Puig AC2024/AT2025 ya tiene gate unico integrado: `audit_annual_tax_mirror_proof` combina fuente/manifiesto, comparador de outputs esperados, readiness Etapa 6 y boundary de seguridad. |
| Motivo de prioridad | Evitar reabrir paquetes cerrados o metatareas. La siguiente decision debe salir del estado real del repo y trazabilidad, no de contexto auxiliar viejo. |
| Worktree | Ningun worktree tactico activo despues de PR #860. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `main` limpio despues de PR #860. Para el proximo paquete no trivial abrir worktree hermano `codex/...` desde `main`. |
| Estado | PR #860 cerro el gate espejo AC2024/AT2025. El gate distingue fuente documentada, arquitectura espejo, comparacion lista, readiness lista, seguridad y revision pendiente; no declara completitud si quedan artefactos con revision responsable. No usa `.env`, SII real, credenciales, DB historica, EDIG ejecutable ni outputs finales como input. |
| Gate esperado | Para AC2024/AT2025 controlado o autorizado, ejecutar `audit_annual_tax_mirror_proof` con salida bajo `local-evidence/` y `--fail-on-incomplete` si se quiere impedir cierre falso. Para otros frentes, elegir el siguiente paquete trazable y proporcional desde `main` limpio. |
| Estado al cerrar paquete | No reabrir prompts de goal, boundary contable de PR #859, selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC ni EDIG como bloqueo general salvo bug nuevo. El gate espejo queda como punto unico para decir preparado, parcial o bloqueado. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Continuar con el siguiente frente trazable desbloqueado desde `main` limpio. Si el usuario quiere convertir AC2024/AT2025 desde prueba controlada a revision con fuente real/autorizada, pedir una unica autorizacion concreta y correr el gate espejo; si no, avanzar por preparacion local segura. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
