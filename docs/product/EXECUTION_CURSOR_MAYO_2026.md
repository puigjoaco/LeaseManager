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
| Frente activo | Etapa 5 / Documentos - readiness especifico de comprobante notarial. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` reglas de expediente documental, firma/notaria y evidencia; `docs/product/STAGE_CARDS/ETAPA_5_DOCUMENTOS_PDF.md`; matriz de trazabilidad. |
| Brecha activa | El dominio/API bloquea formalizaciones con comprobante notarial invalido, pero el readiness documental no distingue snapshots heredados con comprobante notarial de tipo incorrecto, otro expediente o estado no permitido. |
| Motivo de prioridad | Fortalece el gate documental antes de Canales/SII/Reporting sin usar storage real, documentos productivos, secretos ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-notary-receipt-readiness`. |
| Rama | `codex/stage5-notary-receipt-readiness`. |
| Estado | Implementado y validado localmente; pendiente PR, CI, merge y limpieza. |
| Gate esperado | Tests focales Documentos/API/readiness, suite impactada Documentos/readiness, `manage.py check`, migraciones dry-run, readiness local Documentos, frontend build, acceptance local, CI remoto. |
| Estado al cerrar paquete | Integrar paquete por PR/CI/merge y limpiar worktree/rama; no reabrir este frente despues del merge. |
| Bloqueos relacionados | No requiere proveedores externos, datos reales, `.env`, DB historicas ni integraciones. |
| Politica de reanudacion | Si esta rama existe, terminar solo PR/CI/merge/limpieza. Si ya no existe, no reabrir este frente y seleccionar el siguiente paquete operativo desde el estado real. |
| Siguiente accion | Ejecutar higiene final, abrir PR, esperar CI, mergear y limpiar. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
