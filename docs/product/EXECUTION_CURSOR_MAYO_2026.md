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
| Fuente exacta | `main` posterior a PR #856 y al paquete `build_annual_tax_ownership_evidence_chain`. |
| Brecha activa | Inmobiliaria Puig AC2024/AT2025 tiene contabilidad mensual y comparacion anual controlada, pero la generacion anual sigue bloqueada por falta de `ownership` patrimonial independiente. |
| Motivo de prioridad | Sin snapshot ownership no se puede alimentar RETIROS/DIVIDENDOS ni cerrar la prueba espejo de renta; el avance correcto es reproducir la cadena local de evidencia, revisar/OCR candidatos legales y cargar un snapshot controlado solo si la fuente lo prueba. |
| Worktree | Ningun worktree tactico activo para este frente despues del merge. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir esos PDFs salvo decision explicita. |
| Rama | `main`. Para el siguiente paquete no trivial abrir worktree hermano `codex/...` desde `main` limpio. |
| Estado | Auditor empresa/ano disponible por CLI y Reporting; candidatos empresa/ano disponibles. Para Inmobiliaria Puig AC2024/AT2025 estan integrados manifiesto read-only, plan de carga, template, auditor de paquete, draft de valores, writer DB local, run anual controlado, comparador de cobertura/identidad/valores/semantica DDJJ/F22 y la cadena reproducible `build_annual_tax_ownership_evidence_chain`. Balance, RLI/CPT/RAI, DDJJ y F22 finales son comparacion, no calculo. La prueba espejo queda parcial: `ownership_source_present=false`, candidatos societarios existen como soporte/revision, template `ownership` queda con `participants=[]` y `ready_for_controlled_db_load=false` hasta revision/OCR y aprobacion responsable. |
| Gate esperado | Ejecutar `build_annual_tax_ownership_evidence_chain --source-root <external-read-only-source> --company-ref inmobiliaria-puig --commercial-year 2024 --tax-year 2025 --f29-no-declaration-month 2 --f29-no-declaration-month 12` para rehidratar evidencia local bajo `local-evidence/`, revisar/OCR candidatos, completar `ownership.participants` solo con fuente suficiente y luego auditar/aplicar el paquete controlado contra DB local/controlada autorizada. |
| Estado al cerrar paquete | PR #856 ya fue cerrado y no debe reabrirse. El paquete de cadena ownership evita depender de artefactos perdidos al borrar worktrees y deja la proxima accion reproducible desde `main`. |
| Bloqueos relacionados | Sin fuente societaria independiente, OCR/revision y aprobacion responsable no se puede afirmar ownership ni cerrar Etapa 6. Registrar el bloqueo una vez y continuar con trabajo seguro que no invente socios, RUTs ni porcentajes. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente, continuar con preparacion local segura y trazable. |
| Siguiente accion | Rehidratar la cadena ownership en `local-evidence/`, revisar/OCR los candidatos visuales, completar el template solo con evidencia suficiente, auditar el paquete con `audit_annual_tax_controlled_package_readiness` y recien despues ejecutar writer/mirror contra DB local/controlada. Luego continuar con bienes raices, respaldo tributario y revision responsable de artefactos Etapa 6. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
