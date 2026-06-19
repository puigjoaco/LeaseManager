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
| Frente activo | `codex/ownership-visual-index-checklist`. |
| Fuente exacta | `main` en `45d1e98e`, despues del merge confirmado de PR #937 `codex/company-intake-package-handoff`. |
| Brecha activa | Inmobiliaria Puig AC2025/AT2026 ya tiene template ownership y un indice visual local con candidatos societarios renderizados, pero `build_annual_tax_ownership_review_checklist` solo contaba el paquete visual canonico y dejaba esos candidatos como no renderizados. |
| Motivo de prioridad | Ownership/vigencia es bloqueo real para cargar el paquete anual y liberar RLI/CPT/RAI/SAC, DJ1948/F22 o dossier controlado. El checklist debe reflejar evidencia visual existente sin copiar rutas, nombres, RUTs ni archivos sensibles al repo. |
| Worktree | `D:/Proyectos/LeaseManager-ownership-visual-index-checklist`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/ownership-visual-index-checklist`. |
| Estado | Paquete en ejecucion: permitir que el checklist ownership consuma `ownership-visual-index.v1`, contar paginas renderizadas ya existentes y conservar salida redactada. En la evidencia local AC2025/AT2026 el checklist queda con 10 candidatos y 10 renderizados, pero `ready_for_controlled_db_load=false` por falta de patch validado de participantes. |
| Gate esperado | Este paquete usa fixtures, SQLite efimero y artefactos locales bajo `local-evidence`. No lee `.env`, DB real, SII real, banco, EDIG ejecutable, correos ni integraciones; no declara ownership final, contabilidad final, calculo tributario final ni presentacion SII. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. El siguiente frente debe completar el patch/snapshot ownership controlado o seguir la carga contable/renta con estado observado. |
| Bloqueos relacionados | Snapshot ownership final, participantes vigentes al 31-12-2025, Banco Chile certificado/cartola formal 31-12-2025, formato/certificacion F22/DDJJ aplicable, contenido tributario final y presentacion SII siguen bloqueados por responsable tributario, autorizacion explicita y evidencia no sensible. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable, correos ni integraciones externas sin autorizacion explicita. Un checklist observado solo habilita revision/OCR responsable; nunca genera socios, porcentajes, calculo final ni presentacion automatica. |
| Siguiente accion | En rama tactica abierta: completar validaciones proporcionales, ampliar evidencia, cerrar con commit, PR, CI remoto, merge y limpieza. En `main` post-merge: no reabrir este paquete; tomar el patch ownership controlado o la carga contable/renta observada como siguiente frente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
