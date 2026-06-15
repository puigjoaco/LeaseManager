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
| Fuente exacta | `main` posterior a PR #847/#848 y al paquete de Reporting de progreso contable por empresa. |
| Brecha activa | Falta elegir una empresa piloto, ano comercial y fuente controlada/autorizada para medir su avance contable/renta con el auditor disponible por CLI o Reporting. |
| Motivo de prioridad | El sistema ya puede listar candidatos empresa/ano desde senales internas y responder avance por empresa; el siguiente paso no es seguir abstracto, sino aplicar el auditor a un candidato concreto cuando exista fuente permitida. |
| Worktree | Ninguno activo para producto una vez integrado el paquete de candidatos/progreso Reporting; `main` queda como base limpia. |
| Rama | `main`; abrir `codex/...` solo cuando el siguiente paquete concreto lo requiera. |
| Estado | Auditor empresa/ano disponible por comando y expuesto en Reporting como `contabilidad/progreso-empresa/`; candidatos disponibles en `contabilidad/candidatos-progreso-empresa/`. Pendiente seleccion de empresa piloto y fuente de ejecucion. |
| Gate esperado | Cargar candidatos en Reporting, elegir empresa/ano, y ejecutar `audit_company_accounting_progress --empresa-id <id> --fiscal-year <ano>` o consultar Reporting con `empresa_id` y `fiscal_year` contra DB local/controlada o fuente autorizada. El JSON puede guardarse solo bajo `local-evidence/`. |
| Estado al cerrar paquete | Auditor, candidatos y exposicion Reporting integrados; no reabrir esos paquetes salvo bug nuevo. |
| Bloqueos relacionados | Sin empresa/ano/fuente no se puede afirmar avance real de una empresa. Registrar esa falta una vez y seguir solo con trabajo seguro que no dependa de datos reales. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes ya mergeados. Si el usuario no entrega empresa/fuente, continuar con el siguiente paquete seguro desbloqueado sin afirmar avance real de una empresa. |
| Siguiente accion | Cargar candidatos, elegir una empresa piloto, ano comercial y fuente permitida; ejecutar el auditor por CLI o Reporting y responder con porcentaje, siguiente fase bloqueante y faltantes concretos. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
