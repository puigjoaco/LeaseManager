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
| Frente activo | `codex/company-review-materializer`. |
| Fuente exacta | `main` en `5c147e34`, despues del merge confirmado de PR #933 `codex/stage6-certification-readiness`. |
| Brecha activa | El paquete de revision contable/renta por empresa ya existe como builder, comando de auditoria, API y panel Reporting, pero falta materializarlo como carpeta local verificable para entregar a revision responsable sin convertirlo en contabilidad automatica. |
| Motivo de prioridad | LeaseManager debe preparar informacion ordenada y trazable para contador/revisor/IA asistida, no decidir renta ni contabilidad final. Un materializador canonico permite entregar manifest hasheado, cobertura bancaria/leasing redactada y boundary no autonomo sin leer adjuntos reales ni abrir banco/SII. |
| Worktree | `D:/Proyectos/LeaseManager-company-review-materializer`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/company-review-materializer`. |
| Estado | Paquete en ejecucion: agregar `materialize_company_accounting_review_package`, writer/verificador del manifest `company-accounting-review-package.json`, cobertura de paquete listo, salida no vacia, salida versionada y redaccion de manifiestos sensibles, registrar evidencia y cerrar por PR/CI/merge. |
| Gate esperado | Este paquete usa solo fixtures, SQLite efimero y manifests redactados locales bajo `local-evidence`. No lee `.env`, DB real, documentos reales, correos, adjuntos, banco, SII autenticado, EDIG ejecutable ni integraciones; no declara contabilidad autonoma, calculo tributario final ni presentacion SII. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente contable seguro desde repo limpio. |
| Bloqueos relacionados | Carga productiva real, documentos completos, manifest real redactado/autorizado, respaldo bancario/leasing revisado, formato/certificacion F22/DDJJ aplicable, contenido tributario final y presentacion SII siguen bloqueados por responsable tributario, autorizacion explicita y evidencia no sensible. AT2025 conserva brecha `f22_record_format_2025` hasta evidencia oficial/experta vigente. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable, correos ni integraciones externas sin autorizacion explicita. Un paquete preparado solo habilita revision responsable; nunca contabilidad autonoma ni presentacion automatica. |
| Siguiente accion | En rama tactica abierta: completar validaciones proporcionales, ampliar evidencia, cerrar con commit, PR, CI remoto, merge y limpieza. En `main` post-merge: no reabrir este paquete; tomar el siguiente frente seguro de contabilidad/renta. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
