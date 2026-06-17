# Etapa 6 - Dossier de renta anual

## Objetivo

Preparar el dossier anual de renta, DDJJ, F22, certificados y trazabilidad
desde cierres mensuales. LeaseManager organiza datos, reglas, bloqueos y
evidencia; la decision tributaria final requiere revision experta/oficial,
responsable trazado y gate aplicable.

## Alcance

- Proceso de renta anual como expediente revisable.
- Certificados.
- Declaraciones juradas.
- F22 y respaldos.
- Validaciones tributarias.
- Checklist de revision experta/oficial.

## Referencia EDIG AT2026

`docs/product/RENTA_ANUAL_EDIG_AT2026_MAPPING.md` registra la investigacion
local del software EDIG AT2026 como referencia funcional no normativa. El
aprendizaje aceptado para LeaseManager es que renta anual se automatiza mediante
una capa tributaria intermedia: cierres, ledger, F29/PPM, patrimonio, socios,
arriendos, contribuciones y certificados se transforman primero en RLI, CPT,
RAI, SAC, DDJJ y respaldos; recien despues se mapean a F22/export.

EDIG no autoriza reglas fiscales propias, formatos SII finales ni presentacion
automatica. Cualquier ejecucion de EDIG solo puede ocurrir en la VM/sandbox
descrita en `docs/operations/EDIG_AT2026_SANDBOX_RUNBOOK.md`, con datos
ficticios, red controlada y sin credenciales reales.

`docs/product/REFERENCIA_FUNCIONAL_EDIG_DESCARGAS_AT2026_2026-06-15.md`
registra la revision posterior de la pagina oficial de descargas EDIG y de las
carpetas externas archivadas para Contabilidad, Renta AT2026 y
Remuneraciones. La conclusion adicional es que Remuneraciones cierra el ciclo
laboral/previsional que alimenta la renta anual: LRE, Previred, liquidaciones,
impuesto unico, DJ1887, certificados y centralizacion contable deben modelarse
como fuentes revisables del dossier anual. Esto no abre un payroll completo por
defecto ni autoriza reglas laborales/tributarias desde EDIG; solo fija una
brecha de fuente y diseno para una capa laboral/previsional controlada.

La revision consolidada posterior de `D:\Proyectos\10_ACTIVOS\LeaseManager\EDIG`
confirma las tres lineas completas: Contabilidad (libros, F29, balance de ocho
columnas, DJ1847), Remuneraciones (trabajadores, liquidaciones, Previred, LRE,
DJ1887 y centralizacion contable) y Renta (regimenes 14A/14D3/14D8/14G, RLI,
CPT, RAI, SAC, DDJJ, F22, plantillas E-DJ y export/preview). LeaseManager debe
tratar Remuneraciones primero como `fuente anual laboral/previsional`
importable o revisable dentro del source bundle anual; construir un payroll
completo queda fuera del cierre automatico de Etapa 6 salvo ADR/gate propio.
La iteracion SII 2026-06-15 confirma el mismo boundary: F22 AT2026 requiere
certificacion de software que genera archivos y SII no certifica contenido ni
consistencia tributaria; DDJJ 2026 se maneja por medios oficiales por
formulario y EDIG aparece como casa software DDJJ, no como fuente normativa.
Por tanto, no hace falta ejecutar EDIG para avanzar esta etapa. Cualquier
ejecucion futura de `.exe` queda limitada a sandbox observacional con datos
ficticios y una brecha concreta de UI/export previamente registrada.

El inventario estatico read-only de `scripts/analyze-edig-at2026.ps1` clasifica
senales funcionales por administracion, F22, F29/PPM, regimenes 14A/14D3/14D8/
14G, RLI, CPT, RAI, SAC, DDJJ, balance, bienes raices/arriendos,
reportes/respaldo, upload/export y conectividad auxiliar. Las raices de datos
de usuario/licencia/salida quedan excluidas o redactadas; la salida se mantiene
en `local-evidence/` y no se versiona.

`scripts/extract-edig-mdb-schema.ps1` puede extraer metadata de tablas/columnas
de los MDB nucleo desde copias temporales, sin ejecutar EDIG ni leer filas. La
extraccion local confirma bases separadas para maestros, F29/PPM, parametria de
regimen, PRO/F22 y registros RLI/CPT/RAI/SAC. Esa evidencia orienta el motor
anual propio, pero no habilita copiar schema EDIG ni declarar reglas fiscales.

`scripts/build-edig-at2026-leasemanager-coverage.ps1` cruza los inventarios
sanitizados de `local-evidence/` contra componentes propios observables en el
repo. La matriz local confirma que LeaseManager ya cubre la columna vertebral
funcional observada en EDIG: configuracion, F29/PPM, parametria AT, RLI/CPT,
RAI/SAC, bienes raices, matriz DDJJ/F22, dossier y export local. Las brechas
restantes son de fuente oficial/experta, saldos historicos, contribuciones,
formatos/certificacion SII y autorizacion de presentacion; no son razon para
copiar mas EDIG ni abrir una integracion externa.

