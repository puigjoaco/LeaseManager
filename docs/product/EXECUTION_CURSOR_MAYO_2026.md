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
| Frente activo | `stage6-enterprise-registers` en implementacion. |
| Fuente exacta | Worktree tactico `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-enterprise-registers` desde `main` `09b71057`, posterior a `stage6-rli-cpt-skeleton`. |
| Brecha activa | Materializar registros empresariales RAI/SAC/retiros/dividendos desde RLI/CPT y participaciones activas, con hash, snapshot/API/admin redactados y readiness bloqueante. |
| Motivo de prioridad | Consolidar la capa intermedia anual contabilidad -> renta antes de DDJJ/F22/export, sin calculo fiscal final autonomo. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-enterprise-registers`. |
| Rama | `codex/stage6-enterprise-registers`. |
| Estado | Implementado y validado localmente: modelos, migracion, servicio, API/snapshot/admin, readiness, tests y documentacion para registros empresariales. Pendiente PR/CI/merge/limpieza. |
| Gate esperado | CI remoto acceptance antes de merge. Mantener `classification=parcial`; no cerrar presentacion anual sin fuente autorizada, validacion fiscal/oficial, responsable y evidencia no sensible. |
| Estado al cerrar paquete | Etapa 6 cuenta con RAI/SAC/retiros/dividendos trazables sobre RLI/CPT y participaciones activas; aun faltaran seccion bienes raices, matriz DDJJ/F22 final, dossier/export/presentacion SII y decision tributaria autonoma. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Ejecucion EDIG solo en VM/sandbox con datos ficticios. |
| Politica de reanudacion | No reabrir conversaciones de goal, no repetir el mapeo EDIG ya documentado, no volver a inventariar EDIG salvo solicitud nueva concreta y no reabrir la auditoria de contabilizacion ya cerrada. Si no hay worktree sucio, continuar por el siguiente frente util y seguro del repo; si un gate externo bloquea cierre, registrar una vez y seguir con preparacion local valida. |
| Siguiente accion | Completar validacion, PR, CI, merge y limpieza de `stage6-enterprise-registers`; despues recomendar `stage6-real-estate-section` si no aparece brecha mas prioritaria. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
