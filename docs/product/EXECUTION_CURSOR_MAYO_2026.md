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
| Frente activo | `stage6-real-estate-values-draft`. |
| Fuente exacta | worktree `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-real-estate-values-draft`, creado sobre `main` `2251a143`. |
| Brecha activa | La prueba espejo AC2024/AT2025 necesita convertir `real_estate_support` del manifiesto en `package.real_estate` para que el writer pueda materializar `Propiedad` y la fuente controlada de contribuciones. |
| Motivo de prioridad | Es una brecha local de preparacion del paquete controlado. No requiere SII real, `.env`, EDIG ejecutable ni outputs finales como input. |
| Worktree | Continuar/cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-real-estate-values-draft`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-real-estate-values-draft`; al cerrar, PR/CI/merge y limpiar worktree. |
| Estado | En desarrollo validado focalmente: `build_annual_tax_controlled_values_draft` parsea registro estructurado de bienes raices, asocia respaldos de contribuciones/pagos, suma solo pagos del `commercial_year` y genera `package.real_estate` con `final_tax_calculation=false`. En evidencia real AC2024/AT2025 detecta 6 propiedades y 0 pagos AC2024 verificables; el dry-run del writer valida `real_estate_snapshot.present=true`. |
| Gate esperado | Etapa 6/mirror proof sigue `classification=parcial`. La aplicacion real de propiedades en DB requiere antes `ownership` controlado con participaciones completas; sin eso, el dominio de Patrimonio bloquea `Propiedad` activa. |
| Estado al cerrar paquete | No reabrir Compliance #879, filtro #880, union de tokens #881, hash de registros #882, paquetes Stage 6 ya mergeados ni prompts de goal. El siguiente frente real debe completar/revisar `ownership` controlado antes de aplicar bienes raices en el piloto real. |
| Bloqueos relacionados | `ownership_snapshot_missing`/participaciones completas es condicion previa de aplicacion DB para propiedades activas; contribuciones AC2024 quedan sin pagos verificables en los respaldos actuales y no se tratan como calculo final. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Completar validacion, PR/CI/merge y limpiar `stage6-real-estate-values-draft`; luego continuar con snapshot `ownership` controlado/OCR-revision o con el siguiente frente seguro si el usuario no autoriza/completa esa fuente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