`docs/product/RENTA_ANUAL_AT2026_ENGINE_BLUEPRINT.md` traduce esa evidencia a
componentes propios de LeaseManager: source bundle anual, rule set por AT,
normalizador, workbooks RLI/CPT, registros RAI/SAC, seccion bienes raices,
paquetes DDJJ, draft F22, dossier y export gate.
`TaxYearRuleSet` y `TaxCodeMapping` materializan la primera parte de esa capa
propia: reglas versionadas por ano tributario/regimen y mapeos trazables hacia
RLI/CPT/RAI/SAC/DDJJ/F22/Dossier, sin copiar reglas EDIG ni declarar formulas
fiscales finales.
`AnnualTaxSourceBundle` materializa la siguiente capa: congela fuentes anuales
no sensibles desde cierres mensuales, obligaciones PPM/F29 y configuracion
fiscal, conserva hash SHA-256 del payload anual normalizado y se enlaza al
`ProcesoRentaAnual` para que DDJJ/F22 partan desde un dossier revisable, no
desde inferencia libre ni automatizacion tributaria autonoma.
`build_annual_tax_source_manifest` prepara la entrada controlada previa al
bundle para pilotos historicos como Inmobiliaria Puig AC2024/AT2025: lee una
carpeta externa en modo read-only, clasifica archivos como entradas, soportes o
salidas esperadas, calcula hashes, no copia documentos al repo y emite un
borrador no sensible de `AnnualTaxSourceBundle`. Este manifiesto confirma si
existen fuentes suficientes para una prueba espejo desde libros cerrados, pero
no crea cierres mensuales ni hechos tributarios en DB y no reemplaza revision
experta.
Para evitar una prueba circular, el manifiesto separa explicitamente inputs de
calculo y objetivos de comparacion: Libro Diario, Libro Mayor, Libro
Inventario, RCV, F29, compra/venta, remuneraciones y fuente societaria/
patrimonial pueden alimentar carga controlada; Balance General, RLI, CPT, RAI,
Capital Propio, Rentas Empresariales, DDJJ y F22 quedan como salidas esperadas/
baseline. LeaseManager no puede declarar que genero esos artefactos si antes
los uso como insumo de calculo.
El manifiesto tambien exige `ownership_source_input` para considerar completa
la fuente de prueba espejo anual. En la carpeta real AC2024/AT2025 de
Inmobiliaria Puig, RCV, F29 controlado, libros anuales, DDJJ, F22 y registros
esperados estan cubiertos, pero `ready_for_mirror_source_bundle=false` porque no
se encontro fuente societaria independiente (`ownership_source_present=false`).
Ademas distingue candidatos legales de fuente controlada: escrituras,
extractos, inscripciones o Diario Oficial en contexto societario quedan como
`ownership_source_candidate` de soporte/revision. La corrida real detecta 15
candidatos, pero no los usa como input de calculo ni desbloquea la prueba anual
hasta que una fuente suficiente sea revisada y convertida en snapshot
controlado de socios/participaciones vigentes. Las escrituras de propiedades no
se clasifican como ownership societario.
Desde 2026-06-16 el manifiesto separa la entrada operativa al piloto del cierre
del objetivo. Si RCV, F29 controlado, libros anuales, remuneraciones, Balance,
registros tributarios, DDJJ y F22 estan cubiertos, y falta
`ownership_source_input` pero existen `ownership_source_candidate`, entonces
`ready_for_closed_books_mirror_pilot=true` y
`ready_to_start_closed_books_pilot=true`: se puede iniciar el piloto desde
libros cerrados y preparar la revision ownership. En paralelo,
`ready_for_mirror_source_bundle=false`,
`source_documentation_confirmed_for_ac2024_at2025=false` y
`ready_for_objective_completion=false` siguen bloqueando cualquier conclusion
de equivalencia final, presentacion SII o cierre tributario autonomo.
`review_annual_tax_ownership_candidates` revisa esos candidatos sin guardar
texto crudo, RUTs ni nombres: en la evidencia real AC2024/AT2025 los PDFs no
son extraibles por `pdftotext`, por lo que 10 quedan como candidatos legales
para OCR/revision manual, 3 se excluyen por nulos/sin efecto y 2 quedan como
soporte de aportes/propiedades. El resultado permite avanzar a snapshot
controlado, pero no cierra la fuente ownership ni crea socios/porcentajes por
inferencia.
`build_annual_tax_ownership_snapshot_template` prepara el puente hacia el
writer anual: desde la revision real genera 10 `candidate_sources`, un
`ownership_patch_template` con `participants=[]` y reglas para completar socios,
RUT, porcentajes, vigencias y evidencia no sensible. El template no esta listo
para DB hasta que esa informacion sea completada por OCR/revision controlada y
aprobacion responsable.
`build_annual_tax_ownership_visual_review_packet` prepara esa revision: renderiza
paginas iniciales de los 10 candidatos a PNG bajo `local-evidence`, con indice
por hash/path_ref. La corrida real produce 19 paginas sin errores. Las imagenes
pueden contener datos sensibles, por lo que no se versionan ni se usan como
calculo; sirven para OCR/revision manual previa a completar el snapshot.
`build_annual_tax_ownership_evidence_chain` deja esa secuencia reproducible
desde `main`: manifiesto, revision de candidatos, template ownership y paquete
visual opcional se regeneran bajo `local-evidence/` con una sola orden. Esto no
desbloquea `ownership` por si mismo ni genera participantes; evita que la etapa
dependa de artefactos locales perdidos y mantiene el siguiente paso en
revision/OCR y aprobacion responsable.
`validate_annual_tax_ownership_patch` valida el patch local completado contra
ese template antes de inyectarlo al paquete controlado. El comando rechaza
patches versionados fuera de `local-evidence/`, no escribe DB y emite solo un
reporte redactado con hashes de referencias no sensibles, conteos, porcentaje
total y rutas faltantes/invalidas. En la evidencia real AC2024/AT2025, el patch
pendiente queda correctamente bloqueado por `$.ownership.participants` vacio:
la arquitectura esta lista para recibir ownership controlado, pero no inventa
socios, RUTs ni porcentajes desde F22/DDJJ, registros finales o inferencia.
`build_annual_tax_ownership_review_checklist` consolida el siguiente paso sin
exponer PII: combina template, reporte de validacion redactado y paquete visual
opcional en una cola de revision con candidatos hasheados, conteos de paginas
renderizadas, items pendientes y decision de readiness. La corrida real local
AC2024/AT2025 queda `ready_for_manual_review=true`, con 10 candidatos y 10
candidatos renderizados, pero `ready_for_controlled_db_load=false` por
`ownership_patch_missing` y `participants_count=0`. Esto fija la accion
correcta: completar participantes bajo `local-evidence/` desde revision/OCR
legal controlada, no desde outputs finales ni memoria del chat.
`build_annual_tax_controlled_load_plan` traduce ese manifiesto a un plan de
carga contra modelos canonicos de LeaseManager sin escribir DB: cierres,
libros, balance, obligaciones, F29, hechos mensuales y balance tributario
anual. Para Inmobiliaria Puig AC2024/AT2025 el plan confirma que los outputs
esperados no se usan como input, pero `ready_for_db_load=false` hasta tener
parser/carga manual controlada para libros anuales, F29 PDF, remuneraciones y
fuente societaria, mas un paquete normalizado de entrada, capa anual generada y
comparacion de outputs esperados.
`build_annual_tax_controlled_db_load_template` crea el template seguro de ese
paquete normalizado desde el manifiesto: prearma 12 meses, separa refs de
entrada y `comparison_targets`, y deja los valores contables/tributarios vacios
para parser o carga manual controlada. No escribe DB ni convierte outputs
esperados en insumos. Los meses F29 marcados en el manifiesto como sin
declaracion quedan modelados como `no_aplica`, no como documento faltante.
`apply_annual_tax_controlled_db_load` materializa ese paquete normalizado en DB
local/controlada solo con `--apply`: crea o actualiza cierres mensuales,
LibroDiario, LibroMayor, BalanceComprobacion, obligaciones, F29 y
MonthlyTaxFact, rechazando refs sensibles y cualquier Balance/RLI/CPT/RAI/DDJJ/
F22 final usado como input. Por defecto opera en dry-run para validar sin
escribir DB.
El mismo paquete puede incluir `ownership` como snapshot patrimonial controlado:
fuente no sensible, fecha `as_of`, socios con RUT valido, porcentajes, vigencias
y evidencia no sensible. El writer materializa `Socio` y
`ParticipacionPatrimonial` solo cuando se aplica contra DB local/controlada, y
el mirror anual usa esas participaciones para RETIROS/DIVIDENDOS. Si la fuente
patrimonial no existe, la arquitectura no inventa porcentajes desde cuentas de
retiro ni desde F22/DDJJ finales; conserva warning de revision hasta cargar una
fuente societaria controlada.
`audit_annual_tax_controlled_package_readiness` audita el template o paquete
antes de aplicar el writer: confirma 12 meses, refs de control, valores de
libros/balance, estado F29, estado laboral/previsional y ausencia de outputs
finales usados como input. Ademas separa `ready_for_db_writer` de
`ready_for_annual_generation`: la contabilidad mensual puede estar completa y
aplicable al writer, pero la generacion anual/mirror queda bloqueada si falta
`ownership` como snapshot patrimonial controlado para registros de retiros y
dividendos. Contra el template real de Inmobiliaria Puig AC2024/AT2025 confirma
que no faltan meses y que existen objetivos de comparacion, pero mantiene
`ready_for_db_writer=false` hasta completar los valores normalizados; contra el
draft real post revision laboral completa, `ready_for_db_writer=true` y
`ready_for_annual_generation=false` por `ownership_snapshot_missing`. Febrero y
diciembre F29 `no_aplica` no cuentan como faltantes.
`build_annual_tax_controlled_values_draft` completa ese paquete desde fuentes
AC2024 permitidas y read-only: Libro Diario, Libro Mayor, Libro Inventario, F29,
libros de remuneraciones y soporte de bienes raices. La corrida real de
Inmobiliaria Puig rellena valores contables/laborales, revisa 112 respaldos
laborales esperados para generar `labor_previsional.source_ref`, y genera
`package.real_estate` desde el registro estructurado de bienes raices,
respaldos por `path_ref` e historiales de pago filtrados por `commercial_year`.
En AC2024/AT2025 detecta 6 propiedades y 0 pagos AC2024 verificables, sin usar
outputs finales como input ni declarar calculo fiscal. La aplicacion de
propiedades a DB sigue condicionada por `ownership`: el dominio de Patrimonio
rechaza `Propiedad` activa si la empresa no tiene participaciones completas.
El Libro Inventario se conserva como lineas de balance anual en diciembre para
que el mirror genere `AnnualTaxTrialBalanceLine` desde cuentas controladas
reales de entrada.
El selector de libros anuales queda acotado al `commercial_year`: si el
manifiesto contiene artefactos de otros anos, carpetas historicas o respaldos
pendientes con el mismo `artifact_key`, el draft prioriza la fuente anual
canonica compatible y no usa copias posteriores como insumo AC2024. Con
`ownership` local controlado desde fuente societaria revisada, la prueba espejo
AC2024/AT2025 puede pasar writer y mirror anual
(`ready_for_annual_generation=true`) y generar ProcesoRentaAnual, DDJJ/F22
preparados, matriz, dossier, export y checklist. El mirror tambien emite
`TaxSupportDocument` como `DocumentoEmitido` de tipo `respaldo_tributario`,
usando el generador PDF canonico de Documentos con preview auditada y checksum
de contenido. La seccion de bienes raices queda lista para
`AnnualRealEstateItem` cuando el paquete incluye `real_estate` y la DB ya tiene
ownership suficiente para materializar `Propiedad`; en la corrida real actual,
ese es el prerequisito que falta antes de despejar
`stage6.real_estate_item_missing`. Esto no convierte el expediente en
presentacion SII real ni calculo tributario final.
`audit_annual_tax_mirror_proof` es el gate local de conclusion para esta prueba
espejo: combina readiness de fuente/manifiesto, arquitectura espejo, comparador
de outputs esperados, readiness Etapa 6 y boundary de seguridad. Debe quedar
`parcial` si cualquier artefacto requiere revision responsable o si falta
fuente/gate externo, aunque los componentes tecnicos existan. Su salida permite
distinguir avance preparado, prueba arquitectonica, bloqueo externo y cierre
real, sin usar SII real, credenciales, `.env`, EDIG ejecutable ni outputs
finales como input.
Cuando el manifiesto historico todavia marca `ownership_source_missing`, el
proof puede recibir evidencia posterior redactada de ownership mediante
`--ownership-evidence`: salida de `validate_annual_tax_ownership_patch` o de
`build_annual_tax_ownership_review_checklist`, sin nombres, RUTs, texto bruto
ni rutas crudas. Si esa evidencia esta lista y el piloto de libros cerrados ya
tenia las demas fuentes, `source_documentation_confirmed` queda verdadero sin
reescribir el manifiesto ni versionar PII. Del mismo modo, si la comparacion
ejecutada queda `ready_for_mirror_conclusion=true` y sin blockers de valores,
el proof cierra la brecha estatica `expected_output_value_equality_completion`
para esa corrida. Esto no abre SII, no convierte outputs esperados en insumo y
no reemplaza la validacion experta.
`scripts/run-stage6-mirror-proof-gate.ps1` es la entrada operativa canonica al
gate espejo: valida refs no sensibles, rechaza outputs/manifiestos dentro del
repo fuera de `local-evidence/`, bloquea migraciones contra `real_autorizado` y
acepta `-OwnershipEvidencePath` solo como JSON bajo una ruta permitida. Usa
`--fail-on-incomplete` solo cuando se quiere exigir completitud probada. El
comando Django queda como motor; el wrapper es el camino seguro para runs
manuales o evidenciales.
`compare_annual_tax_expected_outputs` distingue errores de extraccion
diagnosticos de errores bloqueantes para identidad, semantica documental y
valores esperados. Los errores siguen registrados en `extraction_errors`, pero
el resumen expone `blocking_extraction_errors_total` y solo bloquea cuando falta
la evidencia decisiva de la misma familia: DDJJ aceptadas esperadas, F22
trazable, Balance, registros anuales, documentos generados comparables o el
unico archivo disponible para un par `category/artifact_key` generado. Archivos
historicos, baseline, rechazados o no decisivos no deben reabrir
`expected_output_identity_extraction_errors`,
`expected_output_document_semantic_extraction_errors`,
`expected_output_value_extraction_errors` ni
`expected_output_value_extractors_partial` cuando esas senales decisivas ya
estan presentes. Esto no declara igualdad numerica final; conserva
`expected_output_value_mismatch` y `expected_output_value_extractors_missing`
cuando los valores comparables siguen pendientes o incompletos.
Cuando el manifiesto contiene varios archivos para el mismo artefacto esperado,
por ejemplo varias paginas o versiones de `balance_general`,
`extract_expected_output_value_signals` une los tokens por
`category/artifact_key` antes de comparar. Esto evita que el ultimo archivo del
manifiesto sobrescriba senales de Balance ya extraidas; en la prueba AC2024/AT2025
la comparacion de valores queda `138/138` sin blockers del comparador. El mirror
proof total permanece parcial si Stage 6 aun reporta registros empresariales
invalidos o bienes raices faltantes.
Los movimientos de registros empresariales generados desde RLI/CPT deben
calcular `hash_movimiento` desde la instancia normalizada, no desde el payload
previo a persistencia. Esto evita falsos `stage6.enterprise_register_movement_invalid`
por diferencias de representacion decimal/textual y mantiene RAI/SAC trazables
al payload canonico validado por el modelo. En la prueba AC2024/AT2025 el
readiness queda sin movimientos empresariales invalidos y el siguiente bloqueo
real pasa por bienes raices, condicionado por cargar `ownership` controlado
antes de escribir `Propiedad` activa.
`MonthlyTaxFact` materializa la capa mensual anualizable: por cada empresa,
ano comercial y mes normaliza el cierre aprobado, obligaciones mensuales,
F29 si existe, distribuciones de arriendo y liquidacion de empresa, con
`hash_hecho` del resumen mensual, refs no sensibles y exposicion redactada en
API/snapshot/admin. Esto mantiene la union contabilidad -> renta como
transformacion trazable, no como salto directo desde asientos a F22.
Si existen trabajadores, sueldo empresarial o DJ1887 aplicable, los hechos
mensuales/anuales deben recibir una fuente laboral/previsional revisable
externa o propia: liquidaciones resumidas, cotizaciones, Previred, LRE, DJ1887,
certificados, impuesto unico y asiento/centralizacion contable. Sin esa fuente
la preparacion anual conserva warning de fuente laboral no cargada cuando el
caso lo requiera; no se inventan remuneraciones desde EDIG ni desde IA libre.
Desde 2026-06-16, una DJ1887 aceptada en el manifiesto AC/AT activa
`labor_previsional_source`: `build_annual_tax_source_manifest` no considera
lista la fuente espejo si falta `payroll_support`, el plan/template arrastran
`labor_previsional.required=true`, y readiness/writer bloquean paquetes que no
declaren `labor_previsional.source_ref` no sensible. Esto conserva
Remuneraciones como fuente revisable, no como payroll autonomo ni calculo final.
El draft controlado de valores puede completar ese `source_ref` anual solo
cuando todas las fuentes `payroll_support` esperadas fueron leidas y revisadas
por el parser local permitido; la referencia generada es no sensible y mantiene
`final_tax_calculation=false`.
`AnnualTaxTrialBalance` y `AnnualTaxTrialBalanceLine` materializan la capa
anual de balance de ocho columnas entre contabilidad y RLI/CPT/DJ1847: toman
un `BalanceComprobacion` aprobado de diciembre, una fuente oficial/experta
revisada y el rule set anual para generar lineas por cuenta, clasificador,
sumas, saldos, inventario y resultado. Esta capa es evidencia preparatoria
para revision tributaria; no calcula ni presenta renta final.
`TaxCodeMapping` no puede usar metricas `annual_trial_balance.*` de forma
ambigua: para mappings activos bajo rule set aprobado, esa fuente solo puede
alimentar RLI/CPT y debe indicar `trial_balance_classifier` DJ1847 trazable.
Esto impide saltar desde balance anual directo a F22/DDJJ o preparar workbooks
sin clasificador contable tributario.
`AnnualTaxWorkbook` y `AnnualTaxWorkbookLine` materializan el primer esqueleto
RLI/CPT: para cada `ProcesoRentaAnual` se preparan workbooks RLI y CPT desde
`TaxCodeMapping` aprobado, `MonthlyTaxFact` y, cuando el mapping lo exige,
`AnnualTaxTrialBalance`, con hashes por linea/workbook, warnings revisables y
exposicion redactada. `warning_review_ref` permite registrar revision
responsable no sensible de warnings de linea sin borrar advertencias ni
promover calculo final. Esta capa no declara calculo tributario final; deja
importes, origenes y advertencias listos para revision antes de avanzar a
RAI/SAC/DDJJ/F22.
Los resumenes y checklist solo consideran revisados los warnings con referencia
no sensible; una URL, token o valor sensible no despeja la revision pendiente.
`AnnualEnterpriseRegisterSet` y `AnnualEnterpriseRegisterMovement` materializan
la siguiente capa: registros RAI, SAC, retiros y dividendos por proceso anual,
con saldos iniciales/finales, movimientos trazados a RLI/CPT o participaciones
activas, hashes por movimiento/registro y exposicion redactada. Esta capa
mantiene `final_tax_calculation=false`; no reemplaza revision tributaria ni
presentacion SII.
`AnnualRealEstateSection` y `AnnualRealEstateItem` materializan la seccion
anual de bienes raices/arriendos: preparan items por propiedad desde
`Propiedad`, `DistribucionCobroMensual` y `ContratoPropiedad`, distribuyen
arriendos por porcentaje interno, congelan snapshots anuales con hash y dejan
contribuciones como fuente `not_loaded_v1` hasta contar con respaldo oficial o
experto. Cuando existe `AnnualTaxOfficialSource` de contribuciones/bienes
raices o revision experta con alcance F22/Dossier, la seccion la enlaza como
fuente preparatoria revisable y toma montos solo desde
`AnnualTaxSourceBundle.resumen_fuentes.real_estate_contribuciones.values_by_property_id`.
Si falta fuente o valor por propiedad, conserva warning de cierre. Esta capa
alimenta el dossier y la matriz DDJJ/F22, pero no declara calculo fiscal final
ni presentacion SII.
`AnnualTaxArtifactMatrix` y `AnnualTaxArtifactMatrixItem` materializan la
matriz anual DDJJ/F22: conectan configuracion fiscal, mapeos tributarios,
source bundle, resumen anual, RLI/CPT, registros empresariales y bienes
raices con destinos DDJJ/F22 revisables. Cada item conserva fuente, medio SII,
responsable, payload no sensible, hash, estado de revision y
`final_tax_calculation=false`; no declara formato final SII ni presentacion
autonoma.
`AnnualTaxDossier` materializa el paquete anual revisable: consolida source
bundle, hechos mensuales, RLI/CPT, registros empresariales, bienes raices y
matriz DDJJ/F22 en un resumen hasheado con responsable y referencias no
sensibles. El dossier conserva `final_tax_calculation=false` y
`sii_submission=false`; sirve para revision experta/oficial antes de cualquier
export o presentacion, no para que LeaseManager decida la renta final.
`AnnualTaxExport` materializa el preview/export local controlado: empaqueta el
dossier y la matriz DDJJ/F22 en un payload hasheado, con refs no sensibles,
responsable, conteos DDJJ/F22 y flags obligatorios `official_format=false`,
`sii_submission=false` y `final_tax_calculation=false`. Es una salida revisable
del motor anual, no un formato oficial SII ni una presentacion.
`AnnualTaxReviewChecklist` materializa la revision responsable previa a
cualquier aprobacion: toma dossier, export local, source bundle, rule set y
matriz DDJJ/F22, arma items de control por categoria, conserva refs no
sensibles, evidencia, conteos y hash. El checklist no decide la renta final ni
declara formato oficial, presentacion SII o calculo fiscal autonomo; solo deja
preparado un paquete auditable para responsable experto/oficial.
`RENTA_ANUAL_OFFICIAL_SOURCE_GAPS_AT2026.md` fija la matriz de brechas
oficiales: DTE queda como integracion tecnica separada bajo gate; F29, DDJJ,
DJ1847/RLI/CPT, F22, bienes raices/contribuciones y automatizacion por
navegador quedan limitados a preparacion revisable hasta fuente SII/experta,
formato/certificacion, responsable y autorizacion explicita. La prioridad
posterior al mapeo EDIG es bajar fuentes SII AT2026 a reglas versionadas,
partiendo por balance de 8 columnas/DJ1847, RLI/CPT, DDJJ por formulario,
contribuciones y formato/certificacion F22; no seguir copiando ni ejecutando
EDIG.
`AnnualTaxOfficialSource` materializa ese registro de fuentes oficiales o
expertas: conserva ano tributario, tipo, URL publica SII segura cuando aplica,
referencia no sensible, hash SHA-256, fecha de recuperacion, responsable,
alcance y destino RLI/CPT/RAI/SAC/DDJJ/F22/Dossier. API, snapshot y admin
redactan refs, notas y metadata sensibles; readiness bloquea fuentes invalidas
sin exponer valores.
`AnnualTaxDDJJFormLayout` materializa la capa DDJJ por ano tributario y
formulario: conserva medios SII permitidos, medio preferente, vencimiento,
certificado, resolucion, refs de layout/instrucciones/responsable, fuente
oficial/experta y `hash_layout`. API, snapshot y admin redactan refs/payloads
sensibles. Esta capa alimenta la matriz DDJJ/F22 como preparacion revisable;
no declara formato oficial SII, calculo tributario final ni presentacion
autonoma.
`AnnualTaxF22ExportLayout` materializa la capa F22 por ano tributario antes del
export local: conserva `form_code=F22`, medio preferente, refs no sensibles de
certificacion/formato/instrucciones/responsable, fuentes oficiales/expertas,
warnings, `source_payload` y `hash_layout`. El layout puede alimentar la matriz
DDJJ/F22 con `source_kind=f22_export_layout`, pero mantiene obligatoriamente
`official_format=false`, `sii_submission=false` y
`final_tax_calculation=false`. Sirve para preparar y revisar el paquete F22; no
presenta, no sube y no decide la renta final.
`audit_company_accounting_progress` funciona como cursor operativo por empresa
y ano comercial: consolida en JSON si la empresa tiene configuracion fiscal,
doce cierres, balances aprobados/cuadrados, F29, `ProcesoRentaAnual`,
`AnnualTaxTrialBalance`, workbooks RLI/CPT, dossier y export local. Esto permite
responder el avance de una empresa piloto sin leer datos reales por defecto ni
confundir preparacion tecnica con cierre tributario. La bandera
`ready_for_company_accounting_review` solo significa lista para revision
responsable.
El payload conserva `review_boundary`: incluso con progreso local completo,
`autonomous_accounting=false`, `final_tax_calculation=false`,
`sii_submission=false`, `requires_responsible_review=true` y
`requires_expert_or_official_validation=true`. La accion permitida es revision
asistida por responsable; quedan fuera contabilidad autonoma, calculo
tributario final sin revision y presentacion SII automatica.
El mismo diagnostico queda disponible en Reporting como
`contabilidad/progreso-empresa/`, para que el avance de una empresa piloto se
consulte con `empresa_id` y `fiscal_year` antes de iniciar afirmaciones de
cierre anual. La vista conserva el boundary: no calcula renta final, no sube
F22/DDJJ, no usa SII real y no reemplaza revision tributaria experta. La
trazabilidad del reporte refleja los mismos controles para que el backoffice no
convierta un estado revisable en cierre anual autonomo.
El selector `audit_company_accounting_candidates` y la vista Reporting
`contabilidad/candidatos-progreso-empresa/` priorizan empresas y anos con
senales locales de cierre, balances, F29, proceso anual, balance tributario,
RLI/CPT, dossier y export. Sirve para elegir que expediente revisar primero;
no habilita calculo tributario final, upload SII ni presentacion autonoma.
El selector expone `selection_boundary` para indicar que solo ordena candidatos
con senales internas, sin fuentes externas, sin gates externos y sin habilitar
contabilidad autonoma.
Para F29 mensual, el progreso anual cuenta tanto formularios preparados como
meses con `MonthlyTaxFact` normalizado cuyo F29 esta `no_aplica` y
`no_declaration=true`. Esto permite modelar periodos AC2024 registrados como
sin declaracion sin convertirlos en F29 ficticios ni tratarlos como brecha de
fuente. En Inmobiliaria Puig AC2024/AT2025, esa distincion desplaza el bloqueo
de progreso desde F29 hacia la capa anual (`ProcesoRentaAnual`).
La senal `annual_process` solo cuenta si el `ProcesoRentaAnual` preparado o
superior esta enlazado a un `AnnualTaxSourceBundle` congelado. Un proceso anual
sin source bundle congelado se reporta como
`company_accounting.annual_process_source_bundle_missing`, porque la preparacion
anual debe nacer de fuentes congeladas antes de tratarse como expediente
revisable.
La sincronizacion anual de hechos mensuales conserva esa condicion: si
`run_annual_tax_controlled_mirror` vuelve a ejecutar `sync_monthly_tax_facts`
y no existe `F29PreparacionMensual` para un mes, pero el hecho mensual vigente
trae F29 `no_aplica` + `no_declaration=true`, la marca controlada se preserva
en el nuevo payload y el progreso no vuelve a degradarse a F29 faltante. En la
prueba AC2024/AT2025 regenerada, el expediente queda 100% preparado para
revision responsable despues del mirror anual, sin declarar cierre tributario
final ni presentacion SII.
Tanto el selector como el auditor por empresa exponen si la configuracion
fiscal activa pertenece al regimen automatizable v1
`EmpresaContabilidadCompletaV1`; si no corresponde, conservan las senales
locales pero bloquean `ready_for_company_accounting_review` con issue explicito.

