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
| Frente activo | Sin paquete tactico abierto posterior a integrar este paquete. |
| Fuente exacta | Estado real de `main` base `62f9adb`, PRD canonico, `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`, stage cards, evidencia y bloqueos vigentes. |
| Brecha activa | Cerrada por este paquete: `prepare_sensitive_export()` y `revoke_export()` persistian la exportacion preparada/revocada, pero los eventos `compliance.exportacion_sensible.prepared` y `revoked` quedaban en la vista HTTP. Una falla posterior de auditoria podia dejar exportaciones sensibles sin evento dedicado. |
| Motivo de prioridad | Las exportaciones sensibles son superficie de datos personales/financieros; preparar o revocar una exportacion no debe persistir sin auditoria trazable dentro de la misma transaccion. |
| Worktree | Ninguno tras merge. Durante la ejecucion se uso `D:/Proyectos/LeaseManager-compliance-export-audit-service`. |
| Rama | `main` tras merge; laboratorio usado: `codex/compliance-export-audit-service`. |
| Estado | Paquete Etapa 0 / Compliance / auditoria atomica de exportaciones sensibles preparado para integracion: implementacion, pruebas locales y gates proporcionales OK. |
| Gate esperado | Focal Compliance, suite `compliance` y readiness de datos sensibles, `manage.py check`, `makemigrations --check --dry-run`, gate local Compliance, acceptance local, higiene repo y `git diff --check`. |
| Estado al cerrar paquete | Etapa 0 / Compliance / auditoria atomica de exportaciones sensibles: validacion local OK con focal 5 tests, suite `compliance` + readiness datos sensibles 95 tests, `manage.py check`, migraciones dry-run, gate local Compliance parcial esperado, `npm ci` 0 vulnerabilidades, `npm run build`, `npm run lint`, acceptance 1105 tests, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Sin bloqueo externo nuevo; Compliance de datos sensibles no se declara cerrado sin politica aprobada, responsables, controles, evidencia archivada, validacion legal-operativa y fuente autorizada. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Diagnosticar el siguiente frente seguro desde el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
