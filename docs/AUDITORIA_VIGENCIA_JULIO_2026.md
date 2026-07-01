# Auditoria de vigencia - julio 2026

Fecha: 2026-07-01, `main` en `88cf5885`.
Ejecutada por: agente Claude (Claude Fable 5) asistiendo a Joaquin, por
solicitud explicita del usuario.
Documento hermano: `docs/ORDENAMIENTO_JULIO_2026.md`.

## 1. Proposito y regla

Clasificar todo el set documental y los artefactos pesados del root para
distinguir lo que sirve hoy de lo que quedo como trazabilidad o duplicado.
Regla aplicada: **nada se borro, nada se movio, nada se reescribio**. Esta
auditoria solo clasifica y propone; toda eliminacion queda como propuesta
pendiente de decision explicita del usuario, caso por caso.

Metodo: lectura de encabezados/estado declarado de cada documento, contraste
con la jerarquia de `AGENTS.md` y `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md`,
e inventario metadata-only de artefactos pesados (nombres y tamanos; sin abrir
contenidos, sin leer PDFs, sin tocar datos sensibles). Los inventarios
detallados quedaron en `local-evidence/audit-vigencia-2026-07-01/` (no
versionados).

## 2. Clasificacion documental

Categorias:

- `vigente_rector`: manda hoy; leer siempre.
- `vigente_operativo`: procedimiento o plan utilizable hoy o en un paso futuro
  ya previsto.
- `registro_vivo`: se actualiza continuamente (bloqueos, evidencia, cursor).
- `referencia_no_normativa`: apoyo tecnico/funcional; no autoriza reglas.
- `historico_trazabilidad`: cumplio su funcion; se conserva solo para saber
  por que las cosas quedaron asi. No leer para decidir el presente.

### 2.1 Vigente rector (leer para decidir)

| Documento | Nota |
| --- | --- |
| `AGENTS.md` | Protocolo operativo y jerarquia. Punto de entrada. |
| `ORDEN_DE_LECTURA.md` | Indice de lectura. |
| `README.md` (root) | Identidad del root limpio. |
| `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md` | Que manda y que rol tiene cada fuente. |
| `docs/governance/CODEX_OPERATING_PROTOCOL_MAYO_2026.md` | Como ejecutar cambios. |
| `01_Set_Vigente/PRD_CANONICO.md` | Contrato rector de producto. |
| `01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md` | Estado de capacidades externas. |
| `01_Set_Vigente/BACKLOG_INVESTIGACION.md` | Backlog vigente de investigacion. |
| `02_ADR_Activos/ADR_ARQUITECTURA_001..006, 008` | Decisiones tecnicas activas. |
| `08_Auditoria_Stack/ADR_STACK_FINAL.md` | Stack canonico v1. |
| `docs/architecture/ARQUITECTURA_MAESTRA_LEASEMANAGER.md` | Sintesis rectora. |
| `docs/product/PLAN_EJECUCION_TRAZABLE_CIERRE_MAYO_2026.md` | Plan de cierre por etapas. |
| `docs/product/STAGE_CARDS/ETAPA_0..7` (10 fichas) | Definicion y estado por etapa. |
| `docs/product/ANEXO_MODELO_OPERATIVO_EXCEL_MAYO_2026.md` | Anexo vigente del PRD. |
| `docs/product/RENTA_ANUAL_AT2026_ENGINE_BLUEPRINT.md` | Diseno propio del motor anual. |
| `docs/product/RENTA_ANUAL_OFFICIAL_SOURCE_GAPS_AT2026.md` | Limites y fuentes oficiales Etapa 6. |
| `docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md` | Base tecnica definitiva de comunidades/recaudacion. |
| `03_Ejecucion_Tecnica/` (8 documentos) | Capa de ejecucion; subordinada a stage cards segun precedencia de `AGENTS.md`. |

### 2.2 Registro vivo (se actualiza al avanzar)