## Gate

- Cierres mensuales completos.
- Reglas tributarias validadas.
- `ConfiguracionFiscalEmpresa` activa de la empresa dentro del regimen
  automatizable v1 `EmpresaContabilidadCompletaV1`; otros regimenes pueden
  existir como dato operativo, pero no habilitan automatizacion contable/renta
  sin gate, ADR y validacion oficial/experta.
- `TaxYearRuleSet` aprobado para el ano tributario y regimen fiscal de la
  empresa, con `hash_normativo`, fuente y responsable no sensibles, y enlace a
  `AnnualTaxOfficialSource` revisada/aprobada del mismo AT y regimen
  compatible cuando la fuente declare regimen.
- `TaxCodeMapping` activo y trazable para el rule set antes de preparar
  ProcesoRentaAnual/DDJJ/F22; si pertenece a un rule set aprobado debe enlazar
  una `AnnualTaxOfficialSource` revisada/aprobada del mismo AT, destino
  RLI/CPT/RAI/SAC/DDJJ/F22 compatible cuando aplique y regimen compatible
  cuando la fuente declare regimen.
- `AnnualTaxSourceBundle` congelado por empresa/ano tributario antes de
  preparar ProcesoRentaAnual/DDJJ/F22; debe tener doce cierres aprobados,
  obligaciones mensuales trazables, refs no sensibles y `hash_fuentes`
  coherente con `resumen_fuentes`.
