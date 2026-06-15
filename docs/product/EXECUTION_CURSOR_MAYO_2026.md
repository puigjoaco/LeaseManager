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
| Worktree | Ninguno activo esperado para el frente actual despues de integrar el paquete de regimen soportado; `main` queda como base limpia. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`, con cambios EDIG/eContabilidad y PDFs AT2025 no versionados; no tocar, no stagear y no subir esos PDFs salvo decision explicita. |
| Rama | `main`; abrir `codex/...` solo cuando el siguiente paquete concreto lo requiera. |
| Estado | Auditor empresa/ano disponible por comando y expuesto en Reporting como `contabilidad/progreso-empresa/`; candidatos disponibles en `contabilidad/candidatos-progreso-empresa/`. Para Inmobiliaria Puig AC2024/AT2025 se agrego manifiesto read-only de fuentes externas que separa input contable/soportes de outputs esperados SII y evita prueba circular: Balance General, RLI/CPT/RAI, DDJJ y F22 quedan como comparacion, no como calculo. Pendiente carga controlada a DB local, generacion de artefactos LeaseManager y comparacion contra F22/DDJJ/balance definitivos AT2025. |
| Gate esperado | Cargar candidatos en Reporting, elegir empresa/ano, y ejecutar `audit_company_accounting_progress --empresa-id <id> --fiscal-year <ano>` o consultar Reporting con `empresa_id` y `fiscal_year` contra DB local/controlada o fuente autorizada. El JSON puede guardarse solo bajo `local-evidence/`. |
| Estado al cerrar paquete | Auditor, candidatos, exposicion Reporting y boundary de regimen soportado integrados; no reabrir esos paquetes salvo bug nuevo. |
| Bloqueos relacionados | Sin empresa/ano/fuente no se puede afirmar avance real de una empresa. Registrar esa falta una vez y seguir solo con trabajo seguro que no dependa de datos reales. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes ya mergeados. Si el usuario no entrega empresa/fuente, continuar con el siguiente paquete seguro desbloqueado sin afirmar avance real de una empresa. |
| Siguiente accion | Cerrar `codex/ac2024-mirror-source-bundle` y abrir el siguiente paquete de prueba espejo: loader/control de datos AC2024 hacia DB local, generacion de artefactos LeaseManager AT2025 y comparador contra los documentos finales SII ya respaldados, sin usar esos documentos como input de calculo ni tocar SII real. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
