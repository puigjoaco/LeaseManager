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
| Frente activo | Sin paquete tactico abierto. |
| Fuente exacta | `main` despues del paquete `stage6-tax-year-ruleset`: Etapa 6 ya materializa `TaxYearRuleSet` y `TaxCodeMapping` como parametria anual propia versionada por ano tributario/regimen, sin copiar EDIG ni abrir SII real. |
| Brecha activa | Pendiente elegir el siguiente frente seguro desde el estado real del repositorio. Para Renta Anual, el siguiente paquete propio debe avanzar `stage6-source-bundle` o normalizador anual RLI/CPT/RAI/SAC/DDJJ/F22 desde `docs/product/RENTA_ANUAL_AT2026_ENGINE_BLUEPRINT.md`, plan trazable, stage cards y gates. |
| Motivo de prioridad | Evitar que compactaciones o contexto auxiliar reabran paquetes ya cerrados, repitan goals/prompts o pierdan el orden trazable desde el repo. |
| Worktree | N/A. |
| Rama | `main`. |
| Estado | Paquete `stage6-tax-year-ruleset` cerrado: modelos, migracion, API/snapshot/admin, servicio de generacion anual, readiness y bootstrap demo exigen regla anual aprobada y mappings activos trazables antes de preparar ProcesoRentaAnual/DDJJ/F22. EDIG sigue protegido como referencia funcional no normativa. |
| Gate esperado | Antes del proximo paquete, confirmar `git status --short --branch`, `git worktree list` y seleccionar una brecha real que no dependa de secretos, EDIG ejecutado, SII real, banco real ni datos productivos. |
| Estado al cerrar paquete | Etapa 6 cuenta con parametria tributaria anual propia: `TaxYearRuleSet` aprobado por AT/regimen, `TaxCodeMapping` activo por destino, resumen anual con version/hash/conteos no sensibles, y readiness que bloquea reglas ausentes, sin mapping o invalidas. No hay formulas finales ni presentacion SII. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Ejecucion EDIG solo en VM/sandbox con datos ficticios. |
| Politica de reanudacion | No reabrir conversaciones de goal, no repetir el mapeo EDIG ya documentado, no volver a inventariar EDIG salvo solicitud nueva concreta y no reabrir la auditoria de contabilizacion ya cerrada. Si no hay worktree sucio, continuar por el siguiente frente util y seguro del repo; si un gate externo bloquea cierre, registrar una vez y seguir con preparacion local valida. |
| Siguiente accion | Diagnosticar estado real y avanzar el siguiente paquete tecnico trazable permitido por la arquitectura, idealmente `stage6-source-bundle` o normalizador anual si no existe un frente mas prioritario en el cursor real. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