| Documento | Nota |
| --- | --- |
| `docs/product/EXECUTION_CURSOR_MAYO_2026.md` | Frente activo; actualizado 2026-07-01. |
| `docs/product/BLOCKERS_MAYO_2026.md` | Bloqueos activos BLK-002..BLK-011. |
| `docs/product/EVIDENCE_REGISTER_MAYO_2026.md` | 848+ entradas de evidencia. |
| `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` | Estado por frente. |
| `docs/product/MAPA_ESTADO_JULIO_2026.md` | Foto compacta + insumos pendientes. |
| `docs/ORDENAMIENTO_JULIO_2026.md` | Registro del ordenamiento 2026-07-01. |
| `docs/AUDITORIA_VIGENCIA_JULIO_2026.md` | Este documento. |

### 2.3 Vigente operativo (runbooks y procedimientos utilizables)

| Documento | Nota |
| --- | --- |
| `docs/MIGRATION_RUNBOOK.md` | Migracion read-only; pendiente por `BLK-007`. |
| `docs/product/STAGE1_SNAPSHOT_INTAKE_MAYO_2026.md` | Ruta opt-in para `BLK-002`. |
| `docs/operations/CUTOVER_RUNBOOK_MAYO_2026.md` | Preparacion de cutover futuro. |
| `docs/operations/EDIG_AT2026_SANDBOX_RUNBOOK.md` | Sandbox condicional; hoy no es necesario ejecutar EDIG (ver ficha Etapa 6). |
| `docs/operations/PROCEDIMIENTO_CAMBIO_MES_EXCEL.md` | Operacion mensual del Excel maestro mientras siga vivo. |
| `docs/DEPLOY_BACKEND_GREENFIELD.md`, `docs/DEPLOY_FRONTEND_VERCEL.md`, `docs/ROLL_OUT_BACKEND_FRONTEND.md` | Publicacion; condicionados a gates (`BLK-006`) y confirmacion del usuario. |
| `docs/SUPABASE_STAGING_PLAYBOOK.md` | Ejecutado 2026-04; reutilizable solo si se repite un staging. Supabase no es modelo final. |
| `backend/README.md`, `infra/README.md`, `migration/README.md` | Arranque local e inventario legacy. |

### 2.4 Referencia no normativa (apoyo; no autoriza reglas)

| Documento | Nota |
| --- | --- |
| `docs/product/RENTA_ANUAL_EDIG_AT2026_MAPPING.md` | Mapeo funcional EDIG -> LeaseManager. |
| `docs/product/REFERENCIA_FUNCIONAL_EDIG_DESCARGAS_AT2026_2026-06-15.md` | Revision descargas EDIG. |

### 2.5 Historico trazabilidad (no leer para decidir el presente)

| Documento | Por que quedo historico |
| --- | --- |
| `05_Contexto_Historico/` completo (7 archivos, incluye `CLAUDE.md` y `prd.txt`) | Autodeclarado historico; PRD marzo reemplazado por PRD mayo. |
| `06_Fuentes_PRD_1_26/` (26 PRD fuente) | Materia prima ya consolidada. |
| `07_ADR_Historicos_o_Podados/ADR_007` | pgvector/IA semantica fuera del boundary v1. |
| `04_Auditoria_y_Cierre/AUDITORIA_MAXIMA_PRD_MAESTRO.md` | Entregable para una reescritura de PRD ya ejecutada. |
| `04_Auditoria_y_Cierre/AUDITORIA_AUTOSUFICIENCIA_SET_ACTIVO.md` | Auditoria del set de marzo; util solo como trazabilidad. |
| `08_Auditoria_Stack/AUDITORIA_STACK_V1.md`, `MATRIZ_COMPARATIVA_STACK.md` | Analisis que respaldo el ADR de stack ya aprobado. |
| `docs/AUDITORIA_DISENO_COMUNIDADES_Y_RECAUDACION_2026-04-05.md` | Recomendaciones ya absorbidas por la especificacion tecnica final. |
| `docs/AUDITORIA_DOCUMENTAL_POST_MERGE_MAYO_2026.md`, `docs/AUDITORIA_PRODUCTO_ARQUITECTURA_MAYO_2026.md` | Auditorias post-merge ya ejecutadas. |
| `docs/GREENFIELD_BOOTSTRAP.md` | Bootstrap ya ejecutado; arranque local vive en READMEs. |
| `docs/ORDENAMIENTO_PROFESIONAL_ROOT_MAYO_2026.md`, `docs/RESULTADO_REEMPLAZO_ROOT_MAYO_2026.md`, `docs/SWAP_ROOT_RUNBOOK_MAYO_2026.md`, `docs/RELEASE_GATE_BASELINE_MAYO_2026.md` | Reemplazo del root y baseline de mayo, ejecutados y cerrados. |
| `docs/product/PLAN_ORDENAMIENTO_PROFESIONAL_MAYO_2026.md` | Antecedente del plan ya ejecutado (autodeclarado). |
| `docs/product/PRD_CANONICO_MAYO_2026_CANDIDATO.md`, `PRD_CANONICO_MAYO_2026_AUDITORIA_FUENTES.md`, `AUDITORIA_PRD_ORDENAMIENTO_MAYO_2026.md` | Trazabilidad de la promocion del PRD mayo. |
| `frontend/README.md` | Template generico de Vite sin adaptar; unico documento sin valor de contexto. Candidato a reescritura futura (no a borrado). |

