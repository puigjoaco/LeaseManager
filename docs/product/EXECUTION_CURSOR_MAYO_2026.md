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
| Fuente exacta | Estado real de `main` tras integrar el paquete Etapa 1 / Operacion / Django admin / redaccion de datos bancarios directos, PRD canonico, `docs/product/STAGE_CARDS/ETAPA_1_DATOS_REALES.md`, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | Ninguna. Ultimo paquete cerrado: `CuentaRecaudadoraAdmin` ya no expone ni busca `numero_cuenta` ni `titular_rut` crudos, y `MandatoOperacionAdmin` ya no muestra cuentas recaudadoras mediante labels con numero bancario. |
| Motivo de prioridad | La ficha de Etapa 1 exige inspeccion operativa redactada y cambios auditados; el paquete deja cerrada la superficie local de datos bancarios directos en admin. |
| Worktree | Ninguno tras merge. El laboratorio usado por este paquete fue `D:/Proyectos/LeaseManager-stage1-operation-admin-account-redaction`. |
| Rama | `main` limpio tras merge; laboratorio cerrado: `codex/stage1-operation-admin-account-redaction`. |
| Estado | Paquete de Operacion/admin cerrado en este frente; luego de merge, el cursor queda libre para diagnosticar el siguiente frente seguro. |
| Gate esperado | No aplica a paquete cerrado. El siguiente paquete debe definir gates proporcionales antes de editar. |
| Estado al cerrar paquete | Etapa 1 / Operacion / admin de datos bancarios directos: focal 1 test OK, suite impactada 172 tests OK, `manage.py check`, migraciones dry-run, readiness local Etapa 1 diagnostico no evidencial OK, `npm ci`, `npm run build`, `npm run lint`, acceptance local 1115 tests OK, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. No requiere `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Diagnosticar el siguiente frente seguro desde el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
