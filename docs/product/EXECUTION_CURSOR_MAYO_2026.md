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
| Frente activo | Etapa 2 / CobranzaActiva / WebPay - auditoria de confirmacion manual. |
| Fuente exacta | Estado real de `main` en `8766fbd` despues de PR #597, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | Readiness no clasifica intentos WebPay `confirmado_manual` heredados sin evento `cobranza.webpay_intento.confirmed_manually` completo, con actor y metadata alineada contra `external_ref`, `pago_mensual_id` y `fecha_pago_webpay`. |
| Motivo de prioridad | La stage card exige que la confirmacion manual WebPay conserve auditoria dedicada en la misma transaccion; el servicio la crea, pero el gate local aun no detecta snapshots heredados o mutaciones directas sin esa traza. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-webpay-confirm-audit-readiness`. |
| Rama | `codex/stage2-webpay-confirm-audit-readiness`. |
| Estado | Implementado y validado localmente; pendiente empaquetar PR, esperar CI, mergear y limpiar worktree. |
| Gate esperado | Etapa 2 local debe seguir `classification=parcial`, `ready_for_stage2_cobranza=false`; el paquete mejora preparacion segura, no cierra etapa. |
| Estado al cerrar paquete | Validacion local OK: focal 6 tests, impactada 190 tests, `manage.py check`, `makemigrations --check --dry-run --noinput`, gate Etapa 2 `classification=parcial`, `npm ci`, `npm run build`, `npm run lint`, acceptance local 1133 tests y `git diff --check`. |
| Bloqueos relacionados | Etapa 2 sigue parcial para cierre real por fuente autorizada y pruebas Email/WebPay controladas. Este paquete no debe usar `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si este worktree existe, continuar este paquete hasta PR/CI/merge/limpieza antes de abrir otro frente; si aparece sucio, terminar o pausar aqui de forma explicita. |
| Siguiente accion | Ejecutar higiene final, abrir PR, esperar CI, mergear, sincronizar `main`, cerrar cursor y eliminar worktree tactico. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