- `MonthlyTaxFact` normalizado por empresa/ano/mes antes de tratar un proceso
  anual como trazable. Deben existir doce meses normalizados para el ano
  comercial y `ProcesoRentaAnual.resumen_anual.annual_tax_monthly_facts` debe
  coincidir con esos hechos.
- `AnnualTaxTrialBalance` preparado requiere proceso anual, source bundle,
  rule set, fuente oficial/experta y `BalanceComprobacion` aprobado del cierre
  de diciembre de la misma empresa. Debe conservar lineas activas,
  `resumen_balance`, `hash_balance`, refs no sensibles y resumen alineado en
  `ProcesoRentaAnual.resumen_anual.annual_tax_trial_balances`.
- `AnnualTaxTrialBalanceLine` activa requiere cuenta contable de la misma
  empresa, clasificador DJ1847/RLI/CPT, montos no negativos de ocho columnas,
  formula/evidencia no sensibles, `source_payload` y `hash_linea` coherente.
  Cualquier warning de linea o del balance agregado bloquea readiness hasta
  revision tributaria.
- `TaxCodeMapping` activo bajo `TaxYearRuleSet` aprobado que declare
  `source_metric=annual_trial_balance.*` debe apuntar solo a RLI/CPT y
  conservar `trial_balance_classifier`; mappings heredados sin ese clasificador
  o apuntando directo a destinos posteriores bloquean readiness.
