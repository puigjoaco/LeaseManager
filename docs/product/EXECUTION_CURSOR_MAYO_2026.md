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
| Frente activo | `company-accounting-progress`. |
| Fuente exacta | `main` en `0a08304f`, posterior al merge de PR #846. |
| Brecha activa | Falta un auditor objetivo por empresa y ano comercial que responda cuanto avance real existe en contabilidad/renta antes de elegir o cerrar una empresa piloto. |
| Motivo de prioridad | Evitar que el avance siga pareciendo abstracto: el sistema debe poder decir, para una empresa concreta, si tiene configuracion fiscal, 12 cierres, balances, F29, proceso anual, balance anual, RLI/CPT, dossier y export local. |
| Worktree | `D:/Proyectos/LeaseManager-company-accounting-progress`. |
| Rama | `codex/company-accounting-progress`. |
| Estado | Implementacion local validada; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Diagnostico local JSON; no cierra Etapa 5 ni Etapa 6, no lee `.env`, no usa datos reales ni abre SII/EDIG. |
| Estado al cerrar paquete | Commit, PR, CI, merge y limpieza; `main` debe quedar sincronizado. |
| Bloqueos relacionados | La contabilidad real de una primera empresa requiere elegir empresa/ano y autorizar fuentes o snapshot controlado; este auditor solo mide el estado de la DB configurada. |
| Politica de reanudacion | Continuar este worktree hasta cerrar, pausar explicitamente o limpiar. No reabrir goal prompts, EDIG ni paquetes ya mergeados. |
| Siguiente accion | Validar `audit_company_accounting_progress` con tests y registrar evidencia. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
