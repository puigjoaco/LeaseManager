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
| Frente activo | Cerrar `stage6-rule-source-link`. |
| Fuente exacta | Rama tactica `codex/stage6-rule-source-link` basada en `main` `e7812000` posterior a PR #831. |
| Brecha activa | `stage6-rule-source-link`: enlazar `TaxYearRuleSet` y `TaxCodeMapping` con `AnnualTaxOfficialSource` revisada/aprobada para que reglas y mappings locales DJ1847/RLI/CPT/DDJJ/F22 tengan respaldo oficial/experto trazable. |
| Motivo de prioridad | El registro de fuentes ya existe. Falta que reglas aprobadas y mappings activos no puedan quedar como texto libre sin fuente AT compatible, manteniendo Renta Anual como preparacion supervisada y no como declaracion autonoma. |
| Worktree | `D:/Proyectos/LeaseManager-stage6-rule-source-link` durante el paquete; tras merge debe eliminarse. |
| Rama | `codex/stage6-rule-source-link` durante el paquete; `main` tras merge. |
| Estado | Validacion local completa: modelo/API/snapshot/admin/readiness/tests enlazan reglas y mappings a `AnnualTaxOfficialSource`; falta PR, CI, merge y limpieza. |
| Gate esperado | Mantener `classification=parcial`; no cerrar presentacion anual sin fuente autorizada, formato/certificacion SII vigente, validacion fiscal/oficial, responsable y evidencia no sensible. |
| Estado al cerrar paquete | `stage6-rule-source-link` cerrado. Reglas y mappings anuales quedan respaldados por fuente oficial/experta compatible, sin habilitar presentacion SII ni calculo final autonomo. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Reglas tributarias finales, contribuciones y mapping RLI/CPT/DJ/F22 requieren fuente oficial/experta. |
| Politica de reanudacion | No reabrir EDIG ni goal prompts. Si no hay worktree sucio, continuar por el siguiente frente util que no requiera datos reales, secretos, presentacion SII ni decision tributaria final autonoma. |
| Siguiente accion | Abrir PR, esperar CI, mergear y limpiar. Luego escoger el siguiente frente Stage 6/7 no sensible segun trazabilidad vigente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
