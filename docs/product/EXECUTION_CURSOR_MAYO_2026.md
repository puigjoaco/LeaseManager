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
| Frente activo | Cerrar `stage6-official-tax-source-registry`. |
| Fuente exacta | Rama tactica `codex/stage6-official-tax-source-registry` basada en `main` `61787799` posterior a PR #830. |
| Brecha activa | `stage6-official-tax-source-registry`: materializar en backend el registro de fuentes oficiales/experta AT2026 que respalda reglas, mappings, DDJJ/F22 y dossier sin usar documentos/credenciales reales. |
| Motivo de prioridad | La matriz oficial ya separa preparacion local de cierre tributario. Falta un registro operacional que permita asociar fuentes SII/experta a reglas y mappings de forma versionada, hasheada, revisable y redactada. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-official-tax-source-registry` durante el paquete; tras merge debe eliminarse. |
| Rama | `codex/stage6-official-tax-source-registry` durante el paquete; `main` tras merge. |
| Estado | Validado localmente: `AnnualTaxOfficialSource` agrega modelo, migracion, API/snapshot/admin redactados y readiness bloqueante para fuentes AT invalidas o sensibles. |
| Gate esperado | Mantener `classification=parcial`; no cerrar presentacion anual sin fuente autorizada, formato/certificacion SII vigente, validacion fiscal/oficial, responsable y evidencia no sensible. |
| Estado al cerrar paquete | `stage6-official-tax-source-registry` cerrado. Queda disponible un registro local de fuentes oficiales/experta para apoyar siguientes paquetes DJ1847/RLI/CPT/DDJJ/F22 sin convertirlos en presentacion SII ni calculo final autonomo. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Reglas tributarias finales, contribuciones y mapping RLI/CPT/DJ/F22 requieren fuente oficial/experta. |
| Politica de reanudacion | No reabrir EDIG ni goal prompts. Si no hay worktree sucio, continuar por el siguiente frente util que no requiera datos reales, secretos, presentacion SII ni decision tributaria final autonoma. |
| Siguiente accion | Abrir PR, esperar CI, mergear y limpiar. Luego escoger entre mapping local DJ1847/RLI/CPT respaldado en `AnnualTaxOfficialSource` o un frente Stage 7/operativo no sensible. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
