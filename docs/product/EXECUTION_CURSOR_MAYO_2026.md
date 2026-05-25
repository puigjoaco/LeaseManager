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
| Frente activo | Etapa 0 - Compliance datos sensibles: guards de politicas de retencion. |
| Fuente exacta | `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `Compliance datos sensibles`; `backend/core/compliance_data_readiness.py`; `scripts/run-compliance-data-readiness-gate.ps1`; `backend/compliance`. |
| Brecha activa | El readiness detecta politicas de retencion invalidas, hold faltante y purga fisica restringida, pero `PoliticaRetencionDatos` no bloquea esas incoherencias desde dominio/API. |
| Motivo de prioridad | Es la brecha local segura mas baja del orden vigente: Stage 0 parcial, verificable con datos sinteticos/locales y sin usar `.env`, secretos, datos reales, DB historicas ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-retention-policy-guards`. |
| Rama | `codex/compliance-retention-policy-guards`. |
| Estado | Paquete tactico abierto desde `main` limpio en `50a47d9`; implementacion y validacion en curso. |
| Gate esperado | `scripts/run-compliance-data-readiness-gate.ps1` debe seguir en `classification=parcial`, `ready_for_compliance_data=false` con fuente local; no cierra Compliance sin fuente autorizada y refs finales. |
| Estado al cerrar paquete | Pendiente. |
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
