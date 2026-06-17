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
| Frente activo | `codex/stage6-export-artifact-contracts`. |
| Fuente exacta | `main` en `db94db6c`, despues del merge confirmado de PR #899 `codex/cursor-post-merge-state`. |
| Brecha activa | Etapa 6 necesita bajar la frontera oficial/exportable a contratos estructurales dentro de `AnnualTaxExport`: cada DDJJ/F22 exportable local debe tener contrato con fuente, hash, medio, revision y flags que mantengan `official_format=false`, `sii_submission=false` y `final_tax_calculation=false`. |
| Motivo de prioridad | La prueba espejo ya confirmo artefactos comparables; la siguiente capa segura es explicitar que el export local conoce sus artefactos exportables sin confundirlos con archivo SII oficial/certificado. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-export-artifact-contracts`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-export-artifact-contracts`. |
| Estado | Paquete en curso. Main estaba limpio y sincronizado antes de abrirlo; se elimino el worktree limpio ya mergeado `codex/cursor-post-merge-state`. |
| Gate esperado | Este paquete no declara cierre de Etapa 6 ni genera archivo oficial SII. Solo agrega contratos estructurales al export local controlado y readiness bloqueante si faltan o intentan abrir formato oficial/presentacion/calculo final. |
| Estado al cerrar paquete | No reabrir proof espejo AC2024/AT2025 ni paquetes ya cerrados salvo fallo nuevo o evidencia contradictoria. |
| Bloqueos relacionados | Formato/certificacion F22, DDJJ y presentacion SII siguen bloqueados por fuente oficial/certificacion vigente, responsable tributario y autorizacion explicita. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Si este cursor contradice el estado real porque nombra una rama/worktree ya eliminado y `main` contiene el merge correspondiente, tratar el paquete como cerrado, corregir el cursor y continuar con el siguiente frente seguro; no recrear el paquete anterior. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Implementar y validar contratos de artefactos exportables en `AnnualTaxExport`, documentar evidencia y cerrar por PR/CI/merge/limpieza si pasa. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