- `AnnualTaxWorkbook` preparado para RLI y CPT antes de tratar un proceso anual
  como trazable. Ambos workbooks deben pertenecer al mismo proceso, rule set,
  bundle y empresa, conservar `hash_workbook` coherente y aparecer en
  `ProcesoRentaAnual.resumen_anual.annual_tax_workbooks`.
- `AnnualTaxWorkbookLine` activa requiere `TaxCodeMapping` del mismo rule set,
  origen, monto, `formula_ref`, `evidencia_ref`, `source_payload` y
  `hash_linea` coherente. Lineas con warnings bloquean readiness mientras no
  tengan `warning_review_ref` no sensible; las revisadas conservan el warning
  en payload/hash y no se transforman en cierre automatico.
- `AnnualEnterpriseRegisterSet` preparado requiere proceso anual, bundle y rule
  set coherentes, saldos iniciales/finales trazables, `resumen_registro` y
  `hash_registro` coherentes. Para tratar un proceso anual como trazable deben
  existir registros RAI, SAC, retiros y dividendos.
- `AnnualEnterpriseRegisterMovement` activo requiere origen, monto, signo,
  `formula_ref`, `evidencia_ref`, `source_payload` y `hash_movimiento`
  coherente. Movimientos con warnings bloquean readiness mientras no tengan
  `warning_review_ref` no sensible; las revisiones conservan warnings dentro
  del hash y no convierten el registro en calculo final. Retiros/dividendos
  pueden conservar movimientos cero trazados a participaciones activas mientras
  no existan eventos propios.
- `AnnualRealEstateSection` preparada requiere proceso anual, bundle y rule
  set coherentes, `resumen_seccion` y `hash_seccion` coherentes. Para tratar un
  proceso anual como trazable debe existir una seccion preparada y su resumen
  debe coincidir con `ProcesoRentaAnual.resumen_anual.annual_real_estate_sections`.
  Si la seccion no enlaza fuente oficial/experta de contribuciones o un item
  activo no tiene monto de contribuciones trazado por propiedad, readiness
  conserva bloqueo explicito de cierre.
- `AnnualRealEstateItem` activo requiere snapshot anual completo de propiedad,
  montos no negativos, `formula_ref`, `evidencia_ref`, `source_payload` y
  `hash_item` coherente. El snapshot anual queda congelado: cambios posteriores
  en la ficha maestra de la propiedad no invalidan evidencia ya preparada,
  siempre que el hash del item se mantenga vigente.
- `AnnualTaxDDJJFormLayout` preparado requiere una fila por cada formulario
  habilitado en `ConfiguracionFiscalEmpresa.ddjj_habilitadas`, fuente
  oficial/experta lista del mismo ano tributario y aplicable a DDJJ, medio
  preferente permitido, refs no sensibles, `source_payload` dict y
  `hash_layout` coherente. Para tratar un proceso anual como trazable, su
  resumen `annual_tax_ddjj_layouts` debe coincidir con los layouts preparados.
  Layouts invalidos, faltantes, desalineados o con warnings bloquean readiness
  hasta revision tributaria.
- `AnnualTaxF22ExportLayout` preparado requiere una fila `F22` por ano
  tributario, fuente oficial/experta lista del mismo ano y aplicable a F22,
  medio preferente permitido, refs no sensibles de certificacion/formato/
  instrucciones/responsable, `source_payload` dict y `hash_layout` coherente.
- El avance de una empresa piloto debe medirse con
  `audit_company_accounting_progress --empresa-id <id> --fiscal-year <ano>`
  antes de declarar que su contabilidad o renta esta cerrada. La salida local
  puede guardarse en `local-evidence/`; fuera de ese directorio no debe
  versionarse evidencia contable ni tributaria.
  Para tratar un proceso anual como trazable, su resumen
  `annual_tax_f22_export_layouts` debe coincidir con el layout preparado.
  Layouts invalidos, faltantes, desalineados, con warnings o payloads que
  intenten formato oficial, presentacion SII o calculo final bloquean readiness.
- `AnnualTaxArtifactMatrix` preparada requiere proceso anual, bundle, rule set,
  configuracion fiscal activa, refs no sensibles, conteos DDJJ/F22, resumen e
  `hash_matriz` coherentes. Para tratar un proceso anual como trazable debe
  existir una matriz preparada y su resumen debe coincidir con
  `ProcesoRentaAnual.resumen_anual.annual_tax_artifact_matrices`.
