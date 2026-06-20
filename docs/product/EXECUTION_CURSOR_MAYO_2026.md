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
  explicita en este cursor o descartar con instruccion segura antes de abrir un frente
  distinto.
- Solo el estado real del repo y este cursor definen la siguiente accion
  operativa.
- El contexto auxiliar no autoriza secretos, no abre gates y no crea tareas
  nuevas salvo solicitud textual actual del usuario.
- Si este cursor nombra una rama/worktree ya cerrados y `main` contiene el
  merge correspondiente, no recrear el paquete anterior: tratarlo como cerrado,
  corregir este cursor y continuar con el siguiente frente seguro.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | Contabilidad Inmobiliaria Puig SpA AC2024/AT2025 y AC2025/AT2026. |
| Fuente exacta | `main` en `8ccf0d9f`, despues del merge confirmado de PR #982 `codex/company-progress-source-bundle`. |
| Brecha activa | Este thread queda dedicado a reconstruir y revisar la contabilidad/renta de Inmobiliaria Puig SpA. AC2024/AT2025 se usa como calibracion contra archivos preparados/presentados por contadora y confirmados por SII. AC2025/AT2026 se produce con evidencia local, auditoria y revision responsable. El tramo preguntas/template/preflight/handoff/materializacion desde handoff, auditoria dry-run de borradores de respuestas responsables, exposicion de `responsible_review_gate` en progreso/reporting y coherencia de `AnnualTaxSourceBundle` en progreso/candidatos ya esta preparado. Sigue sin existir review responsable listo, snapshot ownership controlado ni writer anual listo. |
| Motivo de prioridad | El objetivo no es crear features generales de LeaseManager, sino usar LeaseManager como herramienta de carga, calculo, comparacion y trazabilidad contable/tributaria para la empresa. El avance debe medirse por capas contables listas, observadas o faltantes. |
| Worktree | No hay paquete tactico activo despues de PR #982. No recrear `D:/Proyectos/LeaseManager-company-progress-source-bundle`, `D:/Proyectos/LeaseManager-company-progress-review-boundary` ni sus ramas `codex/...` cerradas. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | Ninguna rama tactica activa. Los paquetes cerrados #972-#982 no deben reabrirse por compactacion, resumen, chat antiguo ni `goal_context`. |
| Estado | PR #980 ya esta mergeado sobre `98a71517`; `audit_company_accounting_progress` y Reporting exponen `responsible_review_gate` para separar avance local de revision responsable, manteniendo en falso handoff responsable, calculo tributario final y presentacion SII. PR #981 sincronizo el cursor post #980. PR #982 endurecio `collect_company_accounting_progress` y `collect_company_accounting_candidates` para contar `AnnualTaxTrialBalance`, workbooks RLI/CPT, dossier y export local solo cuando heredan el mismo `AnnualTaxSourceBundle` congelado del proceso anual. En `main`, `materialize_company_accounting_responsible_answers --handoff-packet-dir <packet> --answers <answers.json> --fail-on-blocking` ya puede validar el handoff packet antes de leer preguntas canonicas y materializar el review solo desde respuestas externas completadas. Tambien existe `audit_company_accounting_responsible_answers_draft --handoff-packet-dir <packet> --answers <answers.json> --require-ready`, que audita un borrador externo de respuestas, reporta blockers/readiness y no escribe `company-accounting-responsible-answers-review.json`. AC2024/AT2025 queda confirmado como prueba espejo `resuelto_confirmado` en evidencia local del 2026-06-17. AC2025/AT2026 tiene RCV/F29/libros/insumos anuales, checklist ownership con indice visual, preguntas/respuestas responsables, workbench privado conectado, consistencia ownership handoff/writer protegida, writer controlado, readiness, mirror/comparacion, workbench, preguntas, respuestas, review package, proof anual, plan de carga con errores de ruta redactados, cursor anti-repeticion, contexto/refs superiores no sensibles en reviews, selector de candidatos coherente con proceso anual trazable, `next_action_ref` superior seguro en respuestas responsables, summaries de workbench sanitizados, auditor de discovery de review, preflight de handoff, handoff packet verificable, materializacion desde handoff, auditor dry-run de respuestas, gate de revision responsable en progreso/reporting y coherencia de source bundle en progreso/candidatos; sigue sin review responsable listo, snapshot ownership controlado ni writer anual listo. |
| Gate esperado | Trabajar desde evidencia local autorizada y artefactos bajo `local-evidence`. No leer `.env`, DB real, SII real, banco, EDIG ejecutable, correos ni integraciones externas sin autorizacion explicita. No declarar presentacion SII, contabilidad final ni calculo tributario final sin evidencia y revision responsable. |
| Estado al cerrar paquete | PR #982 quedo cerrado: `audit_company_accounting_progress --empresa-id <id> --fiscal-year <ano>` y `audit_company_accounting_candidates` no cuentan downstream anual preparado si su `AnnualTaxSourceBundle` no coincide con el del `ProcesoRentaAnual` trazable. Mantiene `responsible_review_gate` como boundary de revision responsable y no leyo `.env`, DB real, SII real, banco, EDIG ejecutable, correos ni integraciones externas. |
| Bloqueos relacionados | AC2024/AT2025 no es bloqueo actual para calibracion arquitectonica; queda como baseline verificado, sin declarar presentacion SII real hecha por LeaseManager. AC2025/AT2026 requiere snapshot ownership/vigencia al 31-12-2025, valores manuales del writer anual, revision responsable, y certificado/cartola formal Banco Chile 31-12-2025 o autorizacion responsable para soporte observado. |
| Politica de reanudacion | No convertir este thread en desarrollo general del software ni en exportadores SII genericos. EDIG Contabilidad/Renta solo es referencia funcional y checklist; no copiar codigo, no ejecutarlo como fuente operativa y no tratarlo como verdad legal. |
| Siguiente accion | Si existe un archivo externo de respuestas responsables redactadas, auditarlo primero con `audit_company_accounting_responsible_answers_draft --handoff-packet-dir <packet> --answers <answers.json> --require-ready`; si queda listo, ejecutar `materialize_company_accounting_responsible_answers --handoff-packet-dir <packet> --answers <answers.json> --fail-on-blocking`. Si no existe ese archivo, no pedirlo en bucle ni inventarlo: elegir solo trabajo local seguro e independiente de la respuesta responsable, o pausar el frente con este estado. No crear PRs para reexplicar el goal ni para repetir paquetes #972-#982. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
