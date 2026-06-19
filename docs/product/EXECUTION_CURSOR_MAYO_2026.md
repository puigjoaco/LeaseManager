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
| Frente activo | `codex/company-intake-package-handoff`. |
| Fuente exacta | `main` en `744a790f`, despues del merge confirmado de PR #936 `codex/company-document-intake-materializer`. |
| Brecha activa | El intake documental ya se materializa como carpeta local, pero el siguiente flujo contable/renta aun necesita poder reabrir esa carpeta desde disco, verificar hashes/boundary sin depender del manifest original ni del chat, y tomar de ahi el manifiesto bancario/leasing derivado. |
| Motivo de prioridad | La revision contable/renta debe encadenar evidencia portable: intake materializado -> manifiesto bancario/leasing derivado -> paquete contable/renta. Esto evita pegar JSON sueltos, reinyectar contexto o confiar en narrativa previa, y mantiene la frontera de revision responsable. |
| Worktree | `D:/Proyectos/LeaseManager-company-intake-package-handoff`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/company-intake-package-handoff`. |
| Estado | Paquete en ejecucion: agregar verificacion desde disco de `company-document-intake-package`, rechazar tamper/archivos extra/JSON no canonico/boundary roto y permitir que `materialize_company_accounting_review_package` consuma `--document-intake-package-dir` como fuente verificada del manifiesto bancario/leasing. |
| Gate esperado | Este paquete usa solo fixtures, SQLite efimero y paquetes redactados locales bajo `local-evidence`. No lee `.env`, DB real, documentos reales, correos, adjuntos, banco, SII autenticado, EDIG ejecutable ni integraciones; no declara contabilidad autonoma, calculo tributario final ni presentacion SII. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. El siguiente frente debe tomar el handoff verificado o continuar la carga contable/renta segura. |
| Bloqueos relacionados | Carga productiva real, documentos completos reales, manifest real redactado/autorizado, lectura de correos/adjuntos, respaldo bancario/leasing revisado archivo por archivo, formato/certificacion F22/DDJJ aplicable, contenido tributario final y presentacion SII siguen bloqueados por responsable tributario, autorizacion explicita y evidencia no sensible. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable, correos ni integraciones externas sin autorizacion explicita. Un intake preparado solo habilita revision y carga controlada; nunca contabilidad autonoma ni presentacion automatica. |
| Siguiente accion | En rama tactica abierta: completar validaciones proporcionales, ampliar evidencia, cerrar con commit, PR, CI remoto, merge y limpieza. En `main` post-merge: no reabrir este paquete; tomar el siguiente frente seguro de contabilidad/renta. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