- `AnnualTaxArtifactMatrixItem` activo requiere destino DDJJ/F22, codigo,
  medio SII, fuente, modelo origen, `formula_ref`, `evidencia_ref`,
  `responsible_ref`, `source_payload` y `hash_item` coherente. Items con
  warnings o estado `bloqueado` bloquean readiness hasta revision tributaria.
- `AnnualTaxDossier` preparado requiere proceso anual, source bundle, rule set,
  matriz DDJJ/F22 y configuracion fiscal activa coherentes; refs no sensibles,
  responsable, `dossier_ref`, conteos anuales, `resumen_dossier` y
  `hash_dossier` alineados. Para tratar un proceso anual como trazable debe
  existir un dossier preparado y su resumen debe coincidir con
  `ProcesoRentaAnual.resumen_anual.annual_tax_dossiers`.
- `AnnualTaxDossier.resumen_dossier` no puede declarar `official_format`,
  `sii_submission`, `sii_submission_attempted` ni `final_tax_calculation` como
  verdaderos. El dossier es expediente revisable, no formato oficial, calculo
  fiscal final ni evidencia de presentacion SII.
- Un dossier con warnings o estado `requiere_revision` puede alimentar un
  export local de revision, pero bloquea readiness hasta revision tributaria
  responsable; un dossier `bloqueado` no se convierte en export ni presentacion
  SII por conveniencia.
- `AnnualTaxExport` preparado requiere proceso anual, source bundle, rule set,
  matriz DDJJ/F22 y dossier coherentes; refs no sensibles, responsable,
  `export_ref`, payload exportable, `hash_export`, conteos DDJJ/F22 y resumen
  en `ProcesoRentaAnual.resumen_anual.annual_tax_exports` alineados.
- `AnnualTaxExport` bloquea readiness si falta, si esta desalineado, si contiene
  refs/payloads sensibles, si hay revision pendiente o si intenta declarar
  formato oficial SII, presentacion SII o calculo fiscal final autonomo.
- `AnnualTaxReviewChecklist` preparado requiere proceso anual, dossier, export
  local, source bundle, rule set y matriz DDJJ/F22 coherentes; refs no
  sensibles, responsable, evidencia, `review_payload`, `hash_checklist`,
  conteos de items, warnings y bloqueos alineados. Para tratar un proceso anual
  como trazable debe existir checklist preparado y su resumen debe coincidir
  con `ProcesoRentaAnual.resumen_anual.annual_tax_review_checklists`.
- `AnnualTaxReviewChecklist.review_payload` no puede declarar
  `official_format`, `sii_submission`, `sii_submission_attempted` ni
  `final_tax_calculation` como verdaderos. Si el checklist conserva items
  incompletos, warnings o bloqueos, readiness exige revision responsable antes
  de cualquier cierre.
- Para workbooks RLI/CPT y registros empresariales, el checklist distingue
  `warnings_total` de `warnings_pending_review_total`: los warnings ya
  revisados con referencia no sensible quedan visibles como advertencia
  historica, pero no mantienen el item en `warning` ni disparan
  `stage6.tax_review_checklist_warning_review_required`.
- Las revisiones de warnings de workbooks, matriz DDJJ/F22 y dossier solo
  cuentan como revisadas cuando `warning_review_ref` es una referencia no
  sensible. URLs, tokens, credenciales o refs sensibles heredadas se mantienen
  como warnings pendientes, bloquean readiness y no pueden propagarse al
  dossier/export como evidencia valida.
- El mirror proof expone `comparison_generated_artifact_evidence` con ids,
  hashes, conteos y refs redactadas de balance anual, RLI/CPT, registros,
  DDJJ/F22, matriz, dossier, export y checklist. No incluye payloads crudos,
  `resumen_*`, textos esperados, montos crudos ni secretos; sirve para ubicar
  que artefacto generado falta revisar sin convertirlo en calculo final.
- La matriz `stage6-official-source-gaps` debe mantenerse alineada con fuentes
  SII vigentes antes de promover cualquier warning de regla, medio DDJJ,
  mapping DJ1847/RLI/CPT, contribucion o formato F22 a estado cerrable.
- `AnnualTaxOfficialSource` revisada/aprobada requiere `source_url` publica SII
  segura si la fuente es SII, `source_ref`, `source_hash`, `retrieved_on` y
  `responsible_ref` no sensibles; `retrieved_on` no puede ser futuro. Fuentes
  invalidas o con URLs/refs/payloads sensibles bloquean readiness.
- Una certificacion tecnica F22, F29 o DDJJ acredita formato/recepcion en el
  alcance descrito por SII; no reemplaza validacion tributaria del contenido ni
  revision responsable.
- `generate_annual_preparation()` sincroniza bienes raices/arriendos despues
  de RLI/CPT y registros empresariales, antes de emitir DDJJ/F22 locales. La
  readiness bloquea procesos trazables sin seccion inmobiliaria, sin items
  activos, con resumen desalineado, invalidos o con warnings pendientes.
- `generate_annual_preparation()` resume `AnnualTaxDDJJFormLayout` y
  `AnnualTaxF22ExportLayout` antes de sincronizar la matriz DDJJ/F22. La
  readiness bloquea procesos trazables sin layout preparado por formulario DDJJ
  habilitado o sin layout F22 preparado, con resumen desalineado, layouts
  invalidos o warnings pendientes, manteniendo DDJJ/F22 como insumos revisables
  y no como presentacion SII.
- `generate_annual_preparation()` sincroniza la matriz DDJJ/F22 despues de
  RLI/CPT, registros empresariales y bienes raices, antes de emitir DDJJ/F22
  locales. La readiness bloquea procesos trazables sin matriz, sin items DDJJ
  o F22, con resumen desalineado, invalidos, con warnings pendientes o items
  bloqueados.
- `generate_annual_preparation()` sincroniza `AnnualTaxDossier` despues de la
  matriz DDJJ/F22 y antes de emitir DDJJ/F22 locales. La readiness bloquea
  procesos trazables sin dossier, con resumen desalineado, refs faltantes,
  invalidos o con revision pendiente.
- `generate_annual_preparation()` sincroniza `AnnualTaxExport` despues de crear
  DDJJ/F22 locales. La readiness bloquea procesos trazables sin export/preview
  controlado, con resumen desalineado, invalidos, refs faltantes o cualquier
  intento de presentacion/formato oficial/calculo final.
- `generate_annual_preparation()` sincroniza `AnnualTaxReviewChecklist` despues
  del export local controlado. La readiness bloquea procesos trazables sin
  checklist, con resumen desalineado, invalidos, refs/evidencia faltantes,
  items incompletos, warnings, bloqueos o cualquier intento de formato oficial,
  presentacion SII o calculo final autonomo.
- Responsable de revision anual trazado antes de tratar el paquete como
  aprobado.
- Documentos generados desde datos trazables.
- Evidencia sin datos sensibles expuestos.
- Capacidades DDJJ/F22, ProcesoRentaAnual, DDJJ y F22 pertenecen a empresas
  con `ConfiguracionFiscalEmpresa` activa propia; el dominio/API rechaza
  nuevas escrituras que no cumplan esa regla.
- `audit_stage6_renta_anual_readiness` consolida configuracion fiscal,
  capacidades DDJJ/F22, doce cierres, obligaciones mensuales, proceso anual,
  respaldos tributarios PDF y referencias finales no sensibles sin conectar SII
  ni leer certificados reales.
- El readiness de Etapa 6 puede declarar preparacion local, brecha o bloqueo de
  cierre; no declara presentacion anual final ni sustituye criterio tributario.
- `ProcesoRentaAnual.resumen_anual`, `DDJJPreparacionAnual.resumen_paquete`
  y `F22PreparacionAnual.resumen_f22` deben trazar al ano comercial
  inmediatamente anterior al `anio_tributario`; el dominio rechaza nuevas
  escrituras desalineadas y readiness bloquea snapshots heredados.
- El dominio SII rechaza F29, ProcesoRentaAnual, DDJJ y F22 en estados
  aprobados, presentados, observados o rectificados si falta la referencia
  final trazable correspondiente.
