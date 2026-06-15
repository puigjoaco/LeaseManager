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
Inventario, RCV, F29, compra/venta y remuneraciones pueden alimentar carga
controlada; Balance General, RLI, CPT, RAI, Capital Propio, Rentas
Empresariales, DDJJ y F22 quedan como salidas esperadas/baseline. LeaseManager
no puede declarar que genero esos artefactos si antes los uso como insumo de
calculo.
`build_annual_tax_controlled_load_plan` traduce ese manifiesto a un plan de
carga contra modelos canonicos de LeaseManager sin escribir DB: cierres,
libros, balance, obligaciones, F29, hechos mensuales y balance tributario
anual. Para Inmobiliaria Puig AC2024/AT2025 el plan confirma que los outputs
esperados no se usan como input, pero `ready_for_db_load=false` hasta tener
parser/carga manual controlada para libros anuales, F29 PDF y remuneraciones,
mas un paquete normalizado de entrada y el comparador de outputs esperados.
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
`audit_annual_tax_controlled_package_readiness` audita el template o paquete
antes de aplicar el writer: confirma 12 meses, refs de control, valores de
libros/balance, estado F29, estado laboral/previsional y ausencia de outputs
finales usados como input. Contra el template real de Inmobiliaria Puig AC2024/
AT2025 confirma que no faltan meses y que existen objetivos de comparacion,
pero mantiene `ready_for_db_writer=false` hasta completar 132 campos
normalizados; febrero y diciembre F29 `no_aplica` no cuentan como faltantes.
`build_annual_tax_controlled_values_draft` completa ese paquete desde fuentes
AC2024 permitidas y read-only: Libro Diario, Libro Mayor, F29 y libros de
remuneraciones. La corrida real de Inmobiliaria Puig rellena 176 campos,
queda `ready_for_db_writer=true` y permite aplicar el writer contra SQLite
local/controlado para materializar 12 cierres mensuales, 12 libros diario/mayor,
12 balances, 10 F29, 10 obligaciones y 12 `MonthlyTaxFact`. Esta carga no usa
outputs finales como input y no declara cierre de renta; deja pendiente la
capa anual, source bundle en DB, DDJJ/F22 generados y comparador.
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
exposicion redactada. Esta capa no declara calculo tributario final; deja
importes, origenes y advertencias listos para revision antes de avanzar a
RAI/SAC/DDJJ/F22.
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
El mismo diagnostico queda disponible en Reporting como
`contabilidad/progreso-empresa/`, para que el avance de una empresa piloto se
consulte con `empresa_id` y `fiscal_year` antes de iniciar afirmaciones de
cierre anual. La vista conserva el boundary: no calcula renta final, no sube
F22/DDJJ, no usa SII real y no reemplaza revision tributaria experta.
El selector `audit_company_accounting_candidates` y la vista Reporting
`contabilidad/candidatos-progreso-empresa/` priorizan empresas y anos con
senales locales de cierre, balances, F29, proceso anual, balance tributario,
RLI/CPT, dossier y export. Sirve para elegir que expediente revisar primero;
no habilita calculo tributario final, upload SII ni presentacion autonoma.
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
  `hash_linea` coherente. Lineas con warnings bloquean readiness hasta revision
  tributaria; no se transforman en cierre automatico.
- `AnnualEnterpriseRegisterSet` preparado requiere proceso anual, bundle y rule
  set coherentes, saldos iniciales/finales trazables, `resumen_registro` y
  `hash_registro` coherentes. Para tratar un proceso anual como trazable deben
  existir registros RAI, SAC, retiros y dividendos.
- `AnnualEnterpriseRegisterMovement` activo requiere origen, monto, signo,
  `formula_ref`, `evidencia_ref`, `source_payload` y `hash_movimiento`
  coherente. Movimientos con warnings bloquean readiness hasta revision
  tributaria; retiros/dividendos pueden conservar movimientos cero trazados a
  participaciones activas mientras no existan eventos propios.
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
  workbooks, sin lineas activas, con warnings, invalidos o con resumen RLI/CPT
  desalineado.
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
  `AnnualTaxWorkbookLine` con refs, warnings y payloads redactados; el admin es
  solo lectura para preservar que RLI/CPT provienen del normalizador anual y no
  de edicion manual opaca.
- La API/snapshot/admin de SII exponen `AnnualEnterpriseRegisterSet` y
  `AnnualEnterpriseRegisterMovement` con refs, warnings y payloads redactados;
  el admin es solo lectura para preservar que RAI/SAC/retiros/dividendos
  provienen del motor anual y no de edicion manual opaca.
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

```powershell
scripts\run-stage6-readiness-gate.ps1 -PythonExe backend\.venv\Scripts\python.exe
```

## Salida

El dossier y su export local no quedan aprobables si existen meses sin cierre
validado, reglas fiscales sin respaldo, responsable de revision ausente,
warnings pendientes o formato/certificacion SII no evidenciado. La renta anual
final no se declara presentada por el core v1; `SII.PresentacionAnualFinal`
sigue podada salvo reemision formal del set activo.
