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
| Fuente exacta | `main` en `69c1b2e7`, despues del merge confirmado de PR #944 `codex/stage6-responsible-questions`. |
| Brecha activa | Este thread queda dedicado a reconstruir y revisar la contabilidad/renta de Inmobiliaria Puig SpA. AC2024/AT2025 se usa como calibracion contra archivos preparados/presentados por contadora y confirmados por SII. AC2025/AT2026 se produce con evidencia local, auditoria y revision responsable. |
| Motivo de prioridad | El objetivo no es crear features generales de LeaseManager, sino usar LeaseManager como herramienta de carga, calculo, comparacion y trazabilidad contable/tributaria para la empresa. El avance debe medirse por capas contables listas, observadas o faltantes. |
| Worktree | Paquete tactico actual: `D:/Proyectos/LeaseManager-stage6-responsible-answers` en rama `codex/stage6-responsible-answers`, solo mientras no este mergeado. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-responsible-answers` para validar/materializar respuestas responsables no sensibles al paquete de preguntas contables/renta. |
| Estado | PR #944 ya esta mergeado. AC2024/AT2025 queda confirmado como prueba espejo `resuelto_confirmado` en evidencia local del 2026-06-17: carga controlada, ownership, bienes raices, DDJJ/F22, comparacion y Stage 6 sin blockers, como calibracion de arquitectura contra contadora/SII. AC2025/AT2026 tiene RCV/F29/libros/insumos anuales y checklist ownership con indice visual disponibles, pero sigue sin snapshot ownership controlado ni writer anual listo. Este paquete valida respuestas responsables redactadas contra `company-accounting-responsible-questions.json`, exige refs no sensibles, bloquea texto libre y produce un manifest de handoff verificable. |
| Gate esperado | Trabajar desde evidencia local autorizada y artefactos bajo `local-evidence`. No leer `.env`, DB real, SII real, banco, EDIG ejecutable, correos ni integraciones externas sin autorizacion explicita. No declarar presentacion SII, contabilidad final ni calculo tributario final sin evidencia y revision responsable. |
| Estado al cerrar paquete | El cierre valido de este paquete debe dejar un validador y comando de respuestas responsables desde JSON redactado, con salida solo bajo `local-evidence/` si queda dentro del repo, sin guardar texto libre, nombres, RUTs, rutas locales ni refs sensibles, y con pruebas que cubran cobertura completa, faltantes, refs sensibles, destino limpio y no filtracion. Despues corresponde usar el paquete de preguntas/respuestas junto al workbench privado para completar ownership/vigencia real, Banco Chile/leasing, criterios tributarios y documentos faltantes. |
| Bloqueos relacionados | AC2024/AT2025 no es bloqueo actual para calibracion arquitectonica; queda como baseline verificado, sin declarar presentacion SII real hecha por LeaseManager. AC2025/AT2026 requiere snapshot ownership/vigencia al 31-12-2025, valores manuales del writer anual, revision responsable, y certificado/cartola formal Banco Chile 31-12-2025 o autorizacion responsable para soporte observado. |
| Politica de reanudacion | No convertir este thread en desarrollo general del software ni en exportadores SII genericos. EDIG Contabilidad/Renta solo es referencia funcional y checklist; no copiar codigo, no ejecutarlo como fuente operativa y no tratarlo como verdad legal. |
| Siguiente accion | Cerrar `codex/stage6-responsible-answers` con PR/CI/merge/limpieza. Luego usar el paquete de preguntas/respuestas responsables y el workbench AC2025/AT2026 bajo `local-evidence/`, completar patch ownership/vigencia controlado mediante revision responsable, validarlo, inyectarlo al paquete, seguir con paquete normalizado de carga DB local, writer controlado, espejo anual y comparacion revisable. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