- El dominio SII rechaza ProcesoRentaAnual, DDJJ y F22 en estados aprobados,
  presentados, observados o rectificados si falta `responsable_revision_ref` no
  sensible. El responsable de revision queda separado de la referencia externa
  del paquete para reforzar que LeaseManager prepara dossiers revisables, no
  decide ni presenta renta final de forma autonoma.
- Las APIs que generan ProcesoRentaAnual/DDJJ/F22 o actualizan estados DDJJ/F22
  persisten la mutacion y su auditoria de vista en una misma transaccion. Si
  falla la auditoria, no debe quedar proceso anual, preparacion ni referencia
  final mutada sin traza de endpoint.
- Los eventos `sii.ddjj_preparacion.status_updated` y
  `sii.f22_preparacion.status_updated` deben conservar metadata minima de
  transicion con `campo_estado`, `estado_anterior` y `estado_nuevo`;
  `audit_stage6_renta_anual_readiness` bloquea snapshots heredados sin esa
  metadata.
- Esos mismos eventos, cuando avanzan DDJJ/F22 a estados aprobados, observados
  o rectificados, deben conservar `responsable_revision_ref` no sensible en la
  metadata auditada. `audit_stage6_renta_anual_readiness` bloquea eventos
  heredados sin responsable auditado o con referencia sensible usando codigos
  `stage6.audit.annual_status_responsible_ref_missing` y
  `stage6.audit.annual_status_responsible_ref_sensitive`, sin exponer valores.
- El backoffice SII solo permite actualizar revision anual DDJJ/F22 mediante
  formulario explicito con artefacto, estado, referencia, observacion no
  sensible y `responsable_revision_ref`; no debe existir accion rapida que
  avance estados anuales sin responsable revisable.
- `audit_stage6_renta_anual_readiness` clasifica explicitamente como
  bloqueantes las referencias finales sensibles en ProcesoRentaAnual, DDJJ y
  F22, sin exponer esos valores.
- `audit_stage6_renta_anual_readiness` clasifica explicitamente como
  bloqueantes ProcesoRentaAnual, DDJJ o F22 avanzados sin
  `responsable_revision_ref`, o con una referencia sensible, usando codigos
  `stage6.*_responsible_ref_missing` y
  `stage6.*_responsible_ref_sensitive`.
- El dominio SII tambien rechaza ProcesoRentaAnual, DDJJ y F22 asociados a
  empresas sin `ConfiguracionFiscalEmpresa` activa propia.
- Los payloads anuales y referencias de DDJJ/F22 heredadas se entregan a
  reporting con redaccion antes de exponerse al backoffice.
- El admin Django de SII expone ProcesoRentaAnual, DDJJ y F22 solo con
  versiones redactadas de refs finales, payloads anuales y observaciones
  heredadas, sin busquedas por los campos crudos ni alta manual desde
  backoffice.
- `audit_stage6_renta_anual_readiness` clasifica como bloqueantes los payloads
  anuales heredados con URLs, tokens, credenciales, correos o claves sensibles
  en `resumen_anual`, `resumen_paquete` o `resumen_f22`, sin imprimir esos
  valores.
- `audit_stage6_renta_anual_readiness` solo puede cerrar con `--source-kind`
  `snapshot_controlado` o `real_autorizado`; `local`, `fixture` y `demo`
  diagnostican brechas pero no habilitan cierre de Etapa 6.
- Una fuente evidencial debe incluir `--source-label` y
  `--authorization-ref` no sensibles. Sin esas refs, el tipo de fuente queda
  reconocido pero no puede cerrar Etapa 6.
- Si `--source-label` o `--authorization-ref` contienen URL, token, credencial
  o valor sensible, readiness debe clasificar `stage6.source_label_sensitive`
  o `stage6.authorization_ref_sensitive`, exponer solo
  `sections.source_trace_sensitive` y no mezclarlo con refs faltantes.
- Las referencias finales de cierre (`Stage5EvidenceRef`,
  `Stage4SiiEvidenceRef`, `FiscalRuleRef`, `CertificatesProofRef` y
  `ResponsibleRef`) tambien deben ser no sensibles. Si contienen URL, token,
  credencial o valor sensible, readiness debe clasificar
  `stage6.*_ref_sensitive`, exponer `sections.final_evidence_sensitive` y no
  mezclarlas con refs faltantes.
- `scripts/run-stage6-readiness-gate.ps1` ejecuta el diagnostico local con
  SQLite efimero bajo `local-evidence/`, no conecta SII, no lee `.env`, no usa
  certificados y reserva `-RequireReady` para fuentes autorizadas con refs
  trazables de Etapa 5, Etapa 4 SII, regla fiscal, certificados y responsable.
- `scripts/run-stage6-mirror-proof-gate.ps1` ejecuta la prueba espejo
  AC2024/AT2025 desde un manifiesto controlado y salida bajo `local-evidence/`.
  El wrapper rechaza referencias sensibles, manifiestos/versionado fuera de
  evidencia local, `source-root` versionado fuera de evidencia local y
  `-RunMigrations` con `real_autorizado`. Su resultado puede quedar parcial sin
  cerrar renta cuando hay revision responsable pendiente.
- El mapeo anual automatizable debe declarar explicitamente su fuente: dato
  LeaseManager, cierre, ledger, F29/PPM, certificado, regla AT, DDJJ o decision
  responsable. Ningun codigo F22/DDJJ queda automatizado solo por inferencia de
  EDIG o por coincidencia visual de plantilla.
- `generate_annual_preparation()` rechaza preparar ProcesoRentaAnual/DDJJ/F22
  si falta `TaxYearRuleSet` aprobado o si sus `TaxCodeMapping` activos no pasan
  validacion de dominio. El resumen anual conserva solo metadata no sensible de
  la regla aplicada: AT, regimen, version, hash y conteos por destino.
- `generate_annual_preparation()` congela o reutiliza un
  `AnnualTaxSourceBundle` local antes de crear ProcesoRentaAnual/DDJJ/F22. El
  proceso anual conserva id/hash del bundle, y
  `audit_stage6_renta_anual_readiness` bloquea procesos heredados sin bundle,
  con bundle no congelado, desalineado o con metadata/hash distinta.
- `generate_annual_preparation()` sincroniza `MonthlyTaxFact` desde los cierres
  aprobados antes de construir el resumen anual. La readiness bloquea hechos
  mensuales invalidos, faltantes, sin configuracion fiscal activa o procesos
  cuyo resumen mensual quede desalineado.
- `generate_annual_preparation()` sincroniza `AnnualTaxTrialBalance` desde el
  balance aprobado de diciembre antes de construir workbooks RLI/CPT. Si no
  existe balance/fuente revisada, la generacion puede seguir como preparacion
  local, pero readiness bloquea el proceso trazable hasta completar esa capa.
- `generate_annual_preparation()` sincroniza workbooks RLI/CPT despues de crear
  el proceso anual y el balance anual cuando corresponda, antes de emitir
  DDJJ/F22 locales. La readiness bloquea procesos trazables sin ambos
  workbooks, sin lineas activas, con warnings pendientes de revision, invalidos
  o con resumen RLI/CPT desalineado.
- `generate_annual_preparation()` sincroniza registros empresariales despues de
  RLI/CPT y antes de emitir DDJJ/F22 locales. La readiness bloquea procesos
  trazables sin RAI/SAC/retiros/dividendos, sin movimientos activos, con
  warnings, invalidos o con resumen empresarial desalineado.
- La API/snapshot/admin de SII exponen `TaxYearRuleSet` y `TaxCodeMapping` con
  referencias/payloads redactados y auditoria de creacion/actualizacion; el
  bootstrap demo anual crea parametria demo controlada, no oficial, antes de
  generar artefactos anuales locales.
- La API/snapshot/admin de SII exponen `AnnualTaxSourceBundle` con refs y
  payloads redactados; el admin no busca referencias crudas potencialmente
  sensibles.
- La API/snapshot/admin de SII exponen `MonthlyTaxFact` con `source_ref`,
  `responsible_ref` y `resumen_hecho` redactados; el admin es solo lectura para
  evitar ediciones manuales de hechos derivados.
- La API/snapshot/admin de SII exponen `AnnualTaxTrialBalance` y
  `AnnualTaxTrialBalanceLine` con refs, warnings y payloads redactados; el
  admin es solo lectura para preservar que el balance anual proviene de
  `BalanceComprobacion` y fuentes revisadas, no de edicion manual opaca.
