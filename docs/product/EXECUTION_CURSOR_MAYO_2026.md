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
| Fuente exacta | `main` en `d29b91f9`, despues del merge confirmado de PR #939 `codex/inmo-puig-accounting-cursor`. |
| Brecha activa | Este thread queda dedicado a reconstruir y revisar la contabilidad/renta de Inmobiliaria Puig SpA. AC2024/AT2025 se usa como calibracion contra archivos preparados/presentados por contadora y confirmados por SII. AC2025/AT2026 se produce con evidencia local, auditoria y revision responsable. |
| Motivo de prioridad | El objetivo no es crear features generales de LeaseManager, sino usar LeaseManager como herramienta de carga, calculo, comparacion y trazabilidad contable/tributaria para la empresa. El avance debe medirse por capas contables listas, observadas o faltantes. |
| Worktree | Paquete tactico actual: `D:/Proyectos/LeaseManager-stage6-ownership-review-handoff` en rama `codex/stage6-ownership-review-handoff`, solo mientras no este mergeado. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-ownership-review-handoff` para cerrar el handoff ownership hacia paquete controlado. Si `main` ya contiene `annual-tax-ownership-review-handoff.v1` y el worktree tactico no existe, tratar este paquete como cerrado y continuar desde el siguiente frente seguro. |
| Estado | PR #939 ya esta mergeado. AC2024/AT2025 queda confirmado como prueba espejo `resuelto_confirmado` en evidencia local del 2026-06-17: carga controlada, ownership, bienes raices, DDJJ/F22, comparacion y Stage 6 sin blockers, como calibracion de arquitectura contra contadora/SII. AC2025/AT2026 tiene RCV/F29/libros/insumos anuales y checklist ownership con indice visual disponibles, pero sigue sin snapshot ownership controlado ni writer anual listo. Este paquete agrega un handoff `ownership_review` redactado para arrastrar ese estado hacia el template/readiness del paquete controlado sin reemplazar `package.ownership`. |
| Gate esperado | Trabajar desde evidencia local autorizada y artefactos bajo `local-evidence`. No leer `.env`, DB real, SII real, banco, EDIG ejecutable, correos ni integraciones externas sin autorizacion explicita. No declarar presentacion SII, contabilidad final ni calculo tributario final sin evidencia y revision responsable. |
| Estado al cerrar paquete | El cierre valido de este paquete debe dejar el handoff ownership incorporado al template/readiness, validado y documentado, manteniendo `ready_for_annual_generation=false` mientras falte `package.ownership`. Despues corresponde completar patch ownership/vigencia controlado y continuar con paquete normalizado AC2025/AT2026. |
| Bloqueos relacionados | AC2024/AT2025 no es bloqueo actual para calibracion arquitectonica; queda como baseline verificado, sin declarar presentacion SII real hecha por LeaseManager. AC2025/AT2026 requiere snapshot ownership/vigencia al 31-12-2025, valores manuales del writer anual, revision responsable, y certificado/cartola formal Banco Chile 31-12-2025 o autorizacion responsable para soporte observado. |
| Politica de reanudacion | No convertir este thread en desarrollo general del software ni en exportadores SII genericos. EDIG Contabilidad/Renta solo es referencia funcional y checklist; no copiar codigo, no ejecutarlo como fuente operativa y no tratarlo como verdad legal. |
| Siguiente accion | Cerrar `codex/stage6-ownership-review-handoff` con PR/CI/merge/limpieza. Si ya esta cerrado en `main`, avanzar AC2025/AT2026 completando patch ownership/vigencia controlado, luego paquete normalizado de carga DB local, writer controlado, espejo anual y comparacion revisable. Juntar dudas concretas para Joaquin sobre ownership, Banco Chile/leasing, criterios tributarios y documentos faltantes. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
