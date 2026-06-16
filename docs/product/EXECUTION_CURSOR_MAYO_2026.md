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
| Frente activo | `compliance-retention-baseline-gate`. |
| Fuente exacta | worktree `D:/Proyectos/10_ACTIVOS/LeaseManager-compliance-retention-baseline-gate`, creado sobre `main` `b6bbed0a`. |
| Brecha activa | El gate local de `Compliance.DatosPersonalesChile2026` debe poder preparar explicitamente la linea base canonica de politicas de retencion demo/local sin carga manual, pero sin mutar fuentes evidenciales ni cerrar Compliance por diagnostico local. |
| Motivo de prioridad | La matriz deja Compliance en `parcial` por falta de fuente y aprobaciones finales, pero hay trabajo seguro: hacer reproducible el baseline local de retencion para que las brechas restantes sean refs finales/fuente autorizada, no ausencia accidental de politicas canonicas en DB local. |
| Worktree | Continuar/cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-compliance-retention-baseline-gate`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. La junction `D:/Proyectos/LeaseManager-company-progress-candidates` apunta a una ruta nueva no registrada por `git worktree list`; no trabajar ahi hasta que exista y Git la registre. |
| Rama | `codex/compliance-retention-baseline-gate`; al cerrar, PR/CI/merge y limpiar worktree. |
| Estado | En desarrollo validado localmente: `run-compliance-data-readiness-gate.ps1 -BootstrapDemoPolicies` ejecuta `bootstrap_demo_compliance_policies` solo para `local`/`fixture`/`demo`, rechaza `snapshot_controlado`/`real_autorizado`, exige SQLite de archivo bajo `local-evidence/`, deja cinco politicas canonicas activas y elimina los issues locales de politicas/holds faltantes. |
| Gate esperado | Compliance debe seguir `classification=parcial` con `ready_for_compliance_data=false` cuando la fuente es `local`, `fixture` o `demo`. Este paquete no autoriza datos reales, no sustituye aprobaciones legales/operativas y no cierra `BLK-010`. |
| Estado al cerrar paquete | No reabrir paquetes Stage 6 ya mergeados ni prompts de goal. El cierre esperado es PR/CI/merge del wrapper y tests de Compliance, dejando el siguiente frente real definido por la primera brecha segura de la matriz/cursor, no por autorizaciones repetidas. |
| Bloqueos relacionados | `BLK-010` sigue abierto: el cierre real de Compliance exige `snapshot_controlado` o `real_autorizado` con `SourceLabel`, `AuthorizationRef`, `PolicyApprovalRef`, `ResponsibleRef`, `ControlsEvidenceRef`, `ArchivedEvidenceRef` y `LegalReviewRef` no sensibles. Este bloqueo impide cierre, no preparacion local segura. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, integraciones externas ni rutas de worktree no registradas por Git sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Completar documentacion, validacion amplia, PR/CI/merge y limpiar `compliance-retention-baseline-gate`; luego continuar con el siguiente frente seguro segun matriz/cursor. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
