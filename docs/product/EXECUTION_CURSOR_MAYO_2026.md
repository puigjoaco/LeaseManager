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
| Frente activo | Etapa 0 / Compliance datos sensibles / auditoria de acceso denegado. |
| Fuente exacta | Estado real de `main` en `e2dc1f0` despues de PR #601, matriz, stage card Etapa 0, evidencia y bloqueos vigentes. |
| Brecha activa | `ExportacionContentView` llama `get_export_payload()`, que puede normalizar una exportacion vencida a `expirada`, y luego crea `compliance.exportacion_sensible.access_denied` fuera de una frontera transaccional explicita; si falla la auditoria, puede quedar una mutacion sin traza. |
| Motivo de prioridad | Compliance es la primera fila parcial de la matriz; BLK-010 impide cierre final, pero esta brecha es local, verificable y alinea mutaciones de datos sensibles con auditoria atomica sin usar fuentes externas. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-export-access-denied-atomicity`. |
| Rama | `codex/compliance-export-access-denied-atomicity`. |
| Estado | Paquete tactico implementado y validado localmente; pendiente higiene final, PR, CI remoto, merge y limpieza. |
| Gate esperado | Compliance local debe seguir `classification=parcial`, `ready_for_compliance_data=false`; el paquete mejora preparacion segura, no cierra Compliance.DatosPersonalesChile2026. |
| Estado al cerrar paquete | `ExportacionContentView` ejecuta descarga/denegacion y eventos `accessed`/`access_denied` dentro de una transaccion; si falla la auditoria de acceso denegado, la normalizacion de exportacion vencida a `expirada` se revierte. Validacion local: focal 3 tests OK; impactada Compliance/readiness 101 tests OK; `manage.py check` OK; `makemigrations --check --dry-run --noinput` OK; gate Compliance local `classification=parcial`, `ready_for_compliance_data=false`; `npm ci`, `npm run build`, `npm run lint` OK; acceptance local 1135 tests OK. |
| Bloqueos relacionados | BLK-010 sigue abierto para cierre legal-operativo y fuente autorizada. Este paquete no debe usar `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si este worktree existe, continuar este paquete hasta PR/CI/merge/limpieza antes de abrir otro frente; si aparece sucio, terminar o pausar aqui de forma explicita. |
| Siguiente accion | Ejecutar higiene final, crear PR, esperar CI, mergear, sincronizar `main`, cerrar cursor y limpiar worktree tactico. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
