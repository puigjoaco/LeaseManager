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
| Frente activo | Cerrar `stage6-edig-inventory`. |
| Fuente exacta | Rama tactica `codex/stage6-edig-inventory` basada en `main` `9f0a36bb` posterior a PR #828. |
| Brecha activa | `stage6-edig-inventory`: consolidar inventarios EDIG AT2026 ya sanitizados en una matriz EDIG -> LeaseManager que pruebe cobertura funcional y separe brechas externas/oficiales. |
| Motivo de prioridad | El objetivo activo es absorber informacion de EDIG para decidir mejor la renta 2026. Ya existe motor anual propio hasta export local; falta dejar un cruce reproducible que evite volver a mapear EDIG manualmente y que muestre que lo pendiente es fuente oficial/experta, no mas estructura EDIG. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-edig-inventory` durante el paquete; tras merge debe quedar solo el root principal esperado, salvo worktrees no relacionados ya existentes. |
| Rama | `codex/stage6-edig-inventory` durante el paquete; `main` tras merge. |
| Estado | En progreso: `build-edig-at2026-leasemanager-coverage.ps1` genera una matriz local ignorada desde `edig-at2026-static-inventory.json` y `edig-at2026-mdb-schema.json`. La corrida local confirma 291 archivos estaticos, 17 senales funcionales, 7/7 MDB nucleo, 205 tablas y 5.494 columnas observadas, y cobertura propia para configuracion, F29/PPM, parametria AT, RLI/CPT, RAI/SAC, bienes raices, matriz DDJJ/F22, dossier y export local. |
| Gate esperado | Mantener `classification=parcial`; no cerrar presentacion anual sin fuente autorizada, formato/certificacion SII vigente, validacion fiscal/oficial, responsable y evidencia no sensible. |
| Estado al cerrar paquete | `stage6-edig-inventory` cerrado. Queda documentado que EDIG ya fue absorbido como referencia funcional suficiente; el siguiente avance real requiere fuente SII/experta para mapping fiscal, contribuciones, formatos/certificacion o saldos historicos. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Ejecucion EDIG solo en VM/sandbox con datos ficticios. EDIG no es fuente normativa ni runtime de LeaseManager. |
| Politica de reanudacion | No reabrir metatareas administrativas ya cerradas, no repetir el mapeo EDIG ya documentado, no volver a inventariar EDIG salvo solicitud nueva concreta y no reabrir la auditoria de contabilizacion ya cerrada. Si no hay worktree sucio, continuar por el siguiente frente util y seguro del repo; si un gate externo bloquea cierre, registrar una vez y seguir con preparacion local valida. |
| Siguiente accion | Validar script/documentacion, registrar evidencia, abrir PR, mergear y limpiar. Luego continuar por un frente Stage 6/7 que no requiera presentacion SII ni datos reales, o pedir una unica fuente oficial/experta si el siguiente paso fiscal lo exige. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
