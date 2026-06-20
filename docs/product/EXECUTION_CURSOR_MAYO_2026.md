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
| Fuente exacta | `main` en `82cdc6ff`, despues del merge confirmado de PR #975 `codex/stage6-handoff-preflight-packet-aware`. |
| Brecha activa | Este thread queda dedicado a reconstruir y revisar la contabilidad/renta de Inmobiliaria Puig SpA. AC2024/AT2025 se usa como calibracion contra archivos preparados/presentados por contadora y confirmados por SII. AC2025/AT2026 se produce con evidencia local, auditoria y revision responsable. Ya existe un handoff packet verificable y el preflight ya deduplica sus copias canonicas; el tramo actual reduce el riesgo del siguiente paso externo permitiendo materializar el review de respuestas responsables desde un handoff packet verificado como fuente de preguntas. |
| Motivo de prioridad | El objetivo no es crear features generales de LeaseManager, sino usar LeaseManager como herramienta de carga, calculo, comparacion y trazabilidad contable/tributaria para la empresa. El avance debe medirse por capas contables listas, observadas o faltantes. |
| Worktree | Paquete tactico actual: `D:/Proyectos/LeaseManager-stage6-answers-from-handoff` en rama `codex/stage6-answers-from-handoff`, solo mientras no este mergeado. Si `main` ya contiene el merge de este paquete y el worktree/rama no existen, no recrearlo. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-answers-from-handoff` para que `materialize_company_accounting_responsible_answers` pueda usar `--handoff-packet-dir` como fuente verificada de preguntas y un archivo `--answers` aparte como respuestas completadas. |
| Estado | PR #975 ya esta mergeado y con `acceptance` remoto exitoso sobre `82cdc6ff`. En `main` el preflight confirma 2 candidatos fisicos de preguntas/template, 1 efectivo por hash, `ready_for_responsible_answer_completion=true`, `ready_for_responsible_decision_handoff=false` e issues esperados `responsible_answers.review_missing` y `responsible_handoff.review_pending`. AC2024/AT2025 queda confirmado como prueba espejo `resuelto_confirmado` en evidencia local del 2026-06-17. AC2025/AT2026 tiene RCV/F29/libros/insumos anuales, checklist ownership con indice visual, preguntas/respuestas responsables, workbench privado conectado, consistencia ownership handoff/writer protegida, writer controlado, readiness, mirror/comparacion, workbench, preguntas, respuestas, review package, proof anual, plan de carga con errores de ruta redactados, cursor anti-repeticion, contexto/refs superiores no sensibles en reviews, selector de candidatos coherente con proceso anual trazable, `next_action_ref` superior seguro en respuestas responsables, summaries de workbench sanitizados, auditor de discovery de review, preflight de handoff y handoff packet verificable; sigue sin review responsable listo, snapshot ownership controlado ni writer anual listo. |
| Gate esperado | Trabajar desde evidencia local autorizada y artefactos bajo `local-evidence`. No leer `.env`, DB real, SII real, banco, EDIG ejecutable, correos ni integraciones externas sin autorizacion explicita. No declarar presentacion SII, contabilidad final ni calculo tributario final sin evidencia y revision responsable. |
| Estado al cerrar paquete | El cierre valido de este paquete debe dejar `materialize_company_accounting_responsible_answers --handoff-packet-dir <packet> --answers <answers.json>` validando el handoff packet antes de leer sus preguntas canonicas, materializando `company-accounting-responsible-answers-review.json` solo desde respuestas externas completadas y manteniendo salida sin rutas crudas. Debe no leer documentos reales, no escribir DB y no declarar revision productiva, ownership final, calculo tributario final ni presentacion SII. |
| Bloqueos relacionados | AC2024/AT2025 no es bloqueo actual para calibracion arquitectonica; queda como baseline verificado, sin declarar presentacion SII real hecha por LeaseManager. AC2025/AT2026 requiere snapshot ownership/vigencia al 31-12-2025, valores manuales del writer anual, revision responsable, y certificado/cartola formal Banco Chile 31-12-2025 o autorizacion responsable para soporte observado. |
| Politica de reanudacion | No convertir este thread en desarrollo general del software ni en exportadores SII genericos. EDIG Contabilidad/Renta solo es referencia funcional y checklist; no copiar codigo, no ejecutarlo como fuente operativa y no tratarlo como verdad legal. |
| Siguiente accion | Cerrar `codex/stage6-answers-from-handoff` con PR/CI/merge/limpieza. Si `main` ya contiene ese merge y el worktree/rama no existen, no repetirlo: completar un archivo externo de respuestas responsables redactadas y ejecutar `materialize_company_accounting_responsible_answers --handoff-packet-dir <packet> --answers <answers.json> --fail-on-blocking`. Si ya existe exactamente un review responsable listo, materializar el workbench con `--require-responsible-answers-ready`, completar patch ownership/vigencia controlado al 31-12-2025, validarlo, inyectarlo al paquete, seguir con paquete normalizado de carga DB local, writer controlado, espejo anual y comparacion revisable. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
