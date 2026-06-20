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
| Fuente exacta | `main` en `9ae99736`, despues del merge confirmado de PR #974 `codex/stage6-responsible-handoff-packet`. |
| Brecha activa | Este thread queda dedicado a reconstruir y revisar la contabilidad/renta de Inmobiliaria Puig SpA. AC2024/AT2025 se usa como calibracion contra archivos preparados/presentados por contadora y confirmados por SII. AC2025/AT2026 se produce con evidencia local, auditoria y revision responsable. Ya existe un handoff packet verificable para agrupar preguntas + template; el tramo actual corrige el preflight para que las copias canonicas dentro del packet no cuenten como multiples handoffs distintos. |
| Motivo de prioridad | El objetivo no es crear features generales de LeaseManager, sino usar LeaseManager como herramienta de carga, calculo, comparacion y trazabilidad contable/tributaria para la empresa. El avance debe medirse por capas contables listas, observadas o faltantes. |
| Worktree | Paquete tactico actual: `D:/Proyectos/LeaseManager-stage6-handoff-preflight-packet-aware` en rama `codex/stage6-handoff-preflight-packet-aware`, solo mientras no este mergeado. Si `main` ya contiene el merge de este paquete y el worktree/rama no existen, no recrearlo. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-handoff-preflight-packet-aware` para hacer que el preflight deduplique preguntas/template equivalentes por hash cuando existen artefactos sueltos y copias dentro del handoff packet. |
| Estado | PR #974 ya esta mergeado y con `acceptance` remoto exitoso sobre `9ae99736`. En `main` se materializo un handoff packet local AC2025/AT2026 con 4 preguntas y 4 respuestas pendientes. El preflight anterior cuenta dos manifests fisicos de preguntas/template por las copias internas del packet; este paquete corrige el readiness efectivo para que eso no bloquee falsamente como multiples handoffs distintos. AC2024/AT2025 queda confirmado como prueba espejo `resuelto_confirmado` en evidencia local del 2026-06-17. AC2025/AT2026 tiene RCV/F29/libros/insumos anuales, checklist ownership con indice visual, preguntas/respuestas responsables, workbench privado conectado, consistencia ownership handoff/writer protegida, writer controlado, readiness, mirror/comparacion, workbench, preguntas, respuestas, review package, proof anual, plan de carga con errores de ruta redactados, cursor anti-repeticion, contexto/refs superiores no sensibles en reviews, selector de candidatos coherente con proceso anual trazable, `next_action_ref` superior seguro en respuestas responsables, summaries de workbench sanitizados, auditor de discovery de review, preflight de handoff y handoff packet verificable; sigue sin review responsable listo, snapshot ownership controlado ni writer anual listo. |
| Gate esperado | Trabajar desde evidencia local autorizada y artefactos bajo `local-evidence`. No leer `.env`, DB real, SII real, banco, EDIG ejecutable, correos ni integraciones externas sin autorizacion explicita. No declarar presentacion SII, contabilidad final ni calculo tributario final sin evidencia y revision responsable. |
| Estado al cerrar paquete | El cierre valido de este paquete debe dejar `audit_company_accounting_responsible_handoff_preflight` contando candidatos fisicos pero deduplicando readiness por hash semantico de preguntas/template, de modo que un handoff packet materializado no produzca `multiple_ready_question_packets` ni `multiple_ready_answer_templates` por sus copias internas. Debe mantener `ready_for_responsible_answer_completion=true` y `ready_for_responsible_decision_handoff=false` cuando solo falta review responsable. Debe no leer documentos reales, no escribir DB y no declarar revision productiva, ownership final, calculo tributario final ni presentacion SII. |
| Bloqueos relacionados | AC2024/AT2025 no es bloqueo actual para calibracion arquitectonica; queda como baseline verificado, sin declarar presentacion SII real hecha por LeaseManager. AC2025/AT2026 requiere snapshot ownership/vigencia al 31-12-2025, valores manuales del writer anual, revision responsable, y certificado/cartola formal Banco Chile 31-12-2025 o autorizacion responsable para soporte observado. |
| Politica de reanudacion | No convertir este thread en desarrollo general del software ni en exportadores SII genericos. EDIG Contabilidad/Renta solo es referencia funcional y checklist; no copiar codigo, no ejecutarlo como fuente operativa y no tratarlo como verdad legal. |
| Siguiente accion | Cerrar `codex/stage6-handoff-preflight-packet-aware` con PR/CI/merge/limpieza. Si `main` ya contiene ese merge y el worktree/rama no existen, no repetirlo: ejecutar `audit_company_accounting_responsible_handoff_preflight --require-answer-template-ready` desde `main` y confirmar que los duplicados fisicos quedan informativos, no bloqueantes. El siguiente paso externo sigue siendo completar `company-accounting-responsible-answers.template.json` como respuesta responsable redactada y luego ejecutar `materialize_company_accounting_responsible_answers --fail-on-blocking`. Si ya existe exactamente un review responsable listo, materializar el workbench con `--require-responsible-answers-ready`, completar patch ownership/vigencia controlado al 31-12-2025, validarlo, inyectarlo al paquete, seguir con paquete normalizado de carga DB local, writer controlado, espejo anual y comparacion revisable. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
