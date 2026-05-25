# Cursor operativo - mayo 2026

Este archivo fija el frente activo de ejecucion. No reemplaza al PRD, AGENTS,
fuente de verdad, arquitectura, matriz, stage cards, evidencia ni bloqueos. Su
funcion es evitar que una reanudacion, compactacion o `goal_context` convierta
contexto historico en tarea nueva.

## Regla de uso

- Antes de abrir o continuar cambios no triviales, leer este cursor.
- Confirmar el estado real con `git status --short --branch` y
  `git worktree list`.
- Si existe un worktree tactico sucio, se debe terminar, pausar de forma
  explicita en este cursor o descartar con instruccion segura antes de abrir un
  frente distinto.
- El `goal_context`, objetivos persistentes, summaries compactados y
  conversaciones pasadas son contexto auxiliar: no autorizan secretos, no abren
  gates y no ordenan redactar goals.
- Las metatareas marcadas como cerradas no se reabren salvo solicitud textual
  actual del usuario.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | Sin paquete tactico abierto; ultimo cierre Etapa 0 - Compliance guards de politicas de retencion. |
| Fuente exacta | PR #205 `Guard compliance retention policy controls`, commit `ea98b50`, merge `44d5e50`, desde `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `Compliance datos sensibles`, `backend/core/compliance_data_readiness.py`, `scripts/run-compliance-data-readiness-gate.ps1` y `backend/compliance`. |
| Brecha activa | Cerrada localmente: `PoliticaRetencionDatos` bloquea plazo minimo cero, evento de inicio sensible, falta de hold tributario/documental y purga fisica documental/secreto; readiness conserva deteccion de politicas heredadas invalidas sin exponer valores. |
| Motivo de prioridad | Compliance Stage 0 es preparacion base para datos sensibles y puede endurecerse con datos sinteticos/locales sin usar fuentes externas. |
| Worktree | Ninguno activo; solo debe existir `D:/Proyectos/LeaseManager` salvo que se abra el siguiente frente. |
| Rama | `main` sincronizada; sin rama tactica activa. |
| Estado | PR #205 integrado en `main`, CI `acceptance` verde, worktree/rama tactica eliminados. |
| Gate esperado | Sin gate pendiente para este paquete; seleccionar el siguiente frente local seguro desde `main` limpio. |
| Estado al cerrar paquete | `implementado_sin_evidencia`; no cierra `Compliance.DatosPersonalesChile2026` sin fuente autorizada y refs finales. |
| Bloqueos relacionados | Falta fuente `snapshot_controlado` o `real_autorizado`, politica aprobada, responsables, controles, evidencia archivada y validacion legal-operativa no sensibles para cierre real de `Compliance.DatosPersonalesChile2026`; no bloquea preparacion local. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Desde `main` limpio, seleccionar el siguiente paquete util y seguro segun AGENTS.md, PRD canonico, stage cards y trazabilidad vigente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