- La API/snapshot/admin de SII exponen `AnnualTaxWorkbook` y
  `AnnualTaxWorkbookLine` con refs, `warning_review_ref`, warnings y payloads
  redactados; el admin es solo lectura para preservar que RLI/CPT provienen del
  normalizador anual y no de edicion manual opaca.
- La API/snapshot/admin de SII exponen `AnnualEnterpriseRegisterSet` y
  `AnnualEnterpriseRegisterMovement` con refs, `warning_review_ref`, warnings y
  payloads redactados; el admin es solo lectura para preservar que
  RAI/SAC/retiros/dividendos provienen del motor anual y no de edicion manual
  opaca.
- La API/snapshot/admin de SII exponen `AnnualRealEstateSection` y
  `AnnualRealEstateItem` con refs, warnings y payloads redactados; el snapshot
  redacta rol/direccion de propiedad y el admin es solo lectura para preservar
  que bienes raices/arriendos provienen del normalizador anual y no de edicion
  manual opaca. La seccion expone el id de `official_contribution_source`
  cuando existe, y los items exponen warnings redactados de fuente/valor
  pendiente sin convertirlo en calculo fiscal final.
- La API/snapshot/admin de SII exponen `AnnualTaxDDJJFormLayout` con refs,
  fuentes, warnings y payloads redactados; el admin es solo lectura para
  preservar que los medios/layouts DDJJ provienen de fuentes revisadas y no de
  edicion manual opaca.
- La API/snapshot/admin de SII exponen `AnnualTaxF22ExportLayout` con refs,
  fuentes, warnings y payloads redactados; el admin es solo lectura para
  preservar que el formato/certificacion F22 alimenta un preview local
  revisable y no una presentacion o calculo tributario final.
- La API/snapshot/admin de SII exponen `AnnualTaxArtifactMatrix` y
  `AnnualTaxArtifactMatrixItem` con refs, warnings y payloads redactados; el
  admin es solo lectura para preservar que la matriz DDJJ/F22 proviene del
  motor anual y no de edicion manual opaca.
- `AnnualTaxArtifactMatrixItem.warning_review_ref` registra revision responsable
  no sensible de warnings de matriz DDJJ/F22. Los warnings permanecen en el
  payload y en los hashes; readiness solo deja de bloquearlos cuando el item
  queda `listo_revision`, la referencia existe y dossier/export/checklist se
  regeneran sin abrir formato oficial, presentacion SII ni calculo final.
- `AnnualTaxReviewChecklist` propaga esa misma regla de warnings pendientes para
  RLI/CPT y registros empresariales: una revision responsable no sensible
  completa el item de checklist aunque el warning total siga auditado.
- `mark_annual_tax_generated_warnings_reviewed` registra una revision responsable
  no sensible sobre la cadena generada completa: lineas RLI/CPT, movimientos
  RAI/SAC y matriz DDJJ/F22. Sin `--apply` opera como dry-run; con `--apply`
  recalcula hashes y regenera dossier, export y checklist. Los warnings quedan
  en payload/hash para auditoria y la accion no habilita formato oficial,
  presentacion SII ni calculo tributario final.
- La API/snapshot/admin de SII exponen `AnnualTaxDossier` con source,
  responsable, dossier ref y payload anual redactados; el admin es solo lectura
  para preservar que el dossier proviene del motor anual y no de edicion manual
  opaca.
- La API/snapshot/admin de SII exponen `AnnualTaxExport` con source,
  responsable, export ref y payload anual redactados; el admin es solo lectura
  y no existe endpoint para presentar a SII desde esta capa.
- La API/snapshot/admin de SII exponen `AnnualTaxReviewChecklist` con checklist
  ref, responsable, evidencia y payload anual redactados; el admin es solo
  lectura para preservar que la checklist proviene del motor anual y no de una
  edicion manual opaca.
- `AnnualTaxSourceBundle` acepta como trazabilidad anual completa los 12
  `MonthlyTaxFact` normalizados aun si algunos meses no tienen F29/obligacion
  por no declaracion controlada; no se deben inventar obligaciones para cerrar
  el ano.
- `run_annual_tax_controlled_mirror` prepara la prueba espejo AC2024/AT2025
  desde la DB local controlada: valida 12 hechos mensuales, crea capacidades
  DDJJ/F22 locales, rule set/mappings/layouts, source bundle
  `snapshot_controlado` y artefactos anuales locales sin usar SII real,
  credenciales ni outputs finales como input. Su salida sigue siendo revisable
  y `final_tax_calculation=false`.
- `compare_annual_tax_expected_outputs` compara cobertura y trazabilidad de
  Balance/RLI/CPT/RAI/DDJJ/F22 esperados contra artefactos anuales generados
  por LeaseManager. Con `--source-root`, `extract_expected_output_content_signals`
  agrega identidad de DDJJ aceptadas, F22, Balance y registros tributarios desde
  una fuente externa read-only, y `extract_expected_output_value_signals`
  compara presencia de valores generados en Balance y registros tributarios sin
  guardar texto bruto, tokens numericos crudos ni montos crudos. Ademas
  `extract_expected_output_document_semantic_signals` compara DDJJ aceptadas con
  folio y F22 con folio contra DDJJ/F22 preparados y layouts anuales preparados,
  sin guardar texto bruto ni folios crudos. No escribe DB, no lee SII real y no
  usa esos outputs como insumo de calculo.
- La normalizacion anual AC2024/AT2025 distingue lineas soporte y lineas
  comparables mediante `source_payload.expected_output_artifacts`. RLI/CPT se
  generan desde Libro Inventario y resultado contable, incluyendo mappings sobre
  varios clasificadores DJ1847; RAI/SAC se preparan para revision, pero no se
  fuerzan como igualdad final de valores. La corrida v2 queda con 132 targets
  comparables, 102 presentes y 30 ausentes concentrados en Balance General; no
  hay faltantes no-balancearios, pero Etapa 6 sigue parcial.
- La comparacion v4 AC2024/AT2025 corrige la falsa brecha de Balance General:
  el draft fusiona Libro Inventario con totales anuales de Libro Mayor para
  preservar sumas/saldos por cuenta, y el extractor de valores esperados evita
  fusionar codigo de cuenta, numero de local y columnas monetarias tras
  normalizar texto PDF. Resultado local: 138 targets comparables, 138 presentes
  y 0 ausentes, sin usar outputs finales como input ni guardar montos crudos.
- La comparacion v5 agrega semantica documental DDJJ/F22. Resultado local:
  7/7 documentos DDJJ/F22 comparados, 138/138 valores comparables presentes, 0
  faltantes y sin categorias esperadas sin soporte. Etapa 6 sigue parcial por
  revision de artefactos generados/responsable y gates finales.
- La prueba espejo AC2024/AT2025 con ownership y bienes raices completos queda
  confirmada el 2026-06-17: paquete controlado local con 12 meses, ownership
  validado y 6 bienes raices; writer local con 12 `MonthlyTaxFact`, ownership y
  bienes raices cargados; mirror anual con las 12 DDJJ esperadas, F22, balance,
  RLI/CPT, RAI/SAC/retiros/dividendos, matriz, dossier, export y checklist; y
  `scripts/run-stage6-mirror-proof-gate.ps1 -FailOnIncomplete` termina
  `classification=resuelto_confirmado`, `ready_for_architecture_proof=true` y
  `ready_for_objective_completion=true`. Esto confirma la arquitectura para el
  objetivo espejo de Inmobiliaria Puig AC2024/AT2025, sin abrir SII real ni
  declarar renta final presentada.

```powershell
scripts\run-stage6-readiness-gate.ps1 -PythonExe backend\.venv\Scripts\python.exe
```

## Salida

El dossier y su export local no quedan aprobables si existen meses sin cierre
validado, reglas fiscales sin respaldo, responsable de revision ausente,
warnings pendientes o formato/certificacion SII no evidenciado. La renta anual
final no se declara presentada por el core v1; `SII.PresentacionAnualFinal`
sigue podada salvo reemision formal del set activo.
