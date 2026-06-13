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
| Frente activo | Etapa 5 Documentos: checksum documental SHA-256 canonico. |
| Fuente exacta | `main` limpio tras mergear PR #771 (`f12ec9cc`); rescue queda pausado fuera de alcance. |
| Brecha activa | `DocumentoEmitido` y `PlantillaDocumental` aceptan variantes no canonicas de checksum como prefijo `sha256:` o mayusculas, aunque stage card/readiness exigen digest SHA-256 canonico. |
| Motivo de prioridad | Endurecer evidencia tecnica documental sin depender de storage real, snapshots autorizados, `.env` ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-doc-checksum-canonical`. |
| Rama | `codex/stage5-doc-checksum-canonical`. |
| Estado | Paquete tactico abierto; no elegir otro frente hasta cerrar, pausar explicitamente o descartar con instruccion segura. |
| Gate esperado | Focal modelo/API/readiness de Documentos; suite impactada `documentos documentos.tests_readiness`; gate local `run-stage5-documents-readiness-gate.ps1` como parcial esperado; acceptance local; CI GitHub acceptance antes de merge. |
| Estado al cerrar paquete | PR #770: focal 2 tests OK; suite impactada Contabilidad/Etapa 5/Reporting 104 tests OK; `manage.py check` OK; migraciones dry-run OK; gate Etapa 5 `classification=parcial`, `ready_for_stage5_contabilidad=false`; `npm ci` 0 vulnerabilidades; build/lint OK; acceptance local 1317 tests OK; CI GitHub acceptance OK; higiene repo y `git diff --check` OK. |
| Bloqueos relacionados | Etapa 5 sigue parcial para cierre evidencial: requiere Conciliacion cerrada y fuente `snapshot_controlado` o `real_autorizado` con evidencia ledger/reportes/responsables. Este paquete solo endurece reglas locales sin fuente real/controlada. |
| Politica de reanudacion | Si no hay worktree tactico de producto abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Implementar checksum canonico, validar modelo/API/readiness/documentacion, abrir PR, esperar CI, mergear y limpiar worktree/rama. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
