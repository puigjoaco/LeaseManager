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
| Frente activo | Sin paquete tactico abierto; ultimo cierre Etapa 0 - Compliance bloqueo de exportaciones categoria secreto. |
| Fuente exacta | PR #207 `Guard compliance secret category exports`, commit `77db16f`, merge `36f92df`, desde `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `Compliance datos sensibles`, `backend/compliance`, `backend/core/compliance_data_readiness.py` y `scripts/run-compliance-data-readiness-gate.ps1`. |
| Brecha activa | Cerrada localmente: `ExportacionSensible.full_clean` y `prepare_sensitive_export` bloquean nuevas exportaciones con categoria `secreto`; readiness conserva deteccion de exportaciones heredadas de secreto sin exponer payloads ni referencias. |
| Motivo de prioridad | Compliance Stage 0 es preparacion base para datos sensibles y puede endurecerse con datos sinteticos/locales sin usar fuentes externas. |
| Worktree | Ninguno activo; solo debe existir `D:/Proyectos/LeaseManager` salvo que se abra el siguiente frente. |
| Rama | `main` sincronizada; sin rama tactica activa. |
| Estado | PR #207 integrado en `main`, CI `acceptance` verde, worktree/rama tactica eliminados. |
| Gate esperado | Sin gate pendiente para este paquete; seleccionar el siguiente frente local seguro desde `main` limpio. |
| Estado al cerrar paquete | `implementado_sin_evidencia`; no cierra `Compliance.DatosPersonalesChile2026` sin fuente autorizada y refs finales. |
| Bloqueos relacionados | Falta fuente `snapshot_controlado` o `real_autorizado`, politica aprobada, responsables, controles, evidencia archivada y validacion legal-operativa no sensibles para cierre real de `Compliance.DatosPersonalesChile2026`; no bloquea preparacion local. |
| Politica de reanudacion | Si no hay paquete abierto, partir desde `main` limpio y elegir el siguiente frente trazable por AGENTS.md, PRD canonico, stage cards, matriz y evidencia. |
| Siguiente accion | Seleccionar el siguiente paquete util y seguro desde `main` limpio. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
