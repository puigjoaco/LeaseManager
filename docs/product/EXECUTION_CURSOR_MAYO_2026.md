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
| Frente activo | Sin paquete tactico abierto tras integrar `stage6-monthly-tax-facts`. |
| Fuente exacta | `main` posterior a `stage6-monthly-tax-facts`: Etapa 6 ya materializa `TaxYearRuleSet`/`TaxCodeMapping`, `AnnualTaxSourceBundle` y `MonthlyTaxFact` como capas propias del motor anual, sin copiar EDIG ni abrir SII real. |
| Brecha activa | Pendiente elegir siguiente frente seguro desde el estado real del repositorio. Para Renta Anual, el siguiente paquete propio recomendado es `stage6-rli-cpt-skeleton` desde `docs/product/RENTA_ANUAL_AT2026_ENGINE_BLUEPRINT.md`. |
| Motivo de prioridad | Evitar que compactaciones o contexto auxiliar reabran paquetes ya cerrados, repitan goals/prompts o pierdan el orden trazable desde el repo. |
| Worktree | N/A. |
| Rama | `main`. |
| Estado | Paquete `stage6-monthly-tax-facts` cerrado: `MonthlyTaxFact` normaliza hechos mensuales por empresa/ano/mes desde cierre aprobado, obligaciones, F29 opcional, distribuciones de arriendo y liquidacion de empresa; API/snapshot/admin redactan refs/payloads y readiness bloquea procesos anuales sin doce hechos mensuales normalizados o con resumen desalineado. |
| Gate esperado | Antes del proximo paquete, confirmar `git status --short --branch`, `git worktree list` y seleccionar una brecha real que no dependa de secretos, EDIG ejecutado, SII real, banco real ni datos productivos. |
| Estado al cerrar paquete | Etapa 6 cuenta con parametria tributaria anual, fuente anual congelada y hechos mensuales anualizables; aun no hay formulas finales RLI/CPT/RAI/SAC/F22 ni presentacion SII. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Ejecucion EDIG solo en VM/sandbox con datos ficticios. |
| Politica de reanudacion | No reabrir conversaciones de goal, no repetir el mapeo EDIG ya documentado, no volver a inventariar EDIG salvo solicitud nueva concreta y no reabrir la auditoria de contabilizacion ya cerrada. Si no hay worktree sucio, continuar por el siguiente frente util y seguro del repo; si un gate externo bloquea cierre, registrar una vez y seguir con preparacion local valida. |
| Siguiente accion | Diagnosticar estado real y avanzar `stage6-rli-cpt-skeleton` como siguiente capa anual propia si no existe un frente mas prioritario en el cursor real. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