Conclusion documental: el set esta sano. Todo documento historico ya se
autodeclara historico o esta en carpeta de historicos; no se encontro ningun
documento activo contradiciendo al set vigente. El unico ajuste sugerido a
futuro es reescribir `frontend/README.md`.

## 3. Artefactos pesados (fuera de git; inventario metadata-only)

`local-evidence/` pesa ~32 GB y `EDIG/` ~2.8 GB. Ambos estan correctamente
ignorados por git. Clasificacion por carpeta:

### 3.1 Conservar (evidencia activa o fuente unica)

| Carpeta | Tamano | Rol |
| --- | --- | --- |
| `EDIG/` (root) | 2.8 GB | Copia canonica de referencia funcional EDIG (2.572 archivos). |
| `local-evidence/inmobiliaria-puig/` | 1.7 GB | Fuentes AC/AT de Etapa 6 (manifiestos, DTE, contribuciones, auditorias de fuente). Evidencia activa. |
| `local-evidence/stage1..stage6, stage5-documents, acceptance, compliance, sii-at2026-output-readiness` | ~60 MB | Salidas de gates de readiness. Activas. |
| `local-evidence/company-document-intake/`, `inmopuig-h1-2026-close-master/`, `monthly-tax-payments/`, `edig-*inventory*`, `edig-at2026-goal-audit/`, `self-sufficiency-audit-2026-07-01/`, `audit-vigencia-2026-07-01/` | ~60 MB | Intakes, inventarios y auditorias referenciadas. |
| Carpeta `*_CONFIDENCIAL_NO_SUBIR` de mapeo mensual (nombre completo omitido aqui por privacidad) | 9 MB | Material confidencial manual. No tocar. |
| `local-evidence/empresas-puig-historical-full-source-copy-2026-06-30/` | 6.3 GB | Copia historica completa de la fuente EMPRESAS PUIG (savegame). Se conserva por regla de savegames, con la excepcion del duplicado EDIG interno (ver 3.2). |

### 3.2 Duplicados verificados (propuesta de limpieza; requiere decision del usuario)

| # | Carpeta | Tamano | Verificacion | Propuesta |
| --- | --- | --- | --- | --- |
| 1 | `local-evidence/external-software-reference-edig-root-copy-2026-07-01/` | 2.8 GB | Identica a `EDIG/` root: 2.572/2.572 archivos coinciden por ruta relativa y tamano (inventario en `audit-vigencia-2026-07-01/`). | Eliminar tras OK del usuario. Recupera 2.8 GB. |
| 2 | `.../EMPRESAS PUIG/Reorganizacion Contabilidad/99_REFERENCIAS_SOFTWARE_EXTERNO/EDIG_DESCARGAS_2026-06-15/` | 1.1 GB | 1.430/1.439 archivos core coinciden con `EDIG/` root; los 9 restantes son instaladores/PDF con nombre distinto ya presentes por otra via. | Opcional: eliminar solo el duplicado interno dejando nota `.md` con el inventario; el resto del savegame no se toca. Recupera ~1.1 GB. |

