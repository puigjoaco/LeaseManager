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
| Frente activo | Etapa 4 SII: validacion de dominio antes de persistir transiciones tributarias avanzadas. |
| Fuente exacta | `main` limpio tras mergear PR #773 (`396b6ea1`); rescue queda pausado fuera de alcance. |
| Brecha activa | Las transiciones manuales de estado SII revalidan gate y refs, pero deben ejecutar `full_clean()` sobre el artefacto actualizado antes de persistir estados externos/avanzados para impedir que un snapshot heredado ya invalido sea mutado por API. |
| Motivo de prioridad | Alinear servicio/API con readiness Etapa 4: un artefacto heredado con capacidad SII de familia incorrecta debe bloquearse antes de guardar la transicion, no solo ser detectado despues por el auditor. |
| Worktree | `D:/Proyectos/LeaseManager-stage4-sii-status-validation`. |
| Rama | `codex/stage4-sii-status-validation`. |
| Estado | Validacion local completa; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Etapa 4 debe seguir `classification=parcial`, `ready_for_stage4_sii=false`; no se cierra SII sin fuente `snapshot_controlado` o `real_autorizado`, evidencia de ambiente/regla fiscal/responsable y dependencia contable. |
| Estado al cerrar paquete | Focal 3 tests OK; suite impactada SII/readiness 78 tests OK; `manage.py check` OK; migraciones dry-run OK; gate Etapa 4 `classification=parcial`, `ready_for_stage4_sii=false`; `npm ci` 0 vulnerabilidades; build/lint OK; acceptance local 1322 tests OK; higiene repo y `git diff --check` OK. |
| Bloqueos relacionados | Etapa 4 sigue parcial para cierre evidencial: requiere ambiente/fuente autorizada, regla fiscal validada, evidencia Etapa 5 y responsables. Este paquete solo endurece rutas locales de estado sin conectar SII. |
| Politica de reanudacion | Continuar este worktree hasta cerrar, pausar explicitamente o limpiar. No reabrir metatareas del goal ni solicitar secretos; si falta fuente externa, registrar una vez y seguir trabajo local seguro. |
| Siguiente accion | Cerrar con commit, PR, CI, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
