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
| Frente activo | Cerrar `stage6-dossier-boundary-flags`. |
| Fuente exacta | Rama tactica `codex/stage6-dossier-boundary-flags` basada en `main` `f1c7a9cc` posterior a PR #835. |
| Brecha activa | `stage6-dossier-boundary-flags`: `AnnualTaxDossier.resumen_dossier` ya declara que no hay calculo final ni presentacion SII, pero el dominio/readiness no clasifican explicitamente snapshots heredados que intenten marcar `official_format`, `sii_submission`, `sii_submission_attempted` o `final_tax_calculation`. |
| Motivo de prioridad | Refuerza la decision de arquitectura: LeaseManager prepara expediente anual revisable; no automatiza ni decide renta final desde el core. |
| Worktree | `D:/Proyectos/LeaseManager-stage6-dossier-boundary-flags` durante el paquete; tras merge debe eliminarse. |
| Rama | `codex/stage6-dossier-boundary-flags` durante el paquete; `main` tras merge. |
| Estado | Validacion local completa: focal, suite impactada, `manage.py check`, migraciones dry-run, gate Stage 6, frontend y acceptance pasaron; falta PR, CI, merge y limpieza. |
| Gate esperado | Mantener `classification=parcial`; no cerrar presentacion anual sin fuente autorizada, formato/certificacion SII vigente, validacion fiscal/oficial, responsable y evidencia no sensible. |
| Estado al cerrar paquete | `stage6-dossier-boundary-flags` cerrado. El dossier anual preparado no acepta ni deja pasar flags/payloads que declaren formato oficial, presentacion SII o calculo fiscal final autonomo. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Reglas tributarias finales, contribuciones y mapping RLI/CPT/DJ/F22 requieren fuente oficial/experta. |
| Politica de reanudacion | No reabrir EDIG ni goal prompts. Si no hay worktree sucio, continuar por el siguiente frente util que no requiera datos reales, secretos, presentacion SII ni decision tributaria final autonoma. |
| Siguiente accion | Abrir PR, esperar CI, mergear y limpiar. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