### 3.3 Dumps de trabajo voluminosos (propuesta de compresion o poda; requiere decision)

| # | Carpeta | Tamano | Caracterizacion | Propuesta |
| --- | --- | --- | --- | --- |
| 3 | `local-evidence/revisar-document-audit/2026-06-21/` | 19 GB, 101.331 archivos | Pasadas intermedias de OCR/render/comparacion de la auditoria documental (ej. `ocr-execution-pass5` 4.9 GB, `pdf-render-recovery-pass44` 2.3 GB, `_tmp_text_compare` 653 MB). Esta referenciada por el registro de evidencia, por lo que NO debe eliminarse completa. | Conservar resultados finales; comprimir o podar solo subcarpetas intermedias `_tmp_*` y pasadas de render/OCR reproducibles, previa confirmacion de que ninguna esta citada como evidencia final. Recuperable estimado: 8-15 GB. |
| 4 | `local-evidence/revisar-dbstore-p5387/` | 2.9 GB | Almacen de PDFs de revision con nombres hasheados; 1.912 archivos, solo 1.091 unicos por nombre+tamano (~43% duplicacion interna). | Deduplicar internamente tras OK. Recuperable estimado: ~1.2 GB. |
| 5 | `local-evidence/stage1-*.sqlite3` (4 archivos sueltos) | ~5 MB | Bases de verificacion de gates ya corridas. | Menor; conservar o agrupar en subcarpeta `stage1/`. Sin urgencia. |
| 6 | PNGs sueltos en el root (11 archivos: capturas de depuracion de jun-2026) | ~2.5 MB | Ignorados por git; solo ruido visual del root. | Mover a `local-evidence/` o eliminar tras OK. Sin urgencia. |

Potencial total de espacio recuperable si el usuario aprueba todo: **~13 a 20 GB**
(items 1-4). Ninguna de estas acciones se ejecuto: son propuestas.

## 3.4 Actualizacion 2026-07-01: decision del usuario y ejecucion

El usuario definio la politica final: no borrar nada; trasladar lo repetido o
sin funcion a una zona inutilizado con rastro. Resultado de la ejecucion,
tras verificacion de referencias mas profunda:

- Items 1 y 2 de la tabla 3.2: **trasladados** a
  `local-evidence/_inutilizado/2026-07-01/` (3.8 GB en total, restaurables).
- Item 3 (`revisar-document-audit`, 19 GB): **reclasificado a conservar**. La
  verificacion encontro que es una red interreferenciada: el registro de
  evidencia cita `expediente-integral-dry-run-pass5390`, las notas de revision
  citan `pdf-render-recovery-pass44` y `_tmp_text_compare` tiene 160
  referencias externas. Tiene funcion; no se movio nada.
- Item 4 (`revisar-dbstore-p5387`, 2.9 GB): **reclasificado a conservar**. Su
  duplicacion interna es organizacion deliberada (arbol canonico
  `canonical-pdf-*` + arbol por destino `destination-pending-responsible-review`).
- Items 5 y 6 (sqlite sueltos y PNGs del root): **trasladados**.

Rastro: manifiesto en `local-evidence/_inutilizado/2026-07-01/MANIFIESTO_TRASLADOS.md`,
migajas `MOVIDO-*.md` en los origenes y seccion 3.6 de
`docs/ORDENAMIENTO_JULIO_2026.md`.

## 4. Regla de ejecucion de las propuestas

Cada item de 3.2/3.3 se ejecuta solo con OK explicito del usuario, item por
item, y siguiendo este orden: (a) verificar que ningun gate o registro de
evidencia referencia rutas dentro de lo que se elimina; (b) dejar registrado en
`docs/ORDENAMIENTO_JULIO_2026.md` o su sucesor que se elimino, cuando y con que
verificacion; (c) preferir comprimir sobre eliminar cuando la duda exista.
