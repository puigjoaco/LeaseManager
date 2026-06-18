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
| Frente activo | `codex/stage6-company-review-package`. |
| Fuente exacta | `main` en `8fa70bf5`, despues del merge confirmado de PR #924 `codex/stage6-presentation-review-bundle`. |
| Brecha activa | Etapa 6 ya puede generar y consolidar candidatos F22/DDJJ/export local, y tambien puede medir avance contable por empresa y cobertura bancaria/leasing por manifiesto redactado, pero falta una superficie unica de revision por empresa/ano que conecte ambos controles antes de tratar una contabilidad como lista para revision productiva. |
| Motivo de prioridad | Inmobiliaria Puig no debe avanzar solo por artefactos anuales internos: la revision real/controlada necesita cruzar progreso contable/renta con respaldo documental bancario/leasing sin leer adjuntos reales ni versionar evidencia sensible. |
| Worktree | `D:/Proyectos/LeaseManager-stage6-company-review-package`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-company-review-package`. |
| Estado | Paquete en ejecucion solo mientras exista la rama/worktree tactico sin merge: agregar auditor/command de paquete de revision contable-renta por empresa/ano, combinando `audit_company_accounting_progress` y `audit_company_bank_support_coverage` con salida redactada. Si este texto esta en `main` despues del merge del PR de este frente, tratar el paquete como cerrado y no repetirlo. |
| Gate esperado | Este paquete no lee documentos reales, correos, adjuntos, `.env`, DB real ni SII. Solo exige manifiesto redactado y DB local/controlada para decidir si una empresa/ano esta lista para revision responsable; no declara contabilidad final ni presentacion SII. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente seguro desde repo limpio. |
| Bloqueos relacionados | Carga productiva real, documentos completos, formato/certificacion F22/DDJJ, codigo autorizado por SII, contenido tributario final y presentacion SII siguen bloqueados por responsable tributario, autorizacion explicita, formato/certificacion vigente aplicable y evidencia no sensible. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. La aprobacion para presentacion solo puede existir como decision y evidencia trazables no sensibles; nunca como salida automatica del motor local. |
| Siguiente accion | En rama tactica abierta: completar validaciones proporcionales, registrar evidencia, cerrar con commit, PR, CI remoto, merge y limpieza. En `main` post-merge: no reabrir este paquete; tomar el siguiente frente seguro desde repo limpio. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
