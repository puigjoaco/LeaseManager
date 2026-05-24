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
| Frente activo | Sin paquete tactico abierto; ultimo cierre Etapa 3 - Transferencias internas/intercuenta trazadas. |
| Fuente exacta | PR #199 `Guard Stage 3 internal transfer readiness`, merge `f968b5e`, desde `01_Set_Vigente/PRD_CANONICO.md` lineas 191, 294, 387, 429 y 435; `docs/product/ANEXO_MODELO_OPERATIVO_EXCEL_MAYO_2026.md` lineas 95-96, 171, 181 y 197. |
| Brecha activa | Cerrada localmente: Conciliacion registra un par cargo/abono intercuenta con evidencia, owner origen/destino, responsable, motivo y readiness bloqueante. |
| Motivo de prioridad | Conciliacion distingue cargo bancario, ingreso desconocido y transferencia real antes de alimentar Contabilidad, sin banco real ni datos externos. |
| Worktree | Ninguno activo; solo debe existir `D:/Proyectos/LeaseManager` salvo que se abra el siguiente frente. |
| Rama | `main` sincronizada; sin rama tactica activa. |
| Estado | PR #199 integrado en `main`, CI `acceptance` verde, worktree/rama tactica eliminados. |
| Gate esperado | Sin gate pendiente para este paquete; seleccionar el siguiente frente local seguro desde `main` limpio. |
| Estado al cerrar paquete | `implementado_sin_evidencia`; no cierra Etapa 3 sin fuente `snapshot_controlado` o `real_autorizado`, prueba bancaria, cuadratura y responsables no sensibles. |
| Bloqueos relacionados | `BLK-003` no bloquea esta preparacion local; solo impide cierre evidencial o conexion bancaria real. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Desde `main` limpio, seleccionar el siguiente paquete util y seguro segun AGENTS.md, PRD canonico, stage cards y trazabilidad vigente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
