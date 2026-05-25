# Cursor operativo - mayo 2026

Este archivo fija el frente activo de ejecucion. No reemplaza al PRD, AGENTS,
fuente de verdad, arquitectura, matriz, stage cards, evidencia ni bloqueos. Su
funcion es evitar que una reanudacion, compactacion o `goal_context` convierta
contexto historico en tarea nueva.

## Regla de uso

- Antes de abrir o continuar cambios no triviales, leer este cursor.
- Confirmar el estado real con `git status --short --branch` y
  `git worktree list`.
- Si existe un worktree tactico sucio, se debe terminar, pausar de forma
  explicita en este cursor o descartar con instruccion segura antes de abrir un
  frente distinto.
- El `goal_context`, objetivos persistentes, summaries compactados y
  conversaciones pasadas son contexto auxiliar: no autorizan secretos, no abren
  gates y no ordenan redactar goals.
- Las metatareas marcadas como cerradas no se reabren salvo solicitud textual
  actual del usuario.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | Sin paquete tactico abierto; ultimo cierre Etapa 5 - Versiones correctivas de documentos formalizados. |
| Fuente exacta | PR #203 `Guard Stage 5 document corrective versions`, merge `015ab2d`, desde `01_Set_Vigente/PRD_CANONICO.md` lineas 193, 252, 364 y 584; `docs/product/STAGE_CARDS/ETAPA_5_DOCUMENTOS_PDF.md`. |
| Brecha activa | Cerrada localmente: documentos formalizados pueden tener version correctiva trazada con origen formalizado, referencia no sensible, PDF/checksum propios y readiness bloqueante si falta auditoria o validez. |
| Motivo de prioridad | Documentos puede preparar correcciones sin mutar el PDF formalizado ni usar storage real, manteniendo trazabilidad antes de Canales/Reporting. |
| Worktree | Ninguno activo; solo debe existir `D:/Proyectos/LeaseManager` salvo que se abra el siguiente frente. |
| Rama | `main` sincronizada; sin rama tactica activa. |
| Estado | PR #203 integrado en `main`, CI `acceptance` verde, worktree/rama tactica eliminados. |
| Gate esperado | Sin gate pendiente para este paquete; seleccionar el siguiente frente local seguro desde `main` limpio. |
| Estado al cerrar paquete | `implementado_sin_evidencia`; no cierra Etapa 5 Documentos sin fuente `snapshot_controlado` o `real_autorizado`, politica final, prueba PDF controlada y responsable. |
| Bloqueos relacionados | `BLK-005` y fuente documental autorizada no bloquean preparacion local; solo impiden cierre evidencial. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Desde `main` limpio, seleccionar el siguiente paquete util y seguro segun AGENTS.md, PRD canonico, stage cards y trazabilidad vigente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
