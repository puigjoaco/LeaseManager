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
| Frente activo | Cerrar `stage6-official-source-gaps`. |
| Fuente exacta | Rama tactica `codex/stage6-official-source-gaps` basada en `main` `48d93ac9` posterior a PR #829. |
| Brecha activa | `stage6-official-source-gaps`: consolidar fuentes SII y brechas oficiales AT2026 para separar preparacion local de formato/certificacion/presentacion o criterio tributario final. |
| Motivo de prioridad | El usuario definio que contabilidad/renta no deben quedar como automatizacion autonoma del business manager. El motor anual ya llega hasta export local; falta fijar una matriz oficial que indique que se puede automatizar mecanicamente y que requiere fuente SII/experta o supervision. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-official-source-gaps` durante el paquete; tras merge debe eliminarse. |
| Rama | `codex/stage6-official-source-gaps` durante el paquete; `main` tras merge. |
| Estado | En progreso: se agrega `RENTA_ANUAL_OFFICIAL_SOURCE_GAPS_AT2026.md` y `build-stage6-official-source-gap-matrix.ps1` para clasificar DTE, F29, DDJJ, DJ1847/RLI/CPT, F22, bienes raices/contribuciones y automatizacion por navegador entre integracion tecnica posible, preparacion local, fuente oficial/experta requerida y presentacion bloqueada. |
| Gate esperado | Mantener `classification=parcial`; no cerrar presentacion anual sin fuente autorizada, formato/certificacion SII vigente, validacion fiscal/oficial, responsable y evidencia no sensible. |
| Estado al cerrar paquete | `stage6-official-source-gaps` cerrado. Queda documentado que DTE es integracion tecnica separada, mientras F29/DDJJ/F22/DJ1847/bienes raices quedan como preparacion local hasta fuente SII/experta, certificacion/formato, responsable y autorizacion. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Reglas tributarias finales, contribuciones y mapping RLI/CPT/DJ/F22 requieren fuente oficial/experta. |
| Politica de reanudacion | No reabrir EDIG ni goal prompts. Si no hay worktree sucio, continuar por el siguiente frente util que no requiera datos reales, secretos, presentacion SII ni decision tributaria final autonoma. |
| Siguiente accion | Validar script/documentacion, registrar evidencia, abrir PR, mergear y limpiar. Luego escoger entre mapping local DJ1847/RLI/CPT con fuente oficial/experta o un frente Stage 7/operativo no sensible. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
