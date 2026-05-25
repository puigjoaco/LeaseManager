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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 4 - SII/DTE: bloqueo de regimen fiscal no soportado para automatizacion tributaria v1. |
| Fuente exacta | PR #217 (`Guard Stage 4 unsupported fiscal regimes`), commit `38758af`, merge `9af0f18`; `01_Set_Vigente/PRD_CANONICO.md` escenario transversal 16; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `SII`; `docs/product/STAGE_CARDS/ETAPA_4_SII_DTE.md`; `backend/sii`; `backend/core/stage4_sii_readiness.py`; `scripts/run-stage4-readiness-gate.ps1`. |
| Brecha activa | Cerrada localmente: capacidades SII abiertas rechazan empresas con `ConfiguracionFiscalEmpresa` activa fuera del regimen automatizable del v1 y readiness Etapa 4 bloquea snapshots con esa condicion. |
| Motivo de prioridad | Paquete seguro completado sin SII real, certificados, `.env`, secretos, DB historicas, datos reales, snapshots ni integraciones externas. |
| Worktree | Ninguno. Solo debe quedar el worktree principal `D:/Proyectos/LeaseManager`. |
| Rama | `main` sincronizada con `origin/main`. |
| Estado | PR #217 integrado con CI `acceptance` verde; worktree tactico y rama local/remota eliminados. |
| Gate esperado | `scripts/run-stage4-readiness-gate.ps1` sigue en `classification=parcial`, `ready_for_stage4_sii=false` con fuente local; no cierra Etapa 4 sin ambiente SII/fuente autorizada y regla fiscal validada. |
| Estado al cerrar paquete | Preparacion local de Etapa 4 reforzada; cierre real de Etapa 4 sigue pendiente por fuentes/evidencia externas autorizadas. |
| Bloqueos relacionados | Falta ambiente SII real/controlado autorizado, evidencia de ledger, regla fiscal validada y responsable para cierre real de Etapa 4; no bloquea preparacion local ni el siguiente frente seguro. |
| Politica de reanudacion | Si `main` esta limpio y no hay worktrees tacticos sucios, diagnosticar el siguiente frente seguro segun trazabilidad y orden de construccion. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; elegir el siguiente paquete pequeno, seguro y verificable desde trazabilidad/stage cards. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
