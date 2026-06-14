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
| Frente activo | `pilot-company-accounting-selection`. |
| Fuente exacta | `main` en `14e7292c`, posterior al merge de PR #847. |
| Brecha activa | Falta elegir una empresa piloto, ano comercial y fuente controlada/autorizada para medir su avance contable/renta con `audit_company_accounting_progress`. |
| Motivo de prioridad | La infraestructura ya puede responder avance por empresa; el siguiente paso no es seguir abstracto, sino aplicar el auditor a una empresa/ano concretos cuando exista fuente permitida. |
| Worktree | Ninguno activo para producto; `main` queda como base limpia. |
| Rama | `main`; abrir `codex/...` solo cuando el siguiente paquete concreto lo requiera. |
| Estado | PR #847 integrado; auditor empresa/ano disponible. Pendiente seleccion de empresa piloto y fuente de ejecucion. |
| Gate esperado | Ejecutar `audit_company_accounting_progress --empresa-id <id> --fiscal-year <ano>` contra DB local/controlada o fuente autorizada. El JSON puede guardarse solo bajo `local-evidence/`. |
| Estado al cerrar paquete | Cerrado en PR #847, CI remoto verde y mergeado; no reabrir ese paquete salvo bug nuevo. |
| Bloqueos relacionados | Sin empresa/ano/fuente no se puede afirmar avance real de una empresa. Registrar esa falta una vez y seguir solo con trabajo seguro que no dependa de datos reales. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes ya mergeados. Si el usuario no entrega empresa/fuente, continuar con el siguiente paquete seguro o construir UI/reporte para ejecutar el auditor cuando haya fuente. |
| Siguiente accion | Responder al usuario que la primera empresa aun no esta medida/cerrada; pedir una unica seleccion concreta de empresa, ano y fuente, o continuar con preparacion local segura. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
