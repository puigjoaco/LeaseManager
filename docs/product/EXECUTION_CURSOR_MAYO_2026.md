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
| Frente activo | Etapa 1 - Perfil documental de arrendatario persona natural. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` linea 398: persona natural requiere nacionalidad, estado civil y profesion cuando el documento lo requiera. |
| Brecha activa | `PoliticaFirmaYNotaria` no puede declarar que un contrato principal exige perfil documental de persona natural, y `Contrato`/API/auditor Etapa 1 no validan nacionalidad, estado civil ni profesion del arrendatario persona natural. |
| Motivo de prioridad | Brecha local de Contratos/Documentos trazable al PRD; no requiere `.env`, secretos, DB historica, datos reales, backfills, deploys ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-natural-tenant-document-profile`. |
| Rama | `codex/stage1-natural-tenant-document-profile`. |
| Estado | Validado localmente; listo para PR/CI/merge. |
| Gate esperado | Completado local: focales de Contratos/Documentos/auditor, suite impactada `contratos documentos core.tests_stage1_matrix_audit`, `manage.py check`, `makemigrations --check --dry-run`, readiness local Etapa 1, `npm ci`, `npm run build`, acceptance local, higiene y `git diff --check`. |
| Estado al cerrar paquete | `implementado_sin_evidencia`; no cierra Etapa 1 sin fuente `snapshot_controlado` o `real_autorizado`. |
| Bloqueos relacionados | `BLK-002` solo bloquea cierre evidencial de Etapa 1; no bloquea esta preparacion local. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Desde `main` limpio, seleccionar el siguiente paquete util y seguro segun AGENTS.md, PRD canonico, stage cards y trazabilidad vigente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
