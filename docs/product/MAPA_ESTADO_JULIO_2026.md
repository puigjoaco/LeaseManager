# Mapa de estado - julio 2026

Fecha de corte: 2026-07-01, `main` en `3c174232`.
Proposito: foto compacta de que esta funcionando, que esta preparado sin
evidencia y que falta para cerrar cada frente, con foco en los insumos que solo
el usuario puede aportar.

Este mapa es informativo y derivado. Ante cualquier conflicto mandan, en este
orden: `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md`,
`01_Set_Vigente/PRD_CANONICO.md`, `01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md`,
los ADR activos, `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`,
`docs/product/BLOCKERS_MAYO_2026.md` y
`docs/product/EXECUTION_CURSOR_MAYO_2026.md`. Este documento no abre gates, no
cierra etapas y no autoriza fuentes.

## 1. Lectura rapida del estado

La ingenieria esta sustancialmente construida (~171k lineas Python en 12 apps
Django, ~1.400 tests en acceptance, gates de readiness por etapa en
`scripts/`). El patron dominante es: codigo y validadores listos, cierre
bloqueado por fuente autorizada, prueba externa o decision del usuario. El
cuello de botella del proyecto no es codigo; son insumos y decisiones.

## 2. Estado por etapa

Estados segun `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` (tabla final).

| Etapa | Frente | Estado | Que falta para cierre | Quien desbloquea |
| --- | --- | --- | --- | --- |
| 0 | Gobierno documental, PRD, PlataformaBase | resuelto_confirmado | Nada; mantener como baseline. | - |
| 0 | Compliance datos personales | parcial | Politica aprobada, responsables, evidencia archivada, validacion legal (`BLK-010`, deadline 2026-12-01). | Usuario + legal |
| 1 | Patrimonio, Operacion, Contratos | implementado_sin_evidencia | Snapshot controlado o DB real autorizada para `run-stage1-snapshot-gate.ps1` (`BLK-002`). | Usuario |
| 2 | CobranzaActiva | parcial | Prueba externa real/controlada de correo y WebPay; datos de Etapa 1 confirmados (`BLK-003`). | Usuario |
| 3 | Conciliacion | parcial | Banco real o snapshot autorizado, cuadratura sistema/banco, responsable (`BLK-003`). | Usuario + banco |
| 4 | SII (DTE, F29) | parcial | Ambiente SII real/controlado autorizado, regla fiscal validada, responsable (`BLK-003`, `BLK-004`). | Usuario + SII/experto |
| 5 | Contabilidad | parcial | Conciliacion cerrada, ledger/reportes controlados, responsable. | Depende de Etapa 3 |
| 5 | Documentos | parcial | Decision final de politica firma/notaria, prueba PDF controlada, responsable (`BLK-005`). | Usuario |
| 6 | Renta Anual | parcial | Ver seccion 3; es el frente activo. | Usuario + experto |
| 7 | Reporting | parcial | Cierres/snapshot controlado y datos reales autorizados. | Depende de etapas previas |
| 7 | Operacion productiva | parcial | Restore autorizado, senales runtime en ambiente real, smoke publico autorizado, aceptacion final (`BLK-006`). | Usuario |
| 1 | Migracion legacy | parcial | Autorizar fuente concreta y validar snapshot/bundle controlado; decidir `BLK-008`. | Usuario |

Bloqueos completos con detalle y rutas de desbloqueo:
`docs/product/BLOCKERS_MAYO_2026.md` (`BLK-002` a `BLK-011` abiertos).

## 3. Frente activo: Renta Anual AC2025/AT2026

Hito ya confirmado: la prueba espejo AC2024/AT2025 de Inmobiliaria Puig quedo
`resuelto_confirmado` el 2026-06-17. El motor anual completo (source bundle ->
MonthlyTaxFact -> balance ocho columnas -> RLI/CPT -> RAI/SAC -> bienes raices
-> matriz DDJJ/F22 -> dossier -> export -> checklist) reprodujo los outputs
esperados: 138/138 valores comparables y 7/7 documentos DDJJ/F22, sin usar
outputs finales como input. Detalle en
`docs/product/STAGE_CARDS/ETAPA_6_RENTA_ANUAL.md`.

Para repetir el ciclo con AC2025/AT2026 faltan estos insumos, que solo el
usuario puede aportar o autorizar:

| # | Insumo pendiente | Para que sirve | Herramienta que lo consume |
| --- | --- | --- | --- |
| 1 | Snapshot ownership: socios/participaciones vigentes al 31-12-2025, desde fuente societaria controlada (escrituras/extractos revisados, no inferencia) | Sin ownership al 31-12 no hay generacion anual: bloquea retiros/dividendos, `Propiedad` activa y el mirror | Cadena `build_annual_tax_ownership_evidence_chain` -> revision/OCR manual -> patch privado -> `validate_annual_tax_ownership_patch` -> `inject_annual_tax_ownership_patch_into_controlled_package` |
| 2 | Certificado o cartola formal Banco de Chile al 31-12-2025, o autorizacion explicita para usar soporte observado | Cobertura bancaria/leasing `verified_complete` (`BLK-011`); sin ella el paquete contable/renta queda `parcial` | `audit_company_bank_support_coverage` y paquete de revision contable |
| 3 | Respuestas responsables completadas sobre el handoff packet de preguntas | Gate de revision responsable; separa avance local de decision humana | `materialize_company_accounting_responsible_handoff_packet` -> completar respuestas -> `audit_company_accounting_responsible_answers_draft` -> `materialize_company_accounting_responsible_answers` |
| 4 | Valores manuales del writer anual AC2025 (libros anuales, F29, remuneraciones si aplica) via paquete controlado | Materializa los 12 `MonthlyTaxFact` y capas anuales en DB local/controlada | `build_annual_tax_controlled_values_draft` -> `audit_annual_tax_controlled_package_readiness` -> `apply_annual_tax_controlled_db_load` -> `run_annual_tax_controlled_mirror` |
| 5 | Validacion oficial/experta de reglas fiscales AT2026 (`BLK-004`) | Ninguna salida tributaria se declara final sin ella | Revision experta sobre dossier/checklist |

Limites vigentes que ningun avance local altera: presentacion SII, calculo
tributario final y contabilidad final siguen cerrados
(`SII.PresentacionAnualFinal` podada; `final_tax_calculation=false` en todos
los artefactos). No se leen `.env`, DB real, SII real, banco, correos ni EDIG
ejecutable sin autorizacion explicita. Evidencia local vive bajo
`local-evidence/` y no se versiona.

## 4. Pendientes de orden menor

- Decision del usuario sobre la rama `codex/stage6-tax-software-boundary`
  (commit documental `d488dc49` nunca integrado; ver
  `docs/ORDENAMIENTO_JULIO_2026.md`, seccion 3.5).
- `BLK-008`: decidir tratamiento de artefactos legacy sensibles e historial.

## 5. Actualizacion de este mapa

Actualizar cuando cambie el estado de un frente en la matriz de trazabilidad,
cuando se aporte o autorice un insumo de la seccion 3, o cuando un bloqueo de
`BLOCKERS_MAYO_2026.md` cambie de estado. Si este mapa queda desactualizado,
mandan las fuentes rectoras listadas arriba.
