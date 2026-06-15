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
| Fuente exacta | `main` posterior a PR #850 y al paquete de boundary de regimen soportado para progreso contable/renta. |
| Brecha activa | Falta elegir una empresa piloto, ano comercial y fuente controlada/autorizada para medir su avance contable/renta con el auditor disponible por CLI o Reporting. |
| Motivo de prioridad | El sistema ya puede listar candidatos empresa/ano desde senales internas, mostrar si el regimen fiscal es automatizable en v1 y responder avance por empresa; el siguiente paso no es seguir abstracto, sino aplicar el auditor a un candidato concreto cuando exista fuente permitida. |
| Worktree | Activo tactico `D:/Proyectos/10_ACTIVOS/LeaseManager-ac2024-mirror-source-bundle` en rama `codex/ac2024-mirror-source-bundle`; `main` queda como base limpia. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`, con cambios EDIG/eContabilidad y PDFs AT2025 no versionados; no tocar, no stagear y no subir esos PDFs salvo decision explicita. |
| Rama | `codex/ac2024-mirror-source-bundle`; cerrar con PR/CI/merge cuando el paquete quede validado. |
| Estado | Auditor empresa/ano disponible por comando y expuesto en Reporting como `contabilidad/progreso-empresa/`; candidatos disponibles en `contabilidad/candidatos-progreso-empresa/`. Para Inmobiliaria Puig AC2024/AT2025 se agrego manifiesto read-only, plan de carga controlada, template de paquete normalizado, writer DB local `apply_annual_tax_controlled_db_load` y auditor `audit_annual_tax_controlled_package_readiness`. Balance General, RLI/CPT/RAI, DDJJ y F22 quedan como comparacion, no como calculo. El template real bajo `local-evidence/` confirma refs mensuales completas, libros anuales presentes y F29 febrero/diciembre `no_aplica`. El auditor real confirma `complete_12_months=true`, `missing_months=[]`, `comparison_targets_present=true`, `ready_for_db_writer=false`, `missing_paths_count=132`, `invalid_paths_count=0`. La prueba espejo no puede escribir DB ni generar AT2025 hasta completar valores normalizados desde libros anuales, F29/meses sin declaracion y remuneraciones, mas comparador contra outputs esperados. |
| Gate esperado | Cargar candidatos en Reporting, elegir empresa/ano, y ejecutar `audit_company_accounting_progress --empresa-id <id> --fiscal-year <ano>` o consultar Reporting con `empresa_id` y `fiscal_year` contra DB local/controlada o fuente autorizada. El JSON puede guardarse solo bajo `local-evidence/`. |
| Estado al cerrar paquete | Auditor, candidatos, exposicion Reporting y boundary de regimen soportado integrados; no reabrir esos paquetes salvo bug nuevo. |
| Bloqueos relacionados | Sin empresa/ano/fuente no se puede afirmar avance real de una empresa. Registrar esa falta una vez y seguir solo con trabajo seguro que no dependa de datos reales. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes ya mergeados. Si el usuario no entrega empresa/fuente, continuar con el siguiente paquete seguro desbloqueado sin afirmar avance real de una empresa. |
| Siguiente accion | Validar suite impactada del paquete `codex/ac2024-mirror-source-bundle`, cerrar PR/CI/merge, y despues continuar con la completitud de valores del template por parser/carga manual controlada para `annual_ledger_input`, `f29_support_input` y `payroll_support`; luego aplicar writer DB local y construir comparador contra outputs esperados sin usarlos como input. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
