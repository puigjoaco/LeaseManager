# Matriz de trazabilidad - mayo 2026

Esta matriz conecta producto, fuentes, implementacion, etapa, estado, gate y
proxima accion. Debe actualizarse cuando un frente avance.

La matriz es un mapa de estado, no el cursor operativo. El frente activo y la
decision de que paquete continuar en una reanudacion quedan en
`docs/product/EXECUTION_CURSOR_MAYO_2026.md`.

Nota 2026-06-13: PRD/Arquitectura/Etapas 4, 5, 6 y 7 fijan el boundary
contable-tributario asistido. LeaseManager v1 mecaniza datos, reglas,
evidencia, asientos, paquetes mensuales y dossiers F29/DDJJ/F22 revisables; no
decide ni presenta renta/tributacion final de forma autonoma. La aprobacion o
presentacion externa exige gate aplicable, responsable trazado y validacion
experta/oficial cuando corresponda.

Nota 2026-06-16: El progreso contable/renta por empresa queda con boundary
explicito en API, Reporting y backoffice. `audit_company_accounting_progress`
y `contabilidad/progreso-empresa/` exponen `review_boundary` con
`autonomous_accounting=false`, `final_tax_calculation=false`,
`sii_submission=false` y revision responsable/experta requerida. El selector
`audit_company_accounting_candidates` y
`contabilidad/candidatos-progreso-empresa/` exponen `selection_boundary`: solo
ordenan empresas/anos con senales locales, sin fuentes externas ni apertura de
gates. `ready_for_company_accounting_review` significa paquete local preparado
para revision responsable, no cierre contable, calculo de renta final ni
presentacion SII.

Nota 2026-06-16: DJ1887/remuneraciones queda como boundary de fuente
laboral-previsional para Etapa 6. Si el manifiesto AC/AT detecta DJ1887
aceptada, `labor_previsional_source` pasa a requerido: falta de
`payroll_support` bloquea `ready_for_mirror_source_bundle`, el plan reporta
`labor_previsional_source_missing`, el template arrastra
`labor_previsional.required=true` y readiness/writer rechazan paquetes sin
`labor_previsional.source_ref` no sensible. No se implementa payroll completo,
no se usa EDIG/SII real y no se convierte DJ1887 final en input de calculo.
El draft controlado de valores consolida `labor_previsional.source_ref` solo
cuando los `payroll_support` esperados fueron revisados exitosamente, dejando
`final_tax_calculation=false` y sin abrir presentacion SII.

Nota 2026-06-16: RLI/CPT distingue warnings totales de warnings pendientes de
revision. `AnnualTaxWorkbookLine.warning_review_ref` conserva una revision
responsable no sensible para lineas con warnings, recalcula hash de linea y
workbook y permite que readiness deje de bloquear solo cuando el warning tiene
revision trazada. Los warnings permanecen en payload/hash y siguen fluyendo a
matriz/artefactos como preparacion revisable; esto no habilita calculo
tributario final, formato oficial ni presentacion SII.

Nota 2026-06-15: La iteracion posterior al mapeo completo EDIG se contrasta
con SII. F22 AT2026 opera por certificacion de software que genera archivos y
SII acredita recepcion, no contenido ni consistencia tributaria. DDJJ Renta
2026 conserva medios oficiales por formulario y SII lista a EDIG como casa
software DDJJ para formularios relevantes del inventario local. F29 mantiene el
patron de upload/certificacion. La decision tecnica queda cerrada: no hace
falta ejecutar binarios EDIG para avanzar LeaseManager; cualquier ejecucion
futura solo puede ser sandbox observacional con datos ficticios y brecha
concreta de UI/export. El camino sigue siendo capa anual revisable,
responsable y gate SII, no API REST asumida ni presentacion autonoma.

Nota 2026-06-15: La prueba espejo Inmobiliaria Puig AC2024/AT2025 agrega
extractor de identidad para outputs esperados externos read-only. El
comparador anual ya no se queda solo en cobertura: con `--source-root` reconoce
senales de DDJJ aceptadas 1835/1837/1847/1887/1926/1948, F22, Balance y
registros tributarios esperados, sin guardar texto bruto ni usar esas salidas
como input de calculo. La conclusion espejo sigue pendiente de extractores de
igualdad de valores, revision responsable de artefactos generados y gates de
Etapa 6.

Nota 2026-06-15: La prueba espejo agrega un primer extractor de valores para
Balance y registros tributarios esperados. El comparador no guarda montos
crudos ni tokens numericos crudos; solo registra refs hash y conteos. Contra la
SQLite local AC2024/AT2025, cobertura e identidad estan listas. Tras cargar
Libro Inventario como input anual permitido, el mirror genera 45 lineas de
balance anual y el comparador pasa a 139 targets comparables: 100 presentes en
outputs esperados y 39 ausentes. Los ausentes se concentran en parte del Balance
y en registros tributarios RLI/CPT/RAI/SAC; DDJJ/F22 siguen fuera del extractor
de valores. El siguiente avance debe reconciliar calculos/semantica de valores,
no declarar cierre.

Nota 2026-06-15: La normalizacion anual posterior separa lineas comparables de
lineas soporte. RLI/CPT se alimentan desde Libro Inventario y resultado contable
con mappings sobre varios clasificadores DJ1847, y `source_payload` declara que
artefactos finales puede comparar cada linea. RAI/SAC quedan preparados como
registros revisables, no como igualdad final automatica. En la SQLite v2
controlada se generan 44 lineas de balance anual, 7 lineas workbook y 9
movimientos; el comparador pasa a 132 targets comparables, 102 presentes y 30
ausentes, todos concentrados en `balance_general`. Esto elimina falsos
faltantes no-balancearios sin cerrar Etapa 6: siguen pendientes Balance faltante,
DDJJ/F22 semantico, bienes raices, soporte tributario y revision responsable.

Nota 2026-06-15: La prueba espejo AC2024/AT2025 corrige la lectura de valores
del Balance General esperado. El draft anual fusiona Libro Inventario con
totales anuales de Libro Mayor para conservar sumas/saldos por cuenta, y el
extractor de outputs esperados deja de aceptar espacios como separadores de
miles despues de normalizar texto PDF, evitando tokens fusionados con codigos de
cuenta o numeros de local. La comparacion v4 queda con 138 targets comparables,
138 presentes y 0 ausentes, sin usar outputs finales como input ni guardar texto
bruto, tokens crudos o montos. Etapa 6 sigue parcial por revision de artefactos
generados y por falta de extractor semantico DDJJ/F22.

Nota 2026-06-15: La comparacion v5 agrega semantica documental DDJJ/F22. El
extractor acepta DDJJ solo si estan aceptadas y con folio, acepta F22 con folio,
deduplica por formulario, ignora documentos rechazados/anulados o resumenes como
objetivo final, y compara contra DDJJ/F22 preparados y layouts anuales
preparados por LeaseManager. Resultado local AC2024/AT2025: 7/7 documentos
DDJJ/F22 y 138/138 targets de valores comparables presentes, sin categorias
esperadas sin soporte. La prueba espejo sigue parcial por revision de artefactos
generados/responsable y gates finales, no por DDJJ/F22 semantico.

Nota 2026-06-15: El patch posterior a PR #856 corrige la seleccion de libros
anuales cuando el manifiesto contiene varios anos o fuentes pendientes. El draft
AC2024 ahora selecciona insumos compatibles con `commercial_year`, vuelve a 180
campos llenos y 0 errores de extraccion. Con snapshot `ownership` local
controlado desde evidencia societaria revisada, el paquete queda
`ready_for_db_writer=true` y `ready_for_annual_generation=true`; el writer carga
12 meses y el mirror genera ProcesoRentaAnual, DDJJ/F22 preparados, matriz,
dossier, export y checklist con source bundle `snapshot_controlado`. El gate
Etapa 6 queda parcial por solo dos bloqueos concretos: item anual de bienes
raices y respaldo tributario usable. No reabrir ownership, DDJJ/F22 semantico,
Balance ni RLI/CPT/RAI/SAC comparable salvo bug nuevo.

Nota 2026-06-16: El mirror anual controlado ahora emite un
`DocumentoEmitido` de tipo `respaldo_tributario` con plantilla `stage6-v1`
desde el generador PDF canonico de Documentos, con preview auditada, checksum
de contenido y alcance local revisable. La corrida AC2024/AT2025 sobre SQLite
local ignorada confirma 1 respaldo emitido y el gate Etapa 6 queda parcial por
un unico bloqueo: `stage6.real_estate_item_missing`. El respaldo no es formato
oficial SII, no registra presentacion y no constituye calculo tributario final.

Nota 2026-06-16: Se agrega `audit_annual_tax_mirror_proof` como gate unico de
prueba espejo AC2024/AT2025. El gate combina manifiesto/fuente, comparador de
outputs esperados, readiness Etapa 6 y boundary de seguridad; solo puede marcar
`ready_for_objective_completion=true` si la fuente esta documentada, la
arquitectura espejo esta completa, la comparacion esta lista, Etapa 6 esta
lista y no se usaron SII real, credenciales ni outputs finales como input. En
fixture sintetico queda parcial por revision de artefactos, lo que confirma que
no sobredeclara cierre.

Nota 2026-06-16: `scripts/run-stage6-mirror-proof-gate.ps1` queda como wrapper
operativo seguro para `audit_annual_tax_mirror_proof`. Exige refs no sensibles,
rechaza salidas/manifiestos versionables fuera de `local-evidence/`, bloquea
`-RunMigrations` con `real_autorizado`, valida el JSON de salida y queda cubierto
por acceptance con un guard que prueba rechazo de output versionable antes de
leer manifiestos o tocar DB.

Nota 2026-06-15: Se agrega `build_annual_tax_ownership_evidence_chain` como
orquestador reproducible para la brecha patrimonial AC2024. Regenera bajo
`local-evidence/` el manifiesto, la revision de candidatos societarios, el
template ownership y opcionalmente el paquete visual/OCR. No escribe DB, no
copia fuentes, no guarda texto crudo ni RUTs, y no genera nombres de socios ni
porcentajes; su objetivo es que una reanudacion desde `main` no dependa de
artefactos perdidos al eliminar worktrees y mantenga la siguiente accion en
revision/OCR y carga controlada, no en prompts ni metatareas.

Nota 2026-06-13: La investigacion local de EDIG AT2026 queda mapeada como
referencia funcional no normativa en
`docs/product/RENTA_ANUAL_EDIG_AT2026_MAPPING.md`, con runbook de sandbox en
`docs/operations/EDIG_AT2026_SANDBOX_RUNBOOK.md` y script read-only
`scripts/analyze-edig-at2026.ps1`. La decision tecnica para Etapa 6 es unir
contabilidad y renta mediante una capa intermedia anual RLI/CPT/RAI/SAC/DDJJ,
no por traspaso directo de asientos a F22 ni por IA autonoma. EDIG queda
ignorado por Git y no abre gate SII.

Nota 2026-06-13: El inventario EDIG AT2026 agrega matriz de senales
funcionales sin versionar evidencia bruta: administracion, F22, F29/PPM,
regimenes 14A/14D3/14D8/14G, RLI, CPT, RAI, SAC, DDJJ,
balance/contabilidad, bienes raices/arriendos, reportes/respaldo,
upload/export y conectividad auxiliar. `CONTRIB/`, `LICENCIAS/`, `RESPUESTA/`
y `UPLOAD/` se excluyen o redactan para evitar datos de usuario, licencia o
salidas de presentacion.

Nota 2026-06-13: El mapeo EDIG AT2026 profundiza a esquema MDB nucleo mediante
`scripts/extract-edig-mdb-schema.ps1`: copia temporalmente solo
`CENTRAL/comun.MDB`, `CENTRAL/prtRegAT21.MDB`, `CENTRAL/R14PARA26.MDB`,
`DATOS/CANova.mdb`, `DATOS/F29LGH.MDB`, `DATOS/PRO26.MDB` y
`DATOS/Reg14.MDB`, extrae metadata de tablas/columnas con Jet 4.0/PowerShell
32-bit y borra las copias. La corrida local obtuvo 205 tablas y 5.494 columnas
sin leer filas, reforzando la separacion entre maestros, F29/PPM, parametria
por regimen, PRO/F22 y registros RLI/CPT/RAI/SAC. Sigue siendo referencia
funcional no normativa.

Nota 2026-06-13: `docs/product/RENTA_ANUAL_AT2026_ENGINE_BLUEPRINT.md`
convierte la evidencia EDIG AT2026 en arquitectura propia implementable para
Etapa 6: `AnnualTaxSourceBundle`, `TaxYearRuleSet`, `AnnualTaxProfile`,
`MonthlyTaxFact`, `AnnualTaxNormalizer`, RLI/CPT workbooks,
`EnterpriseRegisterSet`, seccion bienes raices, DDJJ, F22, dossier y export
gate. El orden recomendado empieza por reglas AT/source bundle y termina en
preview/export controlado, sin presentacion SII autonoma. El blueprint tambien
fija una matriz para decidir integracion SII: DTE puede avanzar por gate tecnico
si existe certificacion/formato/web service vigente; F29/DDJJ/F22 quedan como
preparacion, preview, dossier o export supervisado hasta evidencia oficial,
responsable y autorizacion.

Nota 2026-06-14: Etapa 6 materializa `MonthlyTaxFact` como puente mensual
contabilidad -> renta. `generate_annual_preparation()` sincroniza una fila
normalizada por empresa/ano/mes desde cierre aprobado, obligaciones F29/PPM,
F29 si existe, distribuciones de arriendo y liquidacion de empresa, con hash
del resumen mensual y refs no sensibles. La readiness bloquea procesos anuales
trazables sin doce hechos mensuales normalizados o con resumen mensual
desalineado, manteniendo el camino anual en capas antes de RLI/CPT/F22.

Nota 2026-06-14: Etapas 5/6 agregan `audit_company_accounting_progress` como
auditor operativo por empresa y ano comercial. Consolida configuracion fiscal,
doce cierres, balances mensuales aprobados/cuadrados, F29, proceso anual,
balance tributario, workbooks RLI/CPT, dossier y export local en un JSON con
porcentaje, siguiente fase bloqueante y `ready_for_company_accounting_review`.
La senal es lista para revision responsable, no cierre contable/tributario
legal, y no lee `.env`, fuentes externas, SII, EDIG ni datos reales por
defecto.

Nota 2026-06-14: Reporting expone el auditor de progreso contable/renta por
empresa en `contabilidad/progreso-empresa/` y backoffice. El reporte respeta
scope por empresa, no incluye RUT, agrega trazabilidad de fuentes y muestra
porcentaje, fases, faltantes y bloqueos para que la primera empresa piloto se
mida con `empresa_id` y `fiscal_year` antes de declarar avance real.

Nota 2026-06-14: Reporting y CLI agregan selector de candidatos de progreso
contable/renta en `contabilidad/candidatos-progreso-empresa/` y
`audit_company_accounting_candidates`. Priorizan empresas y anos comerciales
con senales internas de cierres, balances, F29, proceso anual, balance
tributario, RLI/CPT, dossier y export local; no exponen RUT, no leen `.env`,
no usan fuentes externas y no reemplazan el gate de cierre.

Nota 2026-06-14: Progreso contable/renta y readiness Etapa 6 explicitan el
boundary de regimen soportado. Una `ConfiguracionFiscalEmpresa` activa fuera de
`EmpresaContabilidadCompletaV1` puede aparecer como dato operativo y conservar
senales locales, pero bloquea `ready_for_company_accounting_review` y
`ready_for_stage6_renta_anual` con issues especificos hasta que exista gate,
ADR y validacion oficial/experta para ampliar el regimen automatizable.

Nota 2026-06-15: Para Inmobiliaria Puig AC2024/AT2025 se agrega
`build_annual_tax_source_manifest` como paso previo a la prueba espejo. El
comando inventaria una carpeta externa en modo read-only, clasifica archivos
como entradas, soportes o salidas esperadas, calcula hashes y produce un
borrador no sensible de `AnnualTaxSourceBundle`. La corrida local contra
`Ano_2024` confirma entrada minima para espejo desde libros cerrados: RCV 12/12,
F29 12/12 controlado considerando meses sin declaracion, libros
Diario/Mayor/Inventario como inputs, compra/venta 12/12, Balance General y
registros RLI/CPT/RAI/Capital Propio/Rentas Empresariales como objetivos de
comparacion, DDJJ 1835/1837/1847/1887/1926/1948 aceptadas y F22 presente. No
carga DB, no copia documentos y no cierra renta: el siguiente paso es
transformar ese manifiesto en carga controlada de cierres/hechos mensuales y
generar artefactos LeaseManager para compararlos contra esos outputs esperados,
sin usarlos como input de calculo.

Nota 2026-06-15: Se agrega `build_annual_tax_controlled_load_plan` como plan
ejecutable previo al loader DB. El plan mapea el manifiesto AC2024/AT2025 hacia
modelos canonicos (`CierreMensualContable`, `LibroDiario`, `LibroMayor`,
`BalanceComprobacion`, `ObligacionTributariaMensual`, `F29PreparacionMensual`,
`MonthlyTaxFact`, `AnnualTaxTrialBalanceLine`) y confirma que Balance/RLI/CPT/
RAI/DDJJ/F22 son comparacion, no insumo. La corrida real queda en
`ready_for_db_load=false` porque faltan parser/carga manual controlada para
libros anuales, F29 PDF y remuneraciones; pasos posteriores ya quedan
trazados por writer DB local, run anual controlado y comparador de cobertura.

Nota 2026-06-14: Etapa 6 agrega `AnnualTaxTrialBalance` como capa anual de
balance de ocho columnas entre `BalanceComprobacion` y RLI/CPT/DJ1847.
`generate_annual_preparation()` lo sincroniza desde el balance aprobado de
diciembre, fuente oficial/experta revisada y rule set anual; workbooks RLI/CPT
pueden tomar metricas de esas lineas mediante `TaxCodeMapping.metadata`. API,
snapshot y admin redactan refs/payloads, y readiness bloquea procesos sin
balance preparado, resumen alineado, lineas activas o revision de warnings. No
declara calculo tributario final ni presentacion SII.

Nota 2026-06-14: Etapa 6 agrega `AnnualTaxDDJJFormLayout` como capa anual de
medios/layouts DDJJ por formulario. `generate_annual_preparation()` resume los
layouts preparados antes de la matriz DDJJ/F22, y la matriz usa
`source_kind=ddjj_layout` cuando existe layout trazable. API, snapshot y admin
redactan refs/payloads; readiness bloquea formularios habilitados sin layout
preparado, layouts invalidos, warnings pendientes o resumen anual desalineado.
No declara formato oficial, upload SII ni calculo tributario final.

Nota 2026-06-14: Etapa 6 agrega `AnnualTaxF22ExportLayout` como capa anual de
formato/certificacion F22 previa al export local. El layout conserva fuente
oficial/experta, refs no sensibles, medio preferente, hash y boundary explicito
con `official_format=false`, `sii_submission=false` y
`final_tax_calculation=false`. La matriz DDJJ/F22 puede referenciarlo con
`source_kind=f22_export_layout`; dossier, export y checklist lo resumen sin
habilitar presentacion SII ni decision tributaria autonoma. `AnnualTaxExport`
enlaza ademas una `official_format_source` y conserva id/hash/medio del layout
F22 en su payload/resumen. Readiness bloquea procesos trazables sin layout F22
preparado, con warnings, invalidos, resumen desalineado o export sin fuente de
formato/certificacion F22.

Nota 2026-06-14: Etapa 6 endurece la union contabilidad -> renta en
DJ1847/RLI/CPT. `TaxCodeMapping` activo bajo `TaxYearRuleSet` aprobado que
declara `source_metric=annual_trial_balance.*` solo puede alimentar RLI/CPT y
debe conservar `trial_balance_classifier` DJ1847. Readiness clasifica snapshots
heredados con mappings sin clasificador o apuntando directo a destinos
posteriores, evitando saltos desde balance anual hacia F22/DDJJ sin la capa
RLI/CPT trazable.

Nota 2026-06-14: Etapa 6 agrega `AnnualTaxReviewChecklist` como frontera
auditable entre preparacion mecanica y decision tributaria supervisada. El
checklist resume dossier, export local, fuentes, reglas, matriz DDJJ/F22 e
items de control con hash, responsable y evidencia no sensible. No declara
formato oficial, presentacion SII ni calculo fiscal final; readiness bloquea
procesos trazables sin checklist, con resumen desalineado, items incompletos,
warnings/bloqueos o payloads que crucen esa frontera.

Nota 2026-06-14: `RENTA_ANUAL_OFFICIAL_SOURCE_GAPS_AT2026.md` consolida las
fuentes oficiales y brechas externas de Etapa 6. DTE queda como integracion
tecnica posible bajo gate propio; F29, DDJJ, DJ1847/RLI/CPT, F22, bienes
raices/contribuciones y automatizacion por navegador quedan como preparacion
local revisable hasta contar con fuente SII/experta, certificacion/formato,
responsable y autorizacion explicita. `build-stage6-official-source-gap-matrix.ps1`
genera una salida local ignorada para no volver a debatir ese boundary.

Nota 2026-06-14: Etapa 6 materializa `AnnualTaxOfficialSource` como registro
operacional de fuentes SII/experta por ano tributario. Las fuentes revisadas o
aprobadas requieren URL publica SII segura cuando aplica, referencia no
sensible, hash SHA-256, fecha de recuperacion y responsable; API/snapshot/admin
redactan refs, notas y metadata heredadas, y readiness reporta
`stage6.official_source_invalid` si una fuente registrada no pasa dominio.

Nota 2026-06-14: Etapa 6 enlaza reglas y mappings anuales con
`AnnualTaxOfficialSource`. `TaxYearRuleSet` aprobado y `TaxCodeMapping` activo
bajo regla aprobada requieren fuente revisada/aprobada del mismo ano tributario
y compatible con regimen/destino cuando la fuente declare esos alcances. La
readiness reporta faltas o incompatibilidades con codigos especificos, cerrando
la brecha entre matriz oficial AT2026 y reglas locales sin automatizar
presentacion SII ni criterio tributario final.

Nota 2026-06-14: `bootstrap_demo_tax_annual_flow` queda alineado con ese gate:
el baseline anual demo crea/repara `AnnualTaxOfficialSource` experta aprobada
para el rule set y para cada mapping RLI/CPT/RAI/SAC/DDJJ/F22. Esto conserva
el showcase local como preparacion controlada e idempotente, sin presentar SII,
sin usar fuentes reales y sin dejar parametria demo que la readiness de Etapa 6
clasifique como huerfana de fuente.

Nota 2026-06-14: `AnnualTaxOfficialSource.retrieved_on` queda acotado al
pasado o presente para fuentes revisadas/aprobadas. El bootstrap demo anual usa
la fecha local de corrida como recuperacion controlada en vez de derivarla del
ano tributario, evitando evidencia AT futura en escenarios demo.

Nota 2026-06-14: `AnnualTaxDossier.resumen_dossier` queda bajo el mismo
boundary no autonomo que el export local: no puede declarar formato oficial
SII, presentacion SII, intento de presentacion ni calculo fiscal final. La
readiness Etapa 6 clasifica snapshots heredados con flags de cierre como
brecha bloqueante especifica, aunque el hash del dossier este recalculado.

Nota 2026-06-14: Etapa 6 materializa el skeleton RLI/CPT mediante
`AnnualTaxWorkbook` y `AnnualTaxWorkbookLine`. La preparacion anual genera
workbooks RLI y CPT desde `TaxCodeMapping` + `MonthlyTaxFact`, con hashes por
workbook/linea, refs no sensibles, API/snapshot/admin redactados y readiness
bloqueante si falta RLI/CPT, si no hay lineas activas, si el resumen queda
desalineado o si existen warnings pendientes. El resumen conserva
`final_tax_calculation=false`: LeaseManager prepara dossier revisable, no
decide ni presenta renta final de forma autonoma.

Nota 2026-06-14: Etapa 6 agrega registros empresariales trazables mediante
`AnnualEnterpriseRegisterSet` y `AnnualEnterpriseRegisterMovement`. La
preparacion anual deriva RAI desde RLI, SAC desde CPT y retiros/dividendos desde
participaciones activas con movimientos cero trazados cuando no hay eventos
propios; cada registro conserva saldos, movimientos, hashes y resumen anual
alineado. API/snapshot/admin redactan refs/payloads y readiness bloquea
procesos sin RAI/SAC/retiros/dividendos, sin movimientos activos, con warnings
o con resumen empresarial desalineado.

Nota 2026-06-14: Etapa 6 materializa la seccion anual de bienes
raices/arriendos mediante `AnnualRealEstateSection` y `AnnualRealEstateItem`.
`generate_annual_preparation()` prepara items por propiedad desde `Propiedad`,
`DistribucionCobroMensual` y `ContratoPropiedad`, conserva snapshots anuales
con hash, distribuye arriendos por porcentaje interno, deja contribuciones como
`not_loaded_v1`, expone API/snapshot/admin redactados y bloquea readiness si
falta seccion, item activo, resumen alineado o revision de warnings. Sigue sin
calculo fiscal final ni presentacion SII autonoma.

Nota 2026-06-14: Etapa 6 materializa la matriz anual DDJJ/F22 mediante
`AnnualTaxArtifactMatrix` y `AnnualTaxArtifactMatrixItem`. La preparacion anual
genera items desde configuracion fiscal, `TaxCodeMapping`, source bundle,
resumen anual, RLI/CPT, registros empresariales y bienes raices, con destino,
medio SII, fuente, responsable, hash y payload no sensible. API/snapshot/admin
redactan refs/payloads y readiness bloquea procesos sin matriz preparada, sin
items DDJJ/F22, con resumen desalineado, items invalidos, warnings pendientes o
estado bloqueado. Mantiene `final_tax_calculation=false` y no habilita
presentacion SII autonoma.

Nota 2026-06-16: Etapa 6 permite cerrar la revision responsable de warnings de
`AnnualTaxArtifactMatrixItem` con `warning_review_ref` no sensible. Los warnings
permanecen en payload/hash y solo dejan de bloquear dossier/export/checklist si
el item queda `listo_revision`, la referencia existe y los artefactos derivados
se regeneran. Esto no habilita formato oficial, presentacion SII ni calculo
tributario final.

Nota 2026-06-14: Etapa 6 materializa el dossier anual revisable mediante
`AnnualTaxDossier`. `generate_annual_preparation()` lo sincroniza despues de
la matriz DDJJ/F22 y antes de DDJJ/F22 locales, consolidando source bundle,
hechos mensuales, RLI/CPT, registros empresariales, bienes raices y matriz
DDJJ/F22 en un resumen hasheado con responsable, `dossier_ref`, conteos y
estado de revision. API/snapshot/admin redactan refs/payloads y readiness
bloquea procesos trazables sin dossier, con resumen desalineado, invalidos, sin
refs responsables o con revision pendiente. Mantiene
`final_tax_calculation=false` y `sii_submission=false`: LeaseManager prepara
evidencia para revision, no decide ni presenta renta final de forma autonoma.

Nota 2026-06-14: Etapa 6 materializa el export/preview local controlado
mediante `AnnualTaxExport`. `generate_annual_preparation()` lo sincroniza
despues de crear DDJJ/F22 locales, conectado a `AnnualTaxDossier`, source
bundle, rule set y matriz DDJJ/F22. El payload conserva hash, conteos DDJJ/F22,
refs no sensibles, responsable y flags `official_format=false`,
`sii_submission=false` y `final_tax_calculation=false`. API/snapshot/admin
redactan refs/payloads y readiness bloquea procesos trazables sin export, con
resumen desalineado, invalidos, refs faltantes, revision pendiente o cualquier
intento de presentacion/formato oficial/calculo final autonomo.

Nota 2026-06-13: Etapa 6/7 convierten el boundary asistido en enforcement
local para artefactos anuales. `ProcesoRentaAnual`, DDJJ y F22 en estados
aprobados, observados, rectificados o presentados requieren
`responsable_revision_ref` no sensible; dominio/API/readiness/reporting bloquean
refs faltantes o sensibles sin exponer secretos.

Nota 2026-06-13: Etapa 6/7 tambien exigen que la auditoria anual
`sii.ddjj_preparacion.status_updated` y `sii.f22_preparacion.status_updated`
conserve `responsable_revision_ref` no sensible cuando DDJJ/F22 avanzan a
estados de revision final. Readiness y Reporting bloquean eventos heredados sin
responsable auditado o con referencia sensible, sin devolver metadata cruda.

Nota 2026-06-13: Backoffice SII y Reporting reflejan el boundary asistido de
renta anual. SII permite cargar una revision DDJJ/F22 con estado, ref,
`responsable_revision_ref` y observacion no sensible; ya no ofrece un atajo de
estado anual sin responsable. Reporting anual expone responsables redactados
para ProcesoRentaAnual, DDJJ y F22, sin habilitar presentacion final.

Nota 2026-06-13: Backoffice Contabilidad refleja el boundary de pre-cierre
supervisado. El snapshot de control ahora alimenta liquidaciones mensuales y
lineas de liquidacion en la UI; el operador puede registrar una liquidacion de
empresa con evidencia/responsable no sensible, ver la liquidacion que soporta
cada cierre y cargar reaperturas mediante formulario de motivo, efecto, monto
y evidencia. La aprobacion queda deshabilitada en UI si el cierre no tiene
liquidacion responsable visible, manteniendo el bloqueo backend como fuente de
verdad.

Nota 2026-06-13: Etapa 4 aplica el mismo boundary asistido a F29 mensual. F29
en estados aprobados, observados o rectificados requiere
`responsable_revision_ref` no sensible junto a `borrador_ref`; dominio/API,
snapshot, admin, backoffice y readiness bloquean responsables faltantes o
sensibles. La UI reemplaza la accion ciega de estado F29 por un formulario de
revision con responsable, reforzando que LeaseManager prepara formularios
revisables y no presenta ni aprueba tributacion mensual de forma autonoma.

Nota 2026-06-13: Etapa 5 conserva contexto de aprobacion responsable en cierres
mensuales. `approve_monthly_close()` ya no deja el cierre con solo id/estado de
liquidacion: el resumen y los eventos `approved`/`state_changed` conservan
responsable y evidencia base no sensibles de la `LiquidacionMensual` que
soporta la aprobacion. `audit_stage5_contabilidad_readiness` bloquea snapshots
heredados donde el cierre aprobado perdio ese contexto, manteniendo el paquete
mensual apto para revision humana o IA supervisada.

Nota 2026-06-13: Etapa 5 traza reaperturas excepcionales como cambio de estado.
`CierreMensualReopenView` registra `reopened` y
`contabilidad.cierre_mensual.state_changed` en la misma transaccion con
metadata `aprobado` -> `reabierto` y contexto redactable del efecto contable;
si falla la auditoria, se revierte la reapertura, snapshots y evento de efecto.
`audit_stage5_contabilidad_readiness` bloquea cierres reabiertos heredados sin
ese `state_changed`, evitando paquetes mensuales reabiertos sin trazabilidad.

Nota 2026-06-13: Etapa 5 traza la contabilizacion de eventos como cambio de
estado. La creacion y el reintento de `EventoContable` registran
`contabilidad.evento_contable.state_changed` cuando `post_accounting_event()`
cambia `estado_contable`, con `campo_estado`, `estado_anterior`,
`estado_nuevo` y `asiento_id` cuando existe asiento; si falla la auditoria, se
revierte evento/asiento/estado y auditoria previa. Esto mantiene el ledger como
paquete revisable, no como decision contable opaca.

Nota 2026-06-13: Reporting/Etapa 7 cubre en API los bloqueos de
`ProcesoRentaAnual.borrador_f22_ref` faltante o sensible para procesos anuales
finales. `_assert_annual_tax_traceability()` devuelve
`reporting.annual_process_f22_ref_missing` o
`reporting.annual_process_f22_ref_sensitive` sin exponer URLs ni tokens,
cerrando la paridad focal con `paquete_ddjj_ref`.

Nota 2026-06-13: Reporting/Etapa 7 cubre en API la desalineacion de ano
comercial en DDJJ y F22. `_assert_annual_tax_traceability()` devuelve
`reporting.annual_ddjj_fiscal_year_mismatch` o
`reporting.annual_f22_fiscal_year_mismatch` con el documento afectado, ano
observado y ano esperado, alineado con los codigos
`stage7.reporting.annual_ddjj_fiscal_year_mismatch` y
`stage7.reporting.annual_f22_fiscal_year_mismatch` de readiness.

Nota 2026-06-13: Reporting/Etapa 7 cubre en API el bloqueo de procesos de
renta anual sin estado trazable. `_assert_annual_tax_traceability()` devuelve
`reporting.annual_process_not_traceable`, alineado con el codigo
`stage7.reporting.annual_process_not_traceable` de readiness.

Nota 2026-06-13: Reporting/Etapa 7 cubre en API el bloqueo de eventos
contables sin origen trazable antes de entregar el resumen financiero mensual.
`_assert_financial_monthly_traceability()` devuelve
`reporting.event_origin_missing`, alineado con el codigo
`stage7.reporting.event_origin_missing` de `audit_stage7_reporting_readiness`.

Nota 2026-06-13: Reporting/Etapa 7 alinea la API tributaria anual con
readiness para documentos anuales asociados a proceso/empresa/ano tributario
incorrecto. El endpoint anual ahora separa
`reporting.annual_ddjj_process_mismatch` y
`reporting.annual_f22_process_mismatch`, en correspondencia con
`stage7.reporting.annual_ddjj_process_mismatch` y
`stage7.reporting.annual_f22_process_mismatch`.

Nota 2026-06-13: Reporting/Etapa 7 alinea la API tributaria anual con
readiness para configuracion fiscal activa. El endpoint anual ahora separa
`reporting.annual_process_fiscal_config_missing`,
`reporting.annual_ddjj_fiscal_config_missing` y
`reporting.annual_f22_fiscal_config_missing`, en correspondencia con los
codigos `stage7.reporting.annual_*_fiscal_config_missing` del auditor.

Nota 2026-06-13: Reporting/Etapa 7 alinea la API tributaria anual con
readiness para documentos DDJJ/F22 faltantes o sin resumen. El endpoint anual
ahora separa `reporting.annual_ddjj_missing_for_process`,
`reporting.annual_f22_missing_for_process`,
`reporting.annual_ddjj_summary_missing` y
`reporting.annual_f22_summary_missing`, en correspondencia con los codigos
`stage7.reporting.annual_*` equivalentes del auditor de readiness.

Nota 2026-06-13: Reporting/Etapa 7 alinea la API de libros por periodo con
readiness. `_assert_period_books_traceability()` ahora usa
`reporting.books_snapshot_missing_for_close`,
`reporting.books_snapshot_summary_missing` y `reporting.books_balance_not_square`
para los mismos casos que `audit_stage7_reporting_readiness` clasifica como
`stage7.reporting.books_snapshot_missing_for_close`,
`stage7.reporting.books_snapshot_summary_missing` y
`stage7.reporting.books_balance_not_square`.

Nota 2026-06-13: Reporting/Etapa 7 alinea la API financiera mensual con
readiness para asientos contables incluidos en reportes. La API ahora separa
`reporting.accounting_entry_not_posted` y
`reporting.accounting_entry_unbalanced` en vez de agrupar ambos casos como
invalidos genericos, manteniendo correspondencia con
`stage7.reporting.accounting_entry_not_posted` y
`stage7.reporting.accounting_entry_unbalanced`.

Nota 2026-06-13: Reporting/Etapa 7 alinea la API tributaria anual con
readiness para `ProcesoRentaAnual.resumen_anual`: `obligaciones` debe ser una
lista no vacia. `_assert_annual_tax_traceability()` bloquea respuestas
verificadas con `reporting.annual_summary_incomplete` cuando el resumen anual
no conserva obligaciones mensuales trazables, igual que
`audit_stage7_reporting_readiness`.

Nota 2026-06-13: Contabilidad/Etapa 5 bloquea reglas contables activas con
vigencias solapadas para la misma empresa, tipo de evento y version de plan.
`ReglaContable.full_clean()` y la API rechazan nuevas ambiguedades, y
`audit_stage5_contabilidad_readiness` clasifica snapshots heredados con
`stage5.rules_overlapping_vigencia` y
`sections.rules.overlapping_active_rule_windows`.

Nota 2026-06-12: Conciliacion/Etapa 3 normaliza metadata visible de ingresos
desconocidos antes de validar y persistir. `IngresoDesconocido` recorta
`descripcion_origen` y `estado` antes de `full_clean()` y `save()`, evitando
rechazos de choices/equivalencia por espacios crudos en rutas internas.
`audit_stage3_conciliacion_readiness` bloquea snapshots heredados con esa
metadata no canonica mediante `stage3.unknown_income.visible_metadata_no_canonica`
y `sections.unknown_income.visible_metadata_noncanonical`.

Nota 2026-06-12: CobranzaActiva/Etapa 2 normaliza metadata visible antes de
validar y persistir. `ValorUFDiario`, `AjusteContrato`, `PagoMensual`,
`GateCobroExterno`, `IntentoPagoWebPay`, `DistribucionCobroMensual`,
`GarantiaContractual`, `HistorialGarantia`, `RepactacionDeuda`,
`CodigoCobroResidual` y `EstadoCuentaArrendatario` recortan refs, motivos,
estados, fuentes, codigos y observaciones operativas antes de `full_clean()` y
`save()`. `audit_stage2_cobranza_readiness` bloquea snapshots heredados con
metadata no canonica mediante `sections.visible_metadata` y codigos
`stage2.visible_metadata.*_no_canonica`.

Nota 2026-06-12: Contratos/Etapa 1 normaliza metadata visible antes de
validar y persistir. `Arrendatario` recorta identidad, contacto, perfil y
refs/motivos WhatsApp, y normaliza RUT; `ContactoPagoArrendatario` recorta
nombre, rol, medios y evidencia; `Contrato` recorta codigo y refs/motivos
contractuales y normaliza snapshot de representante legal; `PeriodoContractual`
recorta tipo, origen y politica de renovacion; `CodeudorSolidario` normaliza
snapshot de identidad; `AvisoTermino` recorta causal y resolucion de
conflicto. `audit_stage1_matrix` bloquea snapshots heredados con esos campos
no canonicos mediante codigos especificos de contratos.

Nota 2026-06-12: Operacion/Etapa 1 normaliza metadata visible antes de
validar y persistir. `CuentaRecaudadora` recorta institucion, numero, tipo,
titular, uso operativo y evidencia, y normaliza RUT; `IdentidadDeEnvio`
recorta remitente, destino y referencia de credencial; `MandatoOperacion`
recorta relacion operativa, autoridad y evidencia, y normaliza RUT.
`audit_stage1_matrix` bloquea snapshots heredados con esos campos no
canonicos mediante codigos especificos de cuenta, identidad y mandato.

Nota 2026-06-12: Patrimonio/Etapa 1 normaliza metadata visible antes de
validar y persistir. `RepresentacionComunidad` recorta `evidencia_ref` y
`observaciones`; `ServicioPropiedad` recorta proveedor, numero de cliente,
administrador y `evidencia_ref`. `audit_stage1_matrix` bloquea snapshots
heredados con esos campos no canonicos mediante codigos especificos de
representacion y servicio.

Nota 2026-06-10: Etapa 3 endurece supersesiones de resoluciones manuales. El
servicio `supersede_manual_resolutions_for_movement()` valida que el motivo sea
auditable y no sensible antes de mutar estado, metadata o auditoria; una
regresion focal confirma que un motivo con URL/token deja la resolucion abierta
y no emite evento de supersesion.

Nota 2026-06-10: Contratos/Etapa 1 exige causal estructurada en avisos de
termino. `AvisoTermino.full_clean()` rechaza causales vacias tras normalizar
espacios, y `audit_stage1_matrix` clasifica como defectuosos los snapshots
heredados con avisos registrados sin causal operativa.

Nota 2026-06-10: Contratos-Cobranza/Etapa 1 exige justificacion operativa en
ajustes contractuales. `AjusteContrato.full_clean()` rechaza justificaciones
vacias tras normalizar espacios, y `audit_stage1_matrix` clasifica como
defectuosos los snapshots heredados con ajustes sin motivo operativo.

Nota 2026-06-10: Los scripts externos de Vercel/Railway quedan en modo
plan por defecto. `connect-frontend-to-backend.ps1` ya no lee `deploy.bat`,
`.env`, rutas legacy ni `Produccion 1.0`, y solo modifica Vercel con `-Apply`
y `AuthorizationRef`; el redeploy requiere `-Redeploy`.
`railway-backend-bootstrap.ps1` usa `backend/railway.env.example`, no ejecuta
Railway CLI sin `-Apply` y `AuthorizationRef`, y redacta valores en comandos
`variable set`. Tambien rechaza `-BackendEnvPath` apuntando a `.env` real antes
de resolver o leer el archivo; solo acepta templates `.env.example` no
sensibles.
El guard `scripts/tests/external-script-policy.test.ps1` queda incorporado al
acceptance local para bloquear regresiones.

Nota 2026-06-10: Los comandos demo restantes sanitizan errores controlados de
entrada. `bootstrap_demo_public_showcase`, `bootstrap_demo_operational_data`,
`bootstrap_demo_control_activity`, `bootstrap_demo_control_baseline`,
`bootstrap_demo_compliance_exports`, `bootstrap_demo_tax_monthly_flow` y
`bootstrap_demo_tax_annual_flow` conservan sus validaciones, pero sus
`CommandError` y stdout no repiten valores UF/mes/monto crudos, listas, IDs,
usernames, referencias de empresa, configuracion fiscal ni IDs de exportacion.

Nota 2026-06-10: Los errores controlados de comandos demo de acceso tambien
quedan redactados. `seed_demo_access` y `bootstrap_demo_showcase_access`
mantienen validaciones de empresa, socio, propiedad, cuenta, usuario, rol y
scope, pero si una referencia explicita no existe ya no repiten IDs,
usernames, codigos de rol ni listas crudas en `CommandError`.

Nota 2026-06-10: El bootstrap operacional demo reduce errores humanos crudos.
`bootstrap_demo_operational_data` mantiene carga UF, generacion de pagos
faltantes y recalculo de estados de cuenta, pero los fallos controlados del
calculo mensual ya no listan id/codigo de contrato, mes operativo ni excepcion
cruda; solo reportan conteo de errores controlados y detalle no impreso.

Nota 2026-06-10: Los comandos demo tributarios y de actividad de control
reducen salida humana. `bootstrap_demo_tax_monthly_flow`,
`bootstrap_demo_tax_annual_flow` y `bootstrap_demo_control_activity` dejan de
imprimir ids de empresa, pago, DTE, F29, cierres, movimientos, proceso anual,
DDJJ/F22, listas DDJJ y warnings F29 crudos; reportan flags, conteos y estados
no sensibles.

Nota 2026-06-10: El seed demo de acceso RBAC reduce su salida humana.
`seed_demo_access` mantiene la creacion reproducible de roles, scopes,
usuarios y asignaciones, pero stdout ya no imprime usernames demo, codigos de
scope, nombres de socio, ids ni referencias operativas crudas; solo reporta
indice demo, rol, tipo de scope, presencia booleana de referencia y password
no impreso.

Nota 2026-06-10: El bootstrap demo de showcase RBAC tambien reduce su stdout.
`bootstrap_demo_showcase_access` conserva la ampliacion de scopes de empresa
para el usuario demo read-only, pero ya no imprime username, rol,
`company_ids`, codigos de scope ni nombres de empresa; solo reporta flags de
usuario/rol validados, conteo de empresas y asignaciones creadas/reutilizadas.

Nota 2026-06-10: El orquestador `bootstrap_demo_public_showcase` deja de
reemitir payload humano crudo de sus subcomandos. El resumen inicial ya no
lista ids de empresa ni meses operativos crudos, cada paso reporta solo nombre
del comando, conteo de lineas capturadas y flag de detalle no impreso, y los
warnings/errores controlados quedan sanitizados.

Nota 2026-06-10: Los comandos demo de Compliance reducen su salida humana.
`bootstrap_demo_compliance_policies` ya no imprime `evento_inicio` crudo y
`bootstrap_demo_compliance_exports` ya no imprime `scope_resumen`; ambos
mantienen validacion/persistencia, pero stdout queda limitado a confirmaciones,
conteos y resumen de cantidad de campos.

Nota 2026-06-10: El control `security.admin_mfa_control` tambien bloquea
descripciones sensibles. `PlatformSetting.clean()` rechaza `description` con
URLs, tokens o credenciales para evitar que una nota visible en Django admin
se convierta en superficie de secretos; `record_admin_security_control` hereda
esa misma validacion.

Nota 2026-06-10: Etapa 7 incorpora comando seguro para registrar el control
administrativo de seguridad. `record_admin_security_control` crea o actualiza
`security.admin_mfa_control`, ejecuta la validacion de dominio y escribe stdout
redactado con flags booleanos de modo, vigencia y refs, sin imprimir evidencia,
autorizacion, responsable ni payload crudo.

Nota 2026-06-10: El control `security.admin_mfa_control` queda validado en
dominio por `PlatformSetting.clean()`. La misma regla que consume
`audit_operational_observability` rechaza configuraciones de seguridad
administrativa sin MFA probado, sin aceptacion formal de riesgo vigente, con
referencias faltantes o con payload sensible antes de llegar al gate de Etapa 7.

Nota 2026-06-10: Operacion productiva incorpora guard explicito para MFA
administrativo o aceptacion formal de riesgo. `audit_operational_observability`
revisa `security.admin_mfa_control` sin exponer refs: exige MFA probado con
evidencia, autorizacion y responsable no sensibles, o riesgo aceptado vigente
con las mismas trazas; si falta o contiene payload sensible, Etapa 7 queda
parcial.

Nota 2026-06-10: Django admin de Documentos cierra el bypass manual de
`PoliticaFirmaYNotaria`. La politica documental queda visible en solo lectura
desde admin, sin alta, edicion ni borrado; los cambios operativos deben pasar
por API/backoffice auditado, conservando la traza de `updated` y
`state_changed`.

Nota 2026-06-10: Backoffice Documentos expone el flujo auditado de PDF
generado por sistema. El workspace captura expediente, tipo documental,
version de plantilla, titulo y lineas operativas, ejecuta
`documentos-emitidos/previsualizar-pdf/` para registrar la preview auditada y
solo habilita `documentos-emitidos/generar-pdf/` despues de esa preview. El
formulario generico queda reservado para carga externa controlada y no crea
documentos `generado_sistema`.

Nota 2026-06-10: Operacion y Conciliacion dejan de usar numeros bancarios
crudos como etiquetas de snapshot/backoffice. `CuentaRecaudadora` expone
`numero_cuenta_redacted`, los snapshots propagan esa etiqueta para cuentas y
mandatos, y los workspaces la usan en tablas, selectores, busqueda y contexto.
La edicion de cuenta carga el detalle explicitamente para conservar el valor
editable sin convertir snapshots de trabajo en superficie de datos bancarios.

Nota 2026-06-10: Backoffice Contratos tolera registros parciales de snapshot.
Los contratos que llegan desde snapshots de otros modulos pueden no incluir
detalle de propiedades, periodos o codeudores; la tabla, badges, filtros,
edicion inline y cambio guiado ahora usan fallbacks seguros o mensajes
controlados sin romper la inspeccion del workspace.

Nota 2026-06-10: Backoffice conserva los datos cargados por snapshots frente
a cargas diferidas. El loader solo escribe estados cuando la carga
legacy/detail correspondiente esta habilitada, evitando que fallbacks capturados
sobrescriban vistas como Cobranza o Audit. Los filtros de contratos tambien
toleran contratos parciales expuestos por snapshots de otros modulos, sin
romper la inspeccion del workspace.

Nota 2026-06-10: Backoffice Audit alinea el cierre de resoluciones manuales de
Conciliacion con los servicios especializados. La UI ya no intenta cerrar
ingresos desconocidos o cargos bancarios con payload generico incompleto; ahora
captura periodo, criterio, evidencia, entidad o movimiento destino segun el
caso y enruta cargos bancarios y transferencias internas al endpoint auditado
correspondiente. El loader conserva el snapshot de Audit y no lo sobrescribe
con cargas legacy deshabilitadas.

Nota 2026-06-10: Backoffice Cobranza alinea la busqueda global de pagos con
la traza operativa visible. El filtro de pagos mensuales cubre tramo
contractual, codigo efectivo, vencimiento, fechas de deposito/deteccion/WebPay,
moneda y traza UF, de modo que los campos visibles se puedan localizar sin
recalcular ni abrir fuentes externas.

Nota 2026-06-07: Backoffice Cobranza alinea el contrato de snapshot de pagos
con la traza UF. El snapshot de `pagos` expone `periodo_contractual`,
`moneda_calculo`, `uf_fecha_usada`, `uf_valor_usado`, `uf_source_key`,
fechas operativas y `codigo_conciliacion_efectivo`, permitiendo que el
workspace muestre y filtre la misma traza que ya entrega la API de pagos.

Nota 2026-06-07: Backoffice Cobranza hace visible la traza operativa completa
del pago mensual. La tabla de pagos muestra tramo contractual, codigo efectivo
de conciliacion y fechas de deposito/deteccion ya expuestas por el snapshot,
ademas de la traza UF, para revisar pagos sin recalcular ni abrir fuentes
externas.

Nota 2026-06-06: Backoffice Cobranza muestra distribucion economica de pagos.
El snapshot de `pagos` ahora incluye `distribuciones_detail` con beneficiario,
porcentaje snapshot, monto devengado, monto facturable, monto conciliado y
bandera DTE; el workspace muestra esos datos y el buscador global los cubre sin
recalcular ni abrir fuentes externas.

Nota 2026-06-06: Backoffice Canales muestra trazabilidad de recordatorios
programados. El snapshot de `notificaciones_cobranza` ahora expone
arrendatario, mes/ano, estado, vencimiento y monto facturable del pago, ademas
de estado/dias de configuracion; el workspace resuelve esos datos para revisar
cadencia y mensaje asociado sin abrir proveedores externos.

Nota 2026-06-06: Backoffice Canales muestra trazabilidad operativa de mensajes
salientes. El snapshot expone gate/canal, identidad de envio, contrato,
arrendatario, documento, usuario, `enviado_at`, traza y `provider_payload`
redactados; el workspace los resuelve para inspeccion local y el buscador
global cubre esos campos sin abrir Email, WhatsApp ni proveedores externos.

Nota 2026-06-06: Backoffice Cobranza muestra el resumen completo de estado de
cuenta. El workspace expone pagos abiertos/atrasados, repactaciones activas,
codigos residuales activos, meses evaluados, pagos en plazo/fuera de plazo,
meses excluidos por falta de registro operativo, saldo total, score y
observaciones ya redactadas por snapshot/API, y el buscador global cubre esos
campos.

Nota 2026-06-06: Backoffice Cobranza muestra repactaciones y codigos
residuales. El snapshot operativo ahora incluye `codigos_residuales`, y el
workspace lista repactaciones con deuda, plan, saldo, estado y excepcion
parcial redactada, ademas de codigos `CCR-XXXXXX` con arrendatario, contrato
origen, saldo, estado y fecha de activacion.

Nota 2026-06-06: Backoffice Cobranza expone WebPay local controlado.
El workspace permite preparar intentos WebPay desde un pago mensual con
gate/provider y `return_url_ref` no sensible, confirmar manualmente intentos
`preparado` con `external_ref` y `fecha_pago_webpay`, y mostrar gates/intentos
desde API/snapshot redactados. No abre Transbank ni cambia el estado de cierre
de Etapa 2.

Nota 2026-06-10: Cobranza/WebPay Etapa 2 revalida intentos preparados
existentes antes de reutilizarlos. Si el gate, el pago o la referencia de
retorno ya no pasan la validacion vigente, `prepare_webpay_intent()` degrada el
intento a `bloqueado`, crea resolucion manual y auditoria
`cobranza.webpay_intento.prepared`, y solo crea un nuevo intento preparado si la
solicitud actual sigue siendo valida. No llama Transbank ni usa datos reales.

Nota 2026-06-06: Backoffice Contratos expone cambio guiado de arrendatario.
La UI permite preparar el cambio desde un contrato vigente, seleccionar nuevo
arrendatario, codigo y vigencia del contrato futuro, causal del aviso,
representante legal cuando aplica y resolucion de conflicto de renovacion,
llamando al endpoint auditado `cambio-arrendatario/` sin reescribir deuda ni
identidad historica del contrato saliente.

Nota 2026-06-06: Backoffice Contratos expone resolucion guiada de avisos.
La tabla de `AvisoTermino` muestra registro oportuno o fuera de plazo con su
alerta, y expone la referencia/motivo de `resolucion_conflicto_renovacion`
ya redactados por API para revisar conflictos entre aviso, renovacion ejecutada
y contrato futuro sin reescribir efectos producidos.

Nota 2026-06-05: Etapa 1 alinea `audit_stage1_matrix` con el contrato de
trazabilidad usado por etapas posteriores. El auditor y los wrappers exponen
`sections.source_trace`, `sections.source_trace_sensitive`,
`sections.final_evidence` y `sections.final_evidence_sensitive`, separando
fuente/responsable faltante de refs sensibles sin imprimir valores.

Nota 2026-06-06: Los wrappers de gates Etapas 2, 3, 4, 5 Contabilidad,
Documentos, Etapa 6 y Etapa 7 ahora exigen tambien `sections.final_evidence`
en el JSON de readiness y, para fuentes evidenciales, verifican que cada ref
final quede trazable y no sensible. Esto evita aceptar un gate que solo pruebe
ausencia de sensibilidad sin probar presencia de evidencia final.

Nota 2026-06-06: Canales/Etapa 2 mueve la auditoria de materializacion de
recordatorios al servicio. `materialize_payment_notification_schedule()` crea
`canales.notificacion_cobranza.materialized` dentro de la misma transaccion que
crea, realinea u omite recordatorios, y `audit_stage2_cobranza_readiness`
reporta `stage2.notification_schedule.materialization_audit_missing` para
snapshots heredados sin evento con actor y periodo alineado.

Nota 2026-06-12: Canales normaliza la evidencia de configuraciones de
notificacion antes de persistir. `ConfiguracionNotificacionContrato.clean()`,
`save()` y `ConfiguracionNotificacionContratoSerializer` recortan
`evidencia_configuracion_ref` para que API, snapshot y readiness comparen una
referencia canonica no sensible sin espacios crudos.

Nota 2026-06-12: Canales normaliza el motivo de notificaciones de cobranza
omitidas antes de persistir. `NotificacionCobranzaProgramada.clean()` y
`save()` recortan `motivo_estado` para que API, snapshot, backoffice y
readiness comparen un motivo operativo canonico no sensible sin espacios
crudos.

Nota 2026-06-12: Canales normaliza la procedencia de mensajes salientes antes
de persistir. `MensajeSaliente.clean()` y `save()` recortan `external_ref` y
`motivo_bloqueo` para que envio manual, fallback, API, snapshot y readiness
comparen referencias y motivos canonicos no sensibles sin espacios crudos.

Nota 2026-06-12: Canales normaliza el destinatario de mensajes salientes antes
de persistir. `MensajeSaliente.clean()` y `save()` recortan `destinatario`
junto con la procedencia operativa para que envio manual, API, snapshot,
backoffice y readiness comparen un destino canonico sin espacios crudos.

Nota 2026-06-06: Backoffice Canales alinea el formulario y la tabla de gates
con las refs operativas aceptadas por dominio/readiness. El alta de
`CanalMensajeria` ahora puede enviar `credencial_validada_ref` como alternativa
de credencial Email y `template_aprobado_ref` para WhatsApp, y la tabla muestra
prueba, OAuth, credencial o template desde `restricciones_operativas`
redactadas, sin abrir proveedores externos.

Nota 2026-06-12: Canales normaliza la evidencia del gate antes de persistir.
`CanalMensajeria.clean()` y `CanalMensajeriaSerializer` recortan
`evidencia_ref` para que gates Email/WhatsApp, API, snapshot y readiness
comparen una referencia canonica no sensible sin espacios crudos.

Nota 2026-06-12: Canales normaliza refs/textos operativos antes de
`full_clean()` y persistencia. `CanalMensajeria`,
`ConfiguracionNotificacionContrato`, `MensajeSaliente` y
`NotificacionCobranzaProgramada` recortan evidencia, destinatario,
procedencia y motivos antes de los validadores de campo, evitando rechazos por
longitud cruda y manteniendo trazas canonicas para API, snapshot, backoffice y
readiness.

Nota 2026-06-06: Backoffice Patrimonio alinea la tabla de propiedades con el
snapshot de `ServicioPropiedad`. La UI tipa, filtra y muestra servicios/gastos
comunes con proveedor o administracion, numero de cliente, estado y
`evidencia_ref` ya redactada por API, de modo que la cobertura exigida por
Contratos/Etapa 1 sea visible sin usar datos reales ni abrir integraciones.

Nota 2026-06-06: Operacion/Etapa 1 alinea `OperationSnapshotView` y
backoffice con la redaccion de credenciales de `IdentidadDeEnvio`. El snapshot
incluye `credencial_ref` redactada, y la UI de identidades la tipa, filtra y
muestra como referencia operativa visible sin exponer secretos ni conectar
proveedores.

Nota 2026-06-06: Backoffice Operacion ahora permite crear y editar
`IdentidadDeEnvio` desde la API auditada. El formulario conserva owner
empresa/socio, canal, remitente, direccion, estado y `credencial_ref` no
sensible para identidades activas, permitiendo preparar cobertura operativa
sin abrir Email, WhatsApp ni proveedores externos.

Nota 2026-06-06: Operacion/Etapa 1 completa el contrato de snapshot de
identidades de envio. `OperationSnapshotView` ahora expone `owner_id` junto a
`owner_tipo`, `owner_display` y `credencial_ref` redactada, de modo que el
backoffice pueda editar una identidad cargada desde snapshot manteniendo el
owner exacto y sin depender de datos reales ni proveedores externos.

Nota 2026-06-06: Operacion/Etapa 1 alinea el backoffice de Mandatos con la
trazabilidad de autoridad operativa ya expuesta por snapshot/API. La UI ahora
filtra y muestra nombre, RUT, evidencia redactada, autorizaciones y vigencia
del mandato, manteniendo referencias sensibles heredadas redaccionadas y sin
abrir integraciones externas.

Nota 2026-06-06: Operacion/Etapa 1 expone las asignaciones de canal en el
snapshot operativo y backoffice. La UI filtra y muestra mandato, canal,
identidad de envio, owner de identidad, prioridad y estados, haciendo visible
la cobertura exigida para contratos vigentes/futuros sin abrir Email,
WhatsApp ni proveedores externos.

Nota 2026-06-06: Backoffice Operacion ahora permite crear y editar
asignaciones de canal desde el endpoint auditado de
`AsignacionCanalOperacion`. El formulario usa los mandatos operativos vigentes
en snapshot, filtra identidades de envio por canal y refresca cobertura tras
guardar, manteniendo Email/WhatsApp como proveedores cerrados.

Nota 2026-06-05: Etapas 2, 3, 4, 5 Contabilidad, Documentos, Etapa 6 y
Reporting alinean el contrato de `source_trace` con Compliance. Las readiness
ahora exponen `sections.source_trace_sensitive` y clasifican `source_label` o
`authorization_ref` con URLs, tokens, credenciales o valores sensibles mediante
issues `*.source_label_sensitive` y `*.authorization_ref_sensitive`, sin
exponer valores y sin mezclarlos con refs faltantes.

Nota 2026-06-05: Etapas 2, 3, 4, 5 Contabilidad, Documentos, Etapa 6 y
Reporting aplican el mismo criterio a referencias finales de cierre. Las
readiness exponen `sections.final_evidence_sensitive` y clasifican refs
finales con URL, token, credencial o valor sensible mediante issues
`*_ref_sensitive`, sin exponer valores ni mezclarlas con refs faltantes.

Nota 2026-06-05: Los gates/readiness detectan eventos `state_changed`
heredados sin metadata minima de transicion. `core.state_transition_audit_readiness`
centraliza la verificacion de `campo_estado`, `estado_anterior` y
`estado_nuevo`; Etapa 1, Etapa 2, Etapa 3, Etapa 4, Etapa 5 Contabilidad,
Documentos y Compliance ahora reportan issues bloqueantes especificos cuando
la traza historica no conserva esos campos, sin exponer valores sensibles ni
usar fuentes externas.

Nota 2026-06-05: SII/Etapa 4 y Renta Anual/Etapa 6 extienden esa cobertura a
eventos `status_updated` tributarios. `audit_stage4_sii_readiness` bloquea
`sii.*.status_updated` sin metadata minima de transicion, y
`audit_stage6_renta_anual_readiness` bloquea `sii.ddjj_preparacion.status_updated`
o `sii.f22_preparacion.status_updated` incompletos, manteniendo el cierre de
ambas etapas condicionado a fuente autorizada y evidencia suficiente.

Nota 2026-06-05: Reporting/Etapa 7 replica el guard anual sobre
`sii.ddjj_preparacion.status_updated` y `sii.f22_preparacion.status_updated`.
`audit_stage7_reporting_readiness` reporta
`stage7.reporting.audit_annual_status_transition_metadata_missing` si la traza
que sustenta el resumen tributario anual no conserva metadata minima de
transicion.

Nota 2026-06-13: La API de Reporting tributario anual bloquea eventos
`status_updated` DDJJ/F22 existentes sin `campo_estado`, `estado_anterior` o
`estado_nuevo` cuando pertenecen a documentos incluidos en la respuesta
solicitada. La validacion queda acotada al reporte para no bloquear por eventos
ajenos al scope consultado.

Nota 2026-06-05: Operacion productiva endurece el payload de evidencia del
release gate. `run-stage7-readiness-gate.ps1` clasifica
`stage7.restore_payload_sensitive`, `stage7.public_smoke_payload_sensitive` y
`stage7.final_acceptance_payload_sensitive` si la evidencia JSON de restore,
smoke publico o aceptacion final conserva payload sensible o claves de
credenciales, sin exponer valores y sin cerrar aunque los refs esperados sean
no sensibles.

Nota 2026-06-05: Operacion productiva endurece la redaccion de rutas de
screenshot en evidencia de smoke publico. `run-stage7-readiness-gate.ps1`
clasifica como salida no redactada variantes como `screenshot_path`,
`screenshot_file`, `screenshotUrl` o `screenshotLocation`, no solo
`screenshotPath`; `run-acceptance-workflows.ps1` valida el mismo contrato sin
emitir rutas ni valores crudos.

Nota 2026-06-05: Operacion productiva endurece aliases de diagnostico crudo en
evidencia de smoke publico. El release gate ahora trata `user_name`,
`screen_text`, `bodyText`, `errorMessage`, `stackTrace` y variantes
equivalentes como salida no redactada; `errorCode` sigue siendo el unico
resumen de error permitido.

Nota 2026-06-03: Contratos/Etapa 1 exige actor trazable en auditorias de
ciclo contractual guiado. `execute_automatic_contract_renewal()` y
`execute_tenant_replacement()` fallan antes de mutar si una llamada interna no
entrega usuario o `actor_identifier`; los eventos de renovacion automatica y
cambio de arrendatario guardan ese actor, y `Contrato.full_clean()`,
`PeriodoContractual.full_clean()` y `audit_stage1_matrix` ya no aceptan eventos
heredados sin actor como traza suficiente.

Nota 2026-06-03: Contratos/Etapa 1 endurece la trazabilidad de terminaciones
anticipadas con ultimo mes parcial. `Contrato.full_clean()` y
`audit_stage1_matrix` ya no aceptan eventos de prorrata sin actor o con
metadata desalineada frente a `terminacion_anticipada_prorrata_ref`,
`terminacion_anticipada_prorrata_motivo` y `fecha_fin_vigente`; el endpoint de
contratos sigue generando esa auditoria completa dentro de la transaccion.

Nota 2026-06-03: Canales/Etapa 2 bloquea recordatorios programados obsoletos.
`NotificacionCobranzaProgramada.full_clean()` exige que una notificacion
`programada` pertenezca a un pago `pendiente` o `atrasado`, y
`materialize_payment_notification_schedule()` retira programaciones activas de
pagos no cobrables pasandolas a `omitida` con motivo no sensible. Readiness
emite `stage2.notification_schedule.scheduled_for_non_collectable_payment`
para snapshots heredados con programaciones activas sobre pagos no cobrables,
sin abrir proveedores ni usar datos reales.

Nota 2026-06-03: Canales/Etapa 2 alinea recordatorios de cobranza con mensajes
ya enviados. `NotificacionCobranzaProgramada.full_clean()` acepta que una
notificacion `preparada` conserve un `MensajeSaliente` alineado en estado
`preparado`, `bloqueado` o `enviado`; readiness sigue bloqueando mensajes
desalineados o invalidos, sin abrir proveedores ni usar datos reales.

Nota 2026-06-03: Canales/Etapa 2 endurece la ventana operativa WhatsApp.
`MensajeSaliente.full_clean()` y `audit_stage2_cobranza_readiness` detectan
mensajes WhatsApp heredados preparados/enviados fuera de `08:00-21:00
America/Santiago`; la readiness emite `stage2.message.whatsapp_window_violation`
sin abrir proveedores ni usar datos reales.

Nota 2026-06-02: Canales/Etapa 2 endurece rehabilitaciones WhatsApp.
`audit_stage2_cobranza_readiness` exige que una rehabilitacion heredada
conserve la traza original del bloqueo, evento y alerta administrativa
alineados, evento dedicado de rehabilitacion con actor/ref/fecha y sin alertas
de bloqueo aun abiertas.

Nota 2026-06-02: Canales/Etapa 2 endurece la traza de fallback WhatsApp.
`audit_stage2_cobranza_readiness` ya no acepta un Email preparado/enviado
anterior al bloqueo o fallo WhatsApp como alternativa valida solo por compartir
contrato, arrendatario o documento; el Email fallback debe estar alineado por
contexto y preparado/enviado despues del estado bloqueado/fallido, o debe
existir alerta/fallback con evento dedicado.

Nota 2026-06-02: Conciliacion/Etapa 3 deja de contar conexiones bancarias con
error proveedor reciente como listas para `provider_sync`. Si `ultimo_error_at`
es posterior a `ultimo_exito_at`, `bank_provider_sync_blocking_reason` bloquea
nuevas importaciones provider sync y `audit_stage3_conciliacion_readiness`
mantiene `ready_primary_movements=0`, `stage3.bank_connection.recent_error` y
`stage3.movement.provider_sync_connection_not_ready` para snapshots heredados.

Nota 2026-06-02: Cobranza y Canales cubre auditoria de preparacion WebPay en
readiness. `audit_stage2_cobranza_readiness` emite
`stage2.webpay_intent.prepared_event_missing` para intentos WebPay preparados o
bloqueados sin evento `cobranza.webpay_intento.prepared` completo y alineado.

Nota 2026-06-02: Operacion productiva clasifica `FinalAcceptanceRef` simple
sensible. El release gate de Etapa 7 emite `stage7.final_acceptance_ref_sensitive`
cuando se entrega una referencia simple sensible sin evidencia JSON final, sin
exponer el valor ni mezclarla con aceptacion faltante generica.

Nota 2026-06-02: Operacion productiva separa codigos de fuente evidencial en
Etapa 7. `run-stage7-readiness-gate.ps1` emite codigos especificos para
restore, smoke publico y aceptacion final con `source_kind` sintetico/local o
invalido, sin agruparlos como refs faltantes o evidencia autorizada incompleta.

Nota 2026-06-02: Operacion productiva alinea mensajes y acceptance del restore
autorizado. El release gate de Etapa 7 exige `backup_ref` o
`backup_evidence_ref` no sensible, prueba que `backup_evidence_ref` habilita el
subgate de restore y elimina referencias residuales a `backup_file` como
alternativa valida.

Nota 2026-06-02: Operacion productiva endurece evidencia de restore. El release
gate de Etapa 7 clasifica `stage7.restore_backup_file_not_allowed` si una
evidencia autorizada intenta usar `backup_file` crudo como respaldo; para cierre
solo cuentan `backup_ref` o `backup_evidence_ref` no sensibles.

Nota 2026-06-05: Operacion productiva endurece aliases de archivo/ruta cruda en
evidencia de restore. El release gate ahora trata variantes como `backupPath`,
`backup_url`, `snapshotPath`, `dumpFile` o `planned_backup_file` igual que
`backup_file`: no habilitan cierre y deben reemplazarse por `backup_ref` o
`backup_evidence_ref` no sensibles.

Nota 2026-06-02: Operacion productiva cierra el gate de evidencia de smoke
publico no redactada. `run-stage7-readiness-gate.ps1` clasifica
`stage7.public_smoke_output_not_redacted` si el JSON conserva `username`,
extractos de pantalla, rutas de screenshot o errores crudos, aun cuando los
cuatro roles pasen login UI y las refs de ambiente sean validas.

Nota 2026-06-02: Operacion productiva refuerza notas de senales runtime.
`OperationalRuntimeSignal.clean()` rechaza `notes` con URLs, tokens o
credenciales, el comando `record_operational_runtime_signal` hereda ese guard
y `audit_operational_observability` clasifica notas heredadas sensibles sin
exponer valores.

Nota 2026-06-02: Operacion productiva redacciona stdout de senales runtime.
`record_operational_runtime_signal` guarda el payload validado, pero imprime
solo `has_evidence_ref`, traza booleana y valor canonico por tipo de senal; no
devuelve `evidence_ref`, refs de autorizacion ni payload bruto.

Nota 2026-06-02: Contabilidad/Etapa 5 exige linea explicita para saldos
finales de liquidacion. `LiquidacionMensual.clean()` bloquea liquidaciones
preparadas/aprobadas con `saldo_final_clp` distinto de cero si no tienen
`LineaLiquidacionMensual` `saldo_final_explicado` o si el total de esas lineas
no cuadra con el saldo final; `audit_stage5_contabilidad_readiness` reporta
`stage5.liquidation_final_balance_line_missing` o
`stage5.liquidation_final_balance_line_mismatch` para snapshots heredados.

Nota 2026-06-02: Contabilidad/Etapa 5 exige vinculo exacto entre cierre
aprobado y liquidacion mensual de empresa. `audit_stage5_contabilidad_readiness`
reporta `stage5.liquidation_missing_for_approved_close` cuando un snapshot
heredado conserva una `LiquidacionMensual` preparada/aprobada del mismo periodo
pero sin `cierre_contable` apuntando al `CierreMensualContable` aprobado.

Nota 2026-06-02: Reporting/Etapa 7 alinea la API de resumen tributario anual
con readiness de referencias finales del proceso anual. El endpoint bloquea
`ProcesoRentaAnual` aprobado, observado, rectificado o presentado si falta
`paquete_ddjj_ref` o `borrador_f22_ref`, o si esas referencias contienen URLs,
tokens o credenciales, sin exponer los valores en la respuesta.

Nota 2026-06-12: Reporting/Etapa 7 normaliza parametros de query antes de
validar, filtrar o decidir cache. Los endpoints de dashboard, libros por
periodo, resumen mensual, resumen tributario anual y resoluciones manuales
recortan espacios de `mode`, `refresh`, `status`, `periodo`, `empresa_id`,
`anio`, `mes` y `anio_tributario`, evitando falsos faltantes, cache no
refrescado y filtros no canonicos.

Nota 2026-06-12: Operacion productiva/Etapa 7 normaliza trazas de
observabilidad antes de validar y persistir. `OperationalRuntimeSignal` recorta
`evidence_ref`, `source_label`, `authorization_ref` y `notes` antes de
`full_clean()`/`save()`, y `security.admin_mfa_control` recorta modo, refs,
vigencia y descripcion antes de evaluar el control administrativo, evitando
trazas runtime con espacios crudos y rechazos por longitud antes de canonizar.

Nota 2026-05-31: SII/Etapa 4 alinea mutaciones API y auditoria de vista en
una transaccion. `AuditCreateUpdateMixin`, generacion DTE/F29/anual y cambios
de estado DTE, F29, DDJJ y F22 persisten cambios y eventos auditables dentro
de `transaction.atomic()`; si falla la auditoria, no quedan capacidades,
borradores, procesos anuales ni estados tributarios mutados sin traza de
endpoint. Nota 2026-06-05: los eventos SII de cambio o actualizacion de estado
incorporan metadata minima con campo de estado, estado anterior y estado nuevo,
manteniendo refs sensibles redactadas como `sii_track_id`.

Nota 2026-06-12: SII/Etapa 4 normaliza refs/textos operativos antes de
`full_clean()` y persistencia. `CapacidadTributariaSII`, `DTEEmitido`,
`F29PreparacionMensual`, `ProcesoRentaAnual`, `DDJJPreparacionAnual` y
`F22PreparacionAnual` recortan refs de capacidad, tracking, estados externos,
borradores, paquetes y observaciones antes de validadores de campo, evitando
rechazos por longitud cruda y manteniendo trazas canonicas para API, snapshot,
admin, readiness y auditoria.

Nota 2026-06-13: SII/Etapa 4 valida el artefacto completo antes de persistir
transiciones externas o tributarias avanzadas. `register_dte_status`,
`register_f29_status` y `register_annual_status` ejecutan `full_clean()` sobre
el DTE/F29/DDJJ/F22 actualizado antes de guardar, de modo que la API rechaza
snapshots heredados con capacidad SII de familia incorrecta u otra
inconsistencia de dominio antes de emitir el evento auditable.

Nota 2026-06-13: Reporting/Etapa 7 alinea la API tributaria anual con la
validacion de familia SII de DDJJ/F22. `_assert_annual_tax_traceability()`
bloquea documentos anuales con `capacidad_tributaria.capacidad_key` cruzada
usando `reporting.annual_ddjj_invalid` y `reporting.annual_f22_invalid`,
equivalentes a los bloqueos `stage7.reporting.annual_ddjj_invalid` y
`stage7.reporting.annual_f22_invalid` de readiness.

Nota 2026-06-13: Reporting/Etapa 7 alinea referencias finales DDJJ/F22 entre
API tributaria anual y readiness. `_assert_annual_tax_traceability()` trata
`paquete_ref` y `borrador_ref` vacios o compuestos solo por espacios como
faltantes para estados finales, cubriendo snapshots heredados que saltaron la
normalizacion del modelo antes de devolver el reporte como verificado.

Nota 2026-06-13: Reporting/Etapa 7 bloquea refs documentales anuales sensibles
en API para DDJJ o F22 en cualquier estado trazable. El endpoint tributario anual
emite codigos `reporting.annual_ddjj_ref_sensitive` y
`reporting.annual_f22_ref_sensitive` sin filtrar URLs, tokens ni credenciales,
alineando la ruta API con `audit_stage7_reporting_readiness`.

Nota 2026-06-13: Reporting/Etapa 7 bloquea payloads anuales sensibles en API
cuando el proceso, DDJJ o F22 estan en cualquier estado trazable. La ruta tributaria
anual emite codigos `reporting.annual_process_sensitive_payload`,
`reporting.annual_ddjj_sensitive_payload` y
`reporting.annual_f22_sensitive_payload` sin exponer claves o valores
sensibles, evitando entregar reportes validos sobre datos heredados sensibles.

Nota 2026-05-31: Canales/Etapa 2 alinea altas y ediciones API de gates y
configuraciones de notificacion con auditoria atomica. `AuditCreateUpdateMixin`
en Canales persiste `created`, `updated` y `state_changed` dentro de
`transaction.atomic()`; si falla la auditoria, no quedan gates ni
configuraciones mutadas sin traza de endpoint. Nota 2026-06-05: los eventos
`canales.*.state_changed` incorporan metadata minima con campo de estado,
estado anterior y estado nuevo para auditar la transicion sin reconstruccion
externa.

Nota 2026-05-31: Documentos/Etapa 5 alinea updates genericos y auditoria de
vista en una transaccion. `AuditCreateUpdateMixin.perform_update()` persiste
la mutacion documental junto con `documentos.*.updated` y, cuando aplica,
`documentos.*.state_changed` dentro de `transaction.atomic()`; si falla la
auditoria, no quedan expedientes, politicas, plantillas ni documentos mutados
sin traza de endpoint. Nota 2026-06-05: los eventos
`documentos.*.state_changed`, incluyendo formalizacion, incorporan metadata
minima con campo de estado, estado anterior y estado nuevo.

Nota 2026-05-31: Auth/Etapa 0 alinea tokens persistentes y auditoria de
sesion en una transaccion. `LoginView.post()` crea o reutiliza `Token` y
registra `auth.login.succeeded` dentro de `transaction.atomic()`, y
`LogoutView.post()` elimina tokens y registra `auth.logout` dentro de la misma
transaccion; si falla la auditoria, no quedan tokens creados o eliminados sin
traza de vista.

Nota 2026-05-31: Compliance/Etapa 0 alinea altas y ediciones API de
politicas de retencion con auditoria atomica. `AuditCreateUpdateMixin` en
Compliance persiste `created`, `updated` y `state_changed` dentro de la misma
transaccion que `serializer.save()`; si falla la auditoria, no quedan
politicas de retencion creadas o mutadas sin traza de vista. Nota 2026-06-05:
los eventos `compliance.politica_retencion.state_changed` incorporan metadata
minima con campo de estado, estado anterior y estado nuevo.

Nota 2026-06-12: Compliance/Etapa 0 normaliza metadata visible antes de
validar y persistir. `PoliticaRetencionDatos` recorta `evento_inicio`, y
`ExportacionSensible` recorta `motivo`, `encrypted_ref`, strings dentro de
`scope_resumen` y canoniza `payload_hash` a lowercase; la readiness bloquea
snapshots heredados con `evento_inicio`, metadata visible o `payload_hash` no
canonicos.

Nota 2026-05-31: Contabilidad/Etapa 5 alinea mutaciones API y auditoria de
vista en una transaccion. `AuditCreateUpdateMixin`,
`EventoContableListCreateView`, `EventoContablePostView`,
`CierreMensualPrepareView`, `CierreMensualApproveView` y
`CierreMensualReopenView` persisten cambios y eventos auditables de forma
atomica; si falla la auditoria, no quedan catalogos, eventos, asientos,
obligaciones, snapshots, cierres ni efectos de reapertura mutados sin traza.
Nota 2026-06-05: los eventos `contabilidad.*.state_changed` incorporan
metadata minima con campo de estado, estado anterior y estado nuevo para
catalogos contables actualizados por API.

Nota 2026-05-31: Conciliacion/Etapa 3 alinea el reintento manual de match
exacto con auditoria atomica. `MovimientoBancarioRetryMatchView.post()`
ejecuta `reconcile_exact_movement()` y registra
`conciliacion.movimiento_bancario.match_retried` dentro de la misma
transaccion; si falla esa auditoria de vista, no quedan pagos, ingresos
desconocidos, resoluciones supersedidas ni movimientos mutados por el
reintento.
Nota 2026-06-06: Conciliacion/Etapa 3 centraliza esa auditoria en
`reconcile_exact_movement()`. La vista de creacion conserva la auditoria
`created`, pero `match_attempted` y `match_retried` nacen desde el servicio que
muta pagos, codigos residuales, ingresos desconocidos, resoluciones manuales y
eventos contables, cubriendo tambien llamadas internas controladas; si falla
esa auditoria de servicio, no quedan mutaciones de conciliacion sin traza.
Nota 2026-06-06: `audit_stage3_conciliacion_readiness` tambien bloquea
snapshots heredados donde movimientos en `ingreso_desconocido`,
`manual_requerida` o `conciliado_exacto` no conservan `match_attempted` o
`match_retried` alineado al movimiento, o conservan metadata de movimiento
desalineada.
Nota 2026-06-06: la alineacion de auditoria de match exige metadata no
sensible completa (`status`, movimiento, conexion bancaria, cuenta
recaudadora, estado de conciliacion, tipo y fecha). Un evento de match hueco o
parcial ya no cuenta como evidencia suficiente para readiness de Etapa 3.
Nota 2026-06-06: la readiness tambien valida que `metadata.status` sea
compatible con el camino de conciliacion permitido: match automatico a pago o
codigo residual, ingreso desconocido, clasificacion manual de cargo o
regularizacion manual posterior de ingreso desconocido.
Nota 2026-06-06: para `matched_payment` y `matched_residual`, la readiness
exige ademas que la metadata conserve el target conciliado exacto
(`pago_mensual_id` o `codigo_cobro_residual_id`), evitando que un evento con
status correcto apunte a otro pago o codigo residual.

Nota 2026-05-31: CobranzaActiva/Etapa 2 alinea mutaciones API y auditoria
de vista en una transaccion. `AuditCreateUpdateMixin` en Cobranza y los
overrides de UF, pagos, refresco de mora, materializacion local, movimientos
de garantia, repactaciones y rebuild de estado de cuenta persisten cambios y
eventos auditables de forma atomica; si falla la auditoria, no quedan cambios
operativos de Cobranza sin traza. Nota 2026-06-05: los eventos
`cobranza.*.state_changed` incorporan metadata minima con campo de estado,
estado anterior y estado nuevo para pagos, garantias, gates y estados
expuestos por el mixin de vista.

Nota 2026-05-31: Contratos/Etapa 1 alinea altas y ediciones API con auditoria
atomica. `AuditCreateUpdateMixin` y los overrides de arrendatario/contrato
persisten `created`, `updated`, `state_changed` y trazas contractuales
derivadas dentro de la misma transaccion que `serializer.save()`; si falla la
auditoria, no quedan arrendatarios, contactos, contratos anidados ni estados
contractuales mutados sin traza. Nota 2026-06-05: los eventos
`contratos.*.state_changed` incorporan metadata minima con campo de estado,
estado anterior y estado nuevo para dejar la transicion auditable sin
reconstruirla desde el historial.

Nota 2026-05-31: Operacion/Etapa 1 alinea altas y ediciones API con auditoria
atomica. `AuditCreateUpdateMixin` en Operacion persiste `created`, `updated`
y `state_changed` dentro de la misma transaccion que `serializer.save()`; si
falla la auditoria, no quedan cuentas recaudadoras, identidades, mandatos ni
asignaciones de canal mutadas sin traza. Nota 2026-06-05: los eventos
`operacion.*.state_changed` incorporan metadata minima con campo de estado,
estado anterior y estado nuevo para dejar la transicion auditable sin
reconstruirla desde el historial.

Nota 2026-05-31: Patrimonio/Etapa 1 alinea altas y ediciones API con auditoria
atomica. `AuditCreateUpdateMixin` en Patrimonio persiste `created`, `updated`
y `state_changed` dentro de la misma transaccion que `serializer.save()`; si
falla la auditoria, no quedan socios, empresas, comunidades, propiedades,
servicios ni participaciones anidadas mutadas sin traza. Nota 2026-06-05: los
eventos `patrimonio.*.state_changed` incorporan metadata minima con campo de
estado, estado anterior y estado nuevo para dejar la transicion auditable sin
reconstruirla desde el historial.

Nota 2026-05-31: Conciliacion/Etapa 3 alinea creacion de movimientos
bancarios, match exacto local y auditoria en una transaccion unica.
`MovimientoBancarioListCreateView.perform_create()` persiste el movimiento,
crea `conciliacion.movimiento_bancario.created`, ejecuta
`reconcile_exact_movement()` y registra
`conciliacion.movimiento_bancario.match_attempted` de forma atomica; si falla
la auditoria posterior, no quedan movimiento, pago mutado, ingreso desconocido
ni match sin traza completa. Nota 2026-06-05: los eventos
`conciliacion.*.state_changed` incorporan metadata minima con campo de estado,
estado anterior y estado nuevo para conexiones bancarias y cuadraturas
actualizadas por API.
Nota 2026-06-06: el evento `match_attempted` ya no depende de la vista; lo
emite `reconcile_exact_movement()` con metadata no sensible de movimiento,
conexion, cuenta, tipo, fecha, estado y resultado del match.
La readiness de Etapa 3 clasifica como bloqueante la ausencia de esa traza o
su metadata desalineada en movimientos ya clasificados/conciliados.

Nota 2026-05-31: Compliance/Etapa 0 alinea accesos denegados de exportaciones
sensibles con auditoria atomica. `ExportacionContentView` ejecuta
`get_export_payload()` y el evento `compliance.exportacion_sensible.access_denied`
o `accessed` en una sola transaccion; si falla la auditoria al negar una
descarga vencida, no queda la exportacion normalizada a `expirada` sin traza.

Nota 2026-06-03: Compliance/Etapa 0 alinea revocaciones vencidas con auditoria
atomica. `revoke_export()` normaliza una exportacion preparada vencida a
`expirada` y crea `compliance.exportacion_sensible.access_denied` con
`denied_operation=revoke` en la misma transaccion; si falla la auditoria, la
exportacion no queda marcada `expirada` sin traza y no se crea evento `revoked`.

Nota 2026-05-31: Conciliacion/Etapa 3 alinea supersesiones de resoluciones
manuales con auditoria atomica. `supersede_manual_resolutions_for_movement()`
ejecuta la marca `superseded` y el evento `audit.manual_resolution.superseded`
en una sola transaccion; si falla la auditoria, la resolucion manual conserva
su estado abierto y no queda una supersesion sin traza.

Nota 2026-05-31: Cobranza/WebPay Etapa 2 alinea el gate local de
confirmacion manual con la auditoria requerida. `audit_stage2_cobranza_readiness`
clasifica intentos `confirmado_manual` heredados si falta el evento
`cobranza.webpay_intento.confirmed_manually`, si no tiene actor o si su metadata
no coincide con `external_ref`, `pago_mensual_id` y `fecha_pago_webpay`; el
servicio mantiene la confirmacion y su auditoria en una sola transaccion.

Nota 2026-05-31: Cobranza/WebPay Etapa 2 alinea la preparacion de intentos
con auditoria atomica. `prepare_webpay_intent()` crea o repara el evento
`cobranza.webpay_intento.prepared` dentro de la misma transaccion que persiste
el intento preparado o bloqueado; si falla la auditoria, no queda intento
WebPay sin traza.

Nota 2026-05-31: Canales/Etapa 2 realinea fallbacks WhatsApp
preexistentes. `ensure_whatsapp_fallback_resolution()` ya no acepta una
`ManualResolution` abierta como suficiente si su metadata o evento dedicado
quedaron desactualizados: refresca la traza con el motivo/contexto actual y
crea `canales.whatsapp.fallback_required` cuando no existe un evento alineado
con actor.

Nota 2026-05-31: Documentos/Etapa 5 alinea versiones correctivas con
auditoria atomica. `DocumentoEmitidoListCreateView.perform_create()` persiste
la version correctiva y los eventos `created` y
`corrective_version_created` dentro de la misma transaccion; si falla la
auditoria dedicada, se revierte tambien el documento correctivo y no queda
traza huerfana para que readiness la detecte despues.

Nota 2026-05-31: Contabilidad/Etapa 5 alinea la aprobacion de cierre mensual
con readiness de liquidaciones. `approve_monthly_close()` exige una
`LiquidacionMensual` de empresa preparada para el mismo cierre/periodo antes
de pasar a `aprobado`, y deja la referencia de liquidacion en
`resumen_obligaciones`; los bootstraps demo crean esa liquidacion local antes
de aprobar.

Nota 2026-05-31: Canales/Etapa 2 alinea servicios de mensajes con el guard de
dominio. `prepare_message()` valida el `MensajeSaliente` antes de persistir
mensajes preparados o bloqueados, y `mark_message_as_sent()` revalida antes de
marcar envio manual, impidiendo que llamadas internas usen un
`CanalMensajeria` de otro canal.

Nota 2026-05-31: Compliance/Etapa 0 exige trazabilidad minima tambien desde
el servicio de preparacion. `prepare_sensitive_export()` rechaza llamadas
internas sin motivo operativo o sin actor creador trazable antes de persistir
`ExportacionSensible`, y readiness clasifica exportaciones heredadas sin
motivo mediante `compliance.export_motive_missing`.

Nota 2026-05-31: Compliance/Etapa 0 exige actor trazable tambien desde el
servicio de revocacion. `revoke_export()` rechaza llamadas internas sin
`actor_user` antes de mutar la exportacion o crear el evento
`compliance.exportacion_sensible.revoked`, alineando el servicio con readiness
de auditorias sin actor.

Nota 2026-05-31: Compliance/Etapa 0 exige motivo no sensible tambien desde
el servicio de revocacion. `revoke_export()` rechaza llamadas internas sin
motivo trazable o con URLs, correos, tokens, bearer, claves o credenciales
antes de persistir la revocacion, alineando API, servicio y readiness de
revocaciones sensibles.

Nota 2026-05-31: Canales/Etapa 2 preserva omisiones operativas de
recordatorios locales. `materialize_payment_notification_schedule()` mantiene
`NotificacionCobranzaProgramada` en estado `omitida` con su motivo operativo
no sensible cuando rematerializa cadencias, evitando reabrir cobranza o borrar
la decision trazable de omision.

Nota 2026-05-31: Contratos/Etapa 1 cierra alta y edicion manual no auditada
desde Django admin. `ArrendatarioAdmin`,
`ContactoPagoArrendatarioAdmin`, `ContratoAdmin`,
`ContratoPropiedadAdmin`, `PeriodoContractualAdmin`,
`CodeudorSolidarioAdmin` y `AvisoTerminoAdmin` quedan como inspeccion
redactada sin alta, edicion ni borrado manual; las mutaciones contractuales
deben pasar por API, estado, vigencia o flujo auditado.

Nota 2026-05-31: Conciliacion/Etapa 3 cierra el label crudo de conexion
bancaria en movimientos importados. `MovimientoBancarioImportadoAdmin`
reemplaza `conexion_bancaria` por `conexion_bancaria_redacted` en `fields` y
`list_display`, evitando exponer la relacion bancaria directa desde el admin y
manteniendo referencias bancarias sensibles heredadas redactadas.

Nota 2026-05-31: Patrimonio/Etapa 1 cierra alta y edicion manual no auditada
desde Django admin. `SocioAdmin`, `EmpresaAdmin`,
`ComunidadPatrimonialAdmin`, `ParticipacionPatrimonialAdmin`,
`RepresentacionComunidadAdmin`, `PropiedadAdmin` y
`ServicioPropiedadAdmin` quedan como inspeccion redactada sin alta, edicion ni
borrado manual; las mutaciones estructurales deben pasar por API, vigencia,
estado o flujo auditado.

Nota 2026-05-31: Operacion/Etapa 1 cierra exposicion de datos bancarios
directos en Django admin. `CuentaRecaudadoraAdmin` reemplaza `numero_cuenta`
y `titular_rut` por versiones redactadas y deja de buscarlos; ademas
`MandatoOperacionAdmin` muestra la cuenta asociada como
`cuenta_recaudadora_redacted`, evitando labels basados en el `__str__` que
incluyen numero bancario.

Nota 2026-05-31: Conciliacion/Etapa 3 cierra exposicion de numeros de cuenta
recaudadora en Django admin. `ConexionBancariaAdmin`,
`IngresoDesconocidoAdmin` y `CuadraturaBancariaAdmin` reemplazan labels crudos
de `cuenta_recaudadora` por `cuenta_recaudadora_redacted` y dejan de buscar por
`cuenta_recaudadora__numero_cuenta`, manteniendo refs bancarias heredadas
redactadas y mutaciones operativas bajo API/servicios auditados.

Nota 2026-05-31: PlataformaBase/Auth cierra exposicion cruda de
`legacy_reference` en Django admin de usuarios. `LeaseManagerUserAdmin`
mantiene la gestion operativa de usuarios, pero reemplaza la referencia legacy
por `legacy_reference_redacted` y conserva metadata redactada y borrado manual
deshabilitado.

Nota 2026-05-31: Auditoria/Etapa 0 deja `AuditEventAdmin` y
`ManualResolutionAdmin` como superficies solo lectura. Ambos admins conservan
redaccion de campos sensibles y bloquean alta, cambio y borrado manual, para
que eventos y resoluciones se originen por API, servicios o flujos auditados.

Nota 2026-05-29: Auditoria/Etapa 0 hace trazable el ciclo generico de
`ManualResolution`. El endpoint generico crea resoluciones solo abiertas,
ignora intentos de suplantar `requested_by`/`resolved_by`, exige rationale para
cerrar, estampa `resolved_by` y `resolved_at` con el usuario actual y bloquea
reaperturas de resoluciones terminales. Tambien crea `AuditEvent` dedicado y
transaccional para creacion, cambios de estado y ediciones comunes; si falla
esa auditoria, la resolucion no queda creada ni mutada.

Nota 2026-05-29: Auditoria/Etapa 0 cierra exposicion de referencias sensibles
heredadas en API y snapshot. `AuditEventSerializer` redacta actor, entidad,
resumen, request id y metadata; `ManualResolutionSerializer` redacta
scope, resumen, rationale y metadata; y la API generica de resoluciones
manuales rechaza nuevas referencias sensibles en campos textuales o metadata.

Nota 2026-05-29: Documentos/Etapa 5 incorpora registro canonico de plantillas
documentales versionadas. `PlantillaDocumental` exige tipo documental,
version, referencia no sensible, checksum SHA-256 y estado; `DocumentoEmitido`
y la generacion PDF rechazan versiones sin plantilla activa, snapshot/API/admin
redactan refs heredadas sensibles y readiness bloquea plantillas faltantes,
invalidas o documentos sin plantilla activa.

Nota 2026-05-29: Documentos/Etapa 5 hace inmutable la evidencia tecnica de
plantillas documentales ya usadas. Una `PlantillaDocumental` referenciada por
documentos emitidos no puede cambiar tipo, version, referencia, checksum ni
estado desde dominio/API; solo queda editable la descripcion operativa.

Nota 2026-05-29: Documentos/Etapa 5 hace inmutable la politica documental ya
usada. Una `PoliticaFirmaYNotaria` referenciada por documentos emitidos no
puede cambiar tipo documental, requisitos de firma/notaria/documentacion,
modo de firma ni estado desde dominio/API, evitando reinterpretar evidencia
historica sin versionado de politica por documento.

Nota 2026-05-29: Documentos/Etapa 5 aplica scope tambien al comprobante
notarial durante `formalizar/`. `DocumentoFormalizarSerializer` recibe el
`request` del endpoint y filtra `comprobante_notarial` con
`scope_documento_queryset`, evitando que un operador use evidencia documental
de expedientes fuera de su cartera visible.

Nota 2026-05-29: Documentos/Etapa 5 hace atomica la formalizacion documental.
`formalizar/` guarda el estado formalizado y crea los eventos
`documentos.documento_emitido.formalized` y `state_changed` dentro de la misma
transaccion, evitando dejar documentos formalizados sin auditoria dedicada si
falla la escritura del evento.

Nota 2026-05-29: Patrimonio/Etapa 1 completa la salida operativa de owners
locales. `Socio.inactive_dependency_errors()` y
`ComunidadPatrimonial.inactive_state_dependency_errors()` bloquean cuentas
recaudadoras y mandatos activos antes de permitir inactivacion; `Socio`
tambien bloquea identidades de envio activas. La API y
`audit_stage1_matrix` comparten la misma regla por validacion de dominio.

Nota 2026-05-29: Operacion/Etapa 1 cierra edicion manual no auditada desde
admin. `CuentaRecaudadoraAdmin`, `IdentidadDeEnvioAdmin`,
`MandatoOperacionAdmin` y `AsignacionCanalOperacionAdmin` conservan inspeccion
redactada, pero deshabilitan alta, edicion y borrado manual para que cuentas,
identidades, mandatos y asignaciones pasen por API, validaciones de dominio,
vigencias, estados o flujos auditados.

Nota 2026-05-29: CobranzaActiva/Etapa 2 cierra edicion manual no auditada
desde admin. `ValorUFDiarioAdmin`, `AjusteContratoAdmin`,
`PagoMensualAdmin`, `GateCobroExternoAdmin`, `IntentoPagoWebPayAdmin`,
`GarantiaContractualAdmin`, `HistorialGarantiaAdmin`,
`RepactacionDeudaAdmin`, `CodigoCobroResidualAdmin` y
`EstadoCuentaArrendatarioAdmin` conservan inspeccion redactada, pero
deshabilitan alta, edicion y borrado manual para que UF, ajustes, pagos,
gates, intentos WebPay, garantias, repactaciones, residuales y estados de
cuenta pasen por API, servicios, reconstruccion, conciliacion o resolucion
formal auditada.

Nota 2026-05-29: SII/Etapa 4 cierra edicion manual no auditada desde admin.
`CapacidadTributariaSIIAdmin`, `DTEEmitidoAdmin`,
`F29PreparacionMensualAdmin`, `ProcesoRentaAnualAdmin`,
`DDJJPreparacionAnualAdmin` y `F22PreparacionAnualAdmin` conservan inspeccion
redactada, pero deshabilitan alta, edicion y borrado manual para que
capacidades, DTE, F29, DDJJ, F22 y procesos anuales pasen por dominio,
servicios, gates y auditoria.

Nota 2026-05-29: Documentos/Etapa 5 cierra edicion manual no auditada desde
admin. `ExpedienteDocumentalAdmin` y `DocumentoEmitidoAdmin` conservan
inspeccion redactada, pero deshabilitan alta, edicion y borrado manual para
que expedientes, emision, formalizacion, correcciones y cambios operativos
documentales pasen por endpoints o servicios auditados.

Nota 2026-05-29: Contabilidad/Etapa 5 cierra edicion manual no auditada desde
admin para artefactos generados. `EventoContableAdmin`,
`AsientoContableAdmin`, `MovimientoAsientoAdmin`,
`ObligacionTributariaMensualAdmin`, `LibroDiarioAdmin`, `LibroMayorAdmin`,
`BalanceComprobacionAdmin`, `CierreMensualContableAdmin` y
`EfectoReaperturaCierreMensualAdmin` conservan inspeccion redactada, pero
deshabilitan alta, edicion y borrado manual para que eventos, asientos,
movimientos, obligaciones, snapshots, cierres y efectos pasen por API,
servicios, gates y auditoria.

Nota 2026-05-29: Conciliacion/Etapa 3 cierra edicion manual no auditada desde
admin. `MovimientoBancarioImportadoAdmin`, `IngresoDesconocidoAdmin`,
`CuadraturaBancariaAdmin` y `TransferenciaIntercuentaAdmin` conservan
inspeccion redactada, pero deshabilitan alta, edicion y borrado manual para
que importaciones, resoluciones, cuadraturas y transferencias pasen por APIs o
servicios auditados.

Nota 2026-05-29: Canales/Etapa 2 cierra edicion manual no auditada desde
admin. `CanalMensajeriaAdmin`, `MensajeSalienteAdmin`,
`ConfiguracionNotificacionContratoAdmin` y
`NotificacionCobranzaProgramadaAdmin` conservan inspeccion redactada, pero
deshabilitan alta, edicion y borrado manual para que gates, mensajes,
cadencias y recordatorios pasen por APIs, servicios y readiness auditada.

Nota 2026-05-29: Canales/Etapa 2 mueve la auditoria de preparacion al
servicio. `prepare_message()` crea `canales.mensaje_saliente.prepared` dentro
de la misma transaccion que persiste mensajes preparados o bloqueados,
cubriendo endpoint HTTP y llamadas internas controladas sin dejar mensajes sin
evento de preparacion.

Nota 2026-05-29: Compliance/Etapa 0 cierra edicion manual no auditada desde
admin. `PoliticaRetencionDatosAdmin` y `ExportacionSensibleAdmin` quedan como
inspeccion redactada sin alta, edicion ni borrado manual, obligando cambios de
politicas, preparacion, descarga, expiracion y revocacion de exportaciones a
pasar por API, servicios, dominio y auditoria.

Nota 2026-05-29: Compliance/Etapa 0 mueve la auditoria de preparacion y
revocacion de exportaciones sensibles al servicio. `prepare_sensitive_export()`
y `revoke_export()` persisten exportacion/estado y eventos
`compliance.exportacion_sensible.prepared` o
`compliance.exportacion_sensible.revoked` dentro de la misma transaccion,
evitando registros sensibles preparados o revocados sin auditoria dedicada.

Nota 2026-05-29: PlataformaBase/Auth cierra borrado manual de usuarios desde
admin. `LeaseManagerUserAdmin` conserva gestion operativa y metadata redactada,
pero deshabilita borrado manual para preservar actores, scopes, asignaciones y
trazabilidad de auditoria.

Nota 2026-05-29: Documentos/Etapa 5 cierra borrado manual de politica
documental desde admin. `PoliticaFirmaYNotariaAdmin` conserva configuracion
operativa, pero deshabilita borrado manual para preservar la regla que
condiciona firmas, notaria, formalizacion y cierre documental.

Nota 2026-05-29: Contabilidad/Etapa 5 cierra borrado manual de configuracion
fiscal y contable desde admin. `RegimenTributarioEmpresaAdmin`,
`ConfiguracionFiscalEmpresaAdmin`, `CuentaContableAdmin`,
`ReglaContableAdmin`, `MatrizReglasContablesAdmin` y
`PoliticaReversoContableAdmin` deshabilitan borrado manual para conservar
regimenes, configuracion fiscal, plan de cuentas, reglas, matriz, politicas de
reverso y trazabilidad de cambios; las bajas quedan por estado, versionado o
flujo auditado.

Nota 2026-05-29: CobranzaActiva/Etapa 2 cierra borrado manual operativo desde
admin. `ValorUFDiarioAdmin`, `AjusteContratoAdmin`, `PagoMensualAdmin`,
`GateCobroExternoAdmin`, `IntentoPagoWebPayAdmin`,
`GarantiaContractualAdmin`, `HistorialGarantiaAdmin`,
`RepactacionDeudaAdmin`, `CodigoCobroResidualAdmin` y
`EstadoCuentaArrendatarioAdmin` deshabilitan borrado manual; cambios y bajas
quedan bajo flujos auditados, reconstruccion, conciliacion o resolucion formal.

Nota 2026-05-29: Patrimonio/Etapa 1 cierra borrado manual estructural desde
admin. `SocioAdmin`, `EmpresaAdmin`, `ComunidadPatrimonialAdmin`,
`ParticipacionPatrimonialAdmin` y `PropiedadAdmin` deshabilitan borrado manual
para conservar owners, participaciones, vigencias, propiedades y trazabilidad;
las bajas quedan por estado, vigencia o flujo auditado.

Nota 2026-05-28: Contratos/Etapa 1 cierra borrado manual contractual desde
admin. `ArrendatarioAdmin`, `ContactoPagoArrendatarioAdmin`,
`ContratoAdmin`, `ContratoPropiedadAdmin`, `PeriodoContractualAdmin`,
`CodeudorSolidarioAdmin` y `AvisoTerminoAdmin` deshabilitan borrado manual
para conservar snapshots, vigencias, tramos, propiedades vinculadas,
codeudores, avisos y trazabilidad; las bajas quedan por estado, vigencia o
flujo auditado.

Nota 2026-05-28: Operacion/Etapa 1 cierra borrado manual de cobertura
operativa desde admin. `CuentaRecaudadoraAdmin`, `IdentidadDeEnvioAdmin`,
`MandatoOperacionAdmin` y `AsignacionCanalOperacionAdmin` deshabilitan
borrado manual para conservar cuentas, mandatos, identidades, asignaciones,
vigencias y trazabilidad; las bajas quedan por estado, vigencia o flujo
auditado.

Nota 2026-05-28: Documentos/Etapa 5 cierra superficie admin operativa.
`ExpedienteDocumentalAdmin` y `DocumentoEmitidoAdmin` dejan sus campos en solo
lectura y deshabilitan borrado manual; las altas, formalizacion, correcciones y
mutaciones documentales quedan bajo endpoints o servicios auditados. La
politica de firma/notaria conserva su superficie de configuracion operativa sin
borrado manual.

Nota 2026-05-28: Canales/Etapa 2 cierra superficie admin operativa.
`CanalMensajeriaAdmin`, `MensajeSalienteAdmin`,
`ConfiguracionNotificacionContratoAdmin` y
`NotificacionCobranzaProgramadaAdmin` dejan sus campos en solo lectura y
deshabilitan borrado manual; gates, mensajes, cadencias y recordatorios quedan
bajo APIs, servicios y readiness auditada.

Nota 2026-05-28: SII/Etapa 4 cierra superficie admin operativa.
`CapacidadTributariaSIIAdmin`, `DTEEmitidoAdmin`,
`F29PreparacionMensualAdmin`, `ProcesoRentaAnualAdmin`,
`DDJJPreparacionAnualAdmin` y `F22PreparacionAnualAdmin` dejan sus campos en
solo lectura y deshabilitan borrado manual; capacidades, DTE, F29 y renta anual
quedan bajo APIs, servicios, gates y readiness auditada.

Nota 2026-05-28: Contabilidad/Etapa 5 cierra superficie admin operativa.
`EventoContableAdmin`, `AsientoContableAdmin`, `MovimientoAsientoAdmin`,
`ObligacionTributariaMensualAdmin`, `LibroDiarioAdmin`, `LibroMayorAdmin`,
`BalanceComprobacionAdmin`, `CierreMensualContableAdmin` y
`EfectoReaperturaCierreMensualAdmin` dejan sus campos en solo lectura y
deshabilitan borrado manual; las altas, mutaciones y efectos contables quedan
en flujos de API/servicio/gate auditados.

Nota 2026-05-28: Conciliacion/Etapa 3 cierra superficie admin operativa.
`MovimientoBancarioImportadoAdmin`, `IngresoDesconocidoAdmin`,
`CuadraturaBancariaAdmin` y `TransferenciaIntercuentaAdmin` muestran sus
campos en solo lectura y deshabilitan borrado manual; `ConexionBancariaAdmin`
tambien bloquea borrado manual. Las mutaciones de importacion, match,
cuadratura y resolucion quedan en APIs o servicios auditados.

Nota 2026-05-28: CobranzaActiva/Etapa 2 cierra mutaciones genericas de
codigos residuales ya generados. `CodigoCobroResidualSerializer` conserva la
creacion con referencia `CCR-XXXXXX`, pero rechaza cambios posteriores de
referencia, arrendatario, contrato origen, saldo, estado o fecha de activacion;
`CodigoCobroResidualAdmin` muestra esos campos solo como lectura y deshabilita
borrado manual para que el cierre de deuda residual pase por flujos auditados
especificos.

Nota 2026-05-28: CobranzaActiva/Etapa 2 cierra bypass admin del estado de
cuenta. `EstadoCuentaArrendatarioAdmin` conserva visibles `resumen_operativo` y
`score_pago`, pero ambos quedan en `readonly_fields`; el estado operativo sigue
derivado exclusivamente del rebuild de pagos, repactaciones y codigos activos.

Nota 2026-05-28: Auditoria/Conciliacion cierra la superficie generica de
resoluciones manuales especializadas. El endpoint generico de
`ManualResolution` ya no puede crear categorias `conciliacion.*`
especializadas, convertir una resolucion comun a esas categorias ni retargetear
`scope_type`, `scope_reference` o `metadata`; esos casos quedan bajo los
servicios auditados de ingreso desconocido, cargo bancario y transferencia
interna.

Nota 2026-05-28: CobranzaActiva/Etapa 2 cierra edicion manual del score de
estado de cuenta. `EstadoCuentaArrendatarioSerializer` rechaza `score_pago` en
PATCH del endpoint de detalle; el valor operativo debe salir del rebuild de
estado de cuenta sobre pagos, repactaciones y codigos residuales activos.

Nota 2026-05-28: Canales/Etapa 2 agrega ruta interna controlada para
mensajes WhatsApp fallidos. `mark_whatsapp_message_as_failed()` solo acepta
mensajes preparados, exige actor trazable y motivo no sensible, cambia el
estado a `fallido` y crea `ManualResolution`
`canales.whatsapp.fallback_requerido` mas evento
`canales.whatsapp.fallback_required` alineado al motivo/contexto, para que la
readiness no dependa de mutaciones directas del estado.

Nota 2026-05-28: Conciliacion/Etapa 3 exige traza contable para transferencias
internas resueltas manualmente. Readiness valida que la resolucion manual
conserve `evento_contable_ids`, `empresa_evento_ids` y
`resolved_with=internal_transfer`, y que los `EventoContable` de salida/entrada
coincidan con `TransferenciaIntercuenta`, empresas, fechas, moneda y montos; una
traza inexistente o desalineada queda como
`stage3.manual_resolution.internal_transfer_target_mismatch`.

Nota 2026-05-28: Conciliacion/Etapa 3 exige traza contable para cargos
bancarios resueltos manualmente. Readiness valida que la resolucion manual de
`comision_bancaria` conserve `resolved_event_id`, `resolved_empresa_id` y
`resolved_with=charge_manual_classification`, y que el `EventoContable`
`ComisionBancaria` coincida con movimiento, empresa, fecha, moneda y monto; una
traza inexistente o desalineada queda como
`stage3.manual_resolution.charge_classification_target_mismatch`.

Nota 2026-05-28: Conciliacion/Etapa 3 alinea metadata de transferencias
internas manuales. Readiness compara la resolucion manual heredada contra el
registro canonico `TransferenciaIntercuenta`: par cargo/abono, entidades,
periodo economico, criterio, evidencia y responsable; cualquier desalineacion
queda como `stage3.manual_resolution.internal_transfer_target_mismatch`.

Nota 2026-05-28: Conciliacion/Etapa 3 alinea el periodo economico de cargos
bancarios manuales. El servicio de clasificacion de cargos rechaza
`periodo_economico` que no coincida con el mes del movimiento bancario, y
readiness Etapa 3 bloquea resoluciones heredadas con esa metadata desalineada
como `stage3.manual_resolution.charge_classification_target_mismatch`.

Nota 2026-05-28: SII/Etapa 4 protege observaciones tributarias. DTE, F29,
DDJJ y F22 rechazan nuevas observaciones con URLs, correos, tokens o
credenciales desde dominio y servicios; API, snapshot y admin Django redactan
observaciones heredadas, y readiness Etapa 4 reporta
`stage4.dte_sensitive_observations`, `stage4.f29_sensitive_observations`,
`stage4.ddjj_sensitive_observations` y
`stage4.f22_sensitive_observations`.

Nota 2026-05-28: Canales/Etapa 2 exige identidad autorizada en mensajes
contractuales. Mensajes preparados o enviados asociados a contrato o documento
contractual solo aceptan una `IdentidadDeEnvio` autorizada por override
explicito del contrato o asignacion activa del mandato para el mismo canal; el
servicio de preparacion, el registro manual y readiness Etapa 2 bloquean
identidades activas pero no autorizadas.

Nota 2026-05-28: Conciliacion/Etapa 3 protege notas administrativas de
movimientos bancarios. `MovimientoBancarioImportado.clean()` rechaza nuevas
`notas_admin` con URLs, correos, tokens o credenciales; API y admin Django
redactan notas heredadas, y readiness Etapa 3 reporta
`stage3.movement.sensitive_admin_notes`.

Nota 2026-05-28: CobranzaActiva/Etapa 2 protege observaciones de estados de
cuenta. `EstadoCuentaArrendatario.clean()` rechaza nuevas observaciones con
URLs, correos, tokens o credenciales; API, snapshot y admin Django redactan
observaciones heredadas, y readiness Etapa 2 reporta
`stage2.account_state.sensitive_observations`.

Nota 2026-05-28: Contratos/Etapa 1 protege causales de avisos de termino.
`AvisoTermino.clean()` rechaza nuevas causales con URLs, correos, tokens o
credenciales; API, snapshot y admin Django redactan causales heredadas, y el
auditor Etapa 1 reporta `stage1.aviso_termino.causal_sensible`.

Nota 2026-05-28: Cobranza/Etapa 1 protege justificaciones de ajustes
contractuales. `AjusteContrato.clean()` rechaza nuevas justificaciones con
URLs, correos, tokens o credenciales; API, snapshot y admin Django redactan
justificaciones heredadas, y el auditor Etapa 1 reporta
`stage1.ajuste_contrato.justificacion_sensible`.

Nota 2026-05-28: Patrimonio redacta observaciones sensibles heredadas en
representaciones de comunidad. `RepresentacionComunidad.clean()` rechaza nuevas
observaciones con URLs, correos, tokens o credenciales, la API de comunidades
redacta `representacion_vigente.observaciones` y el auditor Etapa 1 reporta
`stage1.representacion.observaciones_sensibles`.

Nota 2026-05-28: Patrimonio cierra borrado manual de representaciones y
servicios estructurados desde admin. `RepresentacionComunidadAdmin` y
`ServicioPropiedadAdmin` mantienen evidencia sensible heredada solo como
version redactada y deshabilitan borrado manual para conservar vigencias,
cobertura de gastos comunes, historial operativo y trazabilidad.

Nota 2026-05-28: Compliance cierra superficie API de politicas de retencion.
`PoliticaRetencionDatosSerializer` redacta `evento_inicio` sensible heredado en
list/detail, mientras dominio/API mantienen el rechazo de nuevas URLs, correos,
tokens, bearer, API keys o credenciales.

Nota 2026-05-28: PlataformaBase/Core clasifica claves sensibles transversales
en metadata. El detector compartido de referencias sensibles ahora trata
`authorization`, variantes de header y `private_key` como claves sensibles aun
cuando el valor sea opaco, reutiliza esa regla en senales runtime y conserva
refs operativas no sensibles como `AuthorizationRef` sin convertirlas en
secretos por nombre de valor.

Nota 2026-05-28: Canales/Admin reutiliza el detector transversal de claves
sensibles. `CanalMensajeriaAdmin` redacta `restricciones_operativas`
heredadas con claves `authorization` o `private_key` aunque sus valores sean
opacos, preservando solo claves canonicas de referencia no sensible del gate.

Nota 2026-05-28: Canales/Cobranza aplica la misma redaccion a API y snapshot
de gates operativos. `CanalMensajeria` conserva claves canonicas de referencia
no sensible como `credencial_validada_ref`, pero API/snapshot redactan claves
sensibles no autorizadas como `api_key` aunque el valor sea opaco; WebPay
expone `GateCobroExterno.restricciones_operativas` solo como payload redactado
en API y snapshot de Cobranza.

Nota 2026-05-28: Conciliacion redacta sugerencias asistidas de ingresos
desconocidos. API, snapshot y admin Django exponen
`IngresoDesconocido.sugerencia_asistida` solo mediante payload redactado, y
readiness Etapa 3 reporta `stage3.unknown_income.sensitive_suggestion` cuando
snapshots heredados conservan claves o valores sensibles en esa metadata.

Nota 2026-05-27: Gobierno ignora artefactos locales `.codex-spreadsheet/`.
Estos archivos son salida local de herramienta, no evidencia, snapshot ni
fuente de producto; deben permanecer fuera de versionado para que `main` quede
limpio y el cursor operativo sea la unica senal de paquete activo.

Nota 2026-05-27: Patrimonio cierra superficie admin de evidencias de servicios
de propiedad. `ServicioPropiedadAdmin` ya no expone ni busca `evidencia_ref`
cruda, muestra solo `evidencia_ref_redacted` y conserva la API/snapshot como
superficies redactadas para referencias heredadas.

Nota 2026-05-27: Contratos cierra superficie admin de refs WhatsApp y contacto
de pago. `ArrendatarioAdmin` y `ContactoPagoArrendatarioAdmin` reemplazan
evidencias, motivos y refs heredadas por vistas redactadas y evitan exponer los
campos crudos desde el admin Django.

Nota 2026-05-27: Cobranza/Etapa 1 protege justificaciones de historial de
garantia. `HistorialGarantia.clean()` rechaza nuevas justificaciones con URLs,
correos, tokens o credenciales; API, snapshot y admin Django redactan
justificaciones sensibles heredadas y el auditor Etapa 1 las clasifica como
`stage1.historial_garantia.validacion_modelo`.

Nota 2026-05-28: Cobranza/Etapa 1 redacta motivos sensibles de resolucion de
exceso de garantia. `GarantiaContractual.clean()` ya rechazaba nuevas
resoluciones con referencias sensibles y el auditor Etapa 1 las clasificaba
como `stage1.garantia.exceso_resolucion_sensible`; API list/detail y snapshot
ahora tambien redactan `resolucion_exceso_garantia_motivo` heredado antes de
exponerlo.

Nota 2026-05-28: CobranzaActiva redacta motivos sensibles de excepcion parcial
en repactaciones. `RepactacionDeuda.clean()` ya rechazaba nuevos motivos con
URLs, correos, tokens o credenciales; API list/detail y snapshot de Cobranza
ahora redactan `excepcion_parcial_motivo` heredado antes de exponerlo, y
readiness Etapa 2 conserva la clasificacion de esos snapshots como
`stage2.repayment.invalid_model` sin filtrar valores.

Nota 2026-05-28: Contratos valida y redacta motivos contractuales sensibles.
API list/detail, serializers de periodos/avisos y snapshot de Contratos
redactan motivos heredados de entrega de llaves, prorrata de terminacion
anticipada, politica base de renovacion y resolucion de conflicto de
renovacion. Nuevas escrituras rechazan motivos sensibles y el auditor Etapa 1
clasifica snapshots heredados con motivos sensibles mediante codigos
especificos sin exponer URLs, correos, tokens ni credenciales.

Nota 2026-05-28: Compliance respeta estados terminales de exportaciones
sensibles. `ExportacionRevokeView` ya no permite revocar exportaciones
expiradas ni revocar dos veces una exportacion sensible; si una exportacion
preparada sin hold ya vencio, se normaliza a `expirada` y se rechaza la
revocacion sin crear evento `revoked`.

Nota 2026-05-27: CobranzaActiva persiste traza UF exacta en pagos mensuales.
`PagoMensual` guarda moneda de calculo, fecha UF usada, valor UF usado y
fuente canonica; la fecha debe coincidir con `fecha_vencimiento`. La generacion
de pagos usa `ValorUFDiario` de la fecha de vencimiento, Etapa 1 audita pagos
existentes dependientes de UF contra esa traza exacta y readiness Etapa 2
bloquea trazas faltantes, desalineadas o sobrantes.

Nota 2026-05-27: Reporting completa las metricas PRD del dashboard operativo.
`build_operational_dashboard` y el backoffice muestran pagos pendientes,
movimientos sin clasificar, diferencias banco/sistema, contratos por vencer,
avisos de termino, garantias incompletas, fallas de integracion y cierres
bloqueados, respetando scope de acceso y sin usar fuentes externas.

Nota 2026-05-27: Patrimonio permite planificar representaciones
patrimoniales futuras contra participaciones futuras alineadas. La validacion
de `RepresentacionComunidad` ya no exige que el representante sea participante
vigente hoy cuando la representacion empieza en una ventana futura; exige que
exista una participacion activa solapada con la vigencia de la representacion,
y el auditor Etapa 1 acepta ese snapshot controlado.

Nota 2026-05-27: CobranzaActiva excluye del score de pago los meses sin
registro operativo. `calculate_payment_score` ignora pagos cuyo vencimiento
queda antes de `Contrato.fecha_registro_operativo`, `EstadoCuentaArrendatario`
expone `score_meses_sin_registro_operativo` en el resumen operativo y
readiness Etapa 2 detecta estados heredados que hayan contado esos meses como
evaluables.

Nota 2026-06-12: CobranzaActiva evita persistir resumenes scoped parciales de
estado de cuenta. `rebuild_account_state()` devuelve resumen filtrado cuando el
usuario tiene scope restringido, pero no crea ni sobrescribe
`EstadoCuentaArrendatario` global con datos de una sola cartera; la auditoria
del endpoint registra si el recalculo persistio resumen global o fue scoped.

Nota 2026-06-12: CobranzaActiva sincroniza estado de cuenta global derivado
despues de refrescar mora. `refresh_overdue_payments()` conserva el scope para
decidir que pagos puede mutar el actor, pero recalcula el
`EstadoCuentaArrendatario` persistido sin filtro parcial y con la misma fecha de
corte; la respuesta/auditoria registran modo `global_derived`, actor scoped y
conteos, sin exponer resumenes monetarios globales.

Nota 2026-06-06: Backoffice Cobranza opera trazabilidad de garantias
parciales y excesos. El workspace de Cobranza permite seleccionar una garantia,
actualizar `aceptacion_parcial_ref` y registrar clasificacion, referencia y
motivo de exceso contra el endpoint auditado de garantias. La tabla de
garantias muestra aceptacion parcial y resolucion de exceso con refs/motivos ya
redactados por API.

Nota 2026-06-06: Backoffice Contratos captura registro operativo retroactivo.
El formulario de Contratos permite informar `fecha_registro_operativo`, envia
la fecha solo cuando el operador la captura, conserva el default de API cuando
queda vacia, y la tabla muestra fecha y detalle de alerta manual retroactiva.

Nota 2026-05-27: Compliance exige motivo no sensible al revocar
exportaciones sensibles. `ExportacionRevokeView` rechaza revocaciones sin
motivo o con URLs, correos, tokens, bearer, claves o credenciales, guarda
`revocation_reason` en el evento `compliance.exportacion_sensible.revoked` y
readiness reporta `compliance.export_revoked_audit_reason_missing` para
snapshots heredados revocados sin motivo auditable valido.

Nota 2026-05-29: Compliance acota exportaciones sensibles por scope operativo.
`RevisorFiscalExterno` puede preparar y descargar exportaciones sensibles solo
dentro de un scope explicito asignado, `render_export_payload` recibe
`ScopeAccess`, detalle/descarga/revocacion revalidan el scope actual, los
intentos fuera de scope se rechazan con 403 y los usuarios no administradores
solo listan, descargan o revocan exportaciones creadas por ellos.

Nota 2026-05-27: Compliance separa motivos sensibles heredados en revocaciones.
`audit_compliance_data_readiness` distingue revocaciones sin motivo de
revocaciones con `revocation_reason` sensible mediante
`compliance.export_revoked_audit_reason_sensitive`, manteniendo el conteo
agregado sin exponer URLs, correos, tokens ni credenciales.

Nota 2026-05-27: Canales clasifica y redacta motivos de bloqueo sensibles en
mensajes salientes. `MensajeSaliente.clean()` rechaza nuevos `motivo_bloqueo`
con URLs, correos, tokens o credenciales; la API y snapshot redactan motivos
heredados antes de exponerlos, y readiness Etapa 2 reporta
`stage2.message.block_reason_sensitive` sin imprimir el valor.

Nota 2026-05-27: Cobranza/WebPay clasifica y redacta motivos de bloqueo
sensibles en intentos de pago. `IntentoPagoWebPay.clean()` rechaza nuevos
`motivo_bloqueo` con URLs, correos, tokens o credenciales; la API y snapshot
redactan motivos heredados antes de exponerlos, y readiness Etapa 2 reporta
`stage2.webpay_intent.sensitive_block_reason` sin imprimir el valor.

Nota 2026-06-11: Cobranza/WebPay normaliza la evidencia del gate antes de
persistir. `GateCobroExterno.clean()` y `GateCobroExternoSerializer` recortan
`evidencia_ref` para que el gate `WebPay.IntentoPago`, API, snapshot y
readiness comparen una referencia canonica no sensible sin espacios crudos.

Nota 2026-06-12: Cobranza/WebPay normaliza refs y motivos de intentos antes de
persistir. `IntentoPagoWebPay.clean()` y `save()` recortan `return_url_ref`,
`external_ref` y `motivo_bloqueo` para que API, servicio, auditoria, snapshot
y readiness comparen trazas canonicas sin espacios crudos.

Nota 2026-05-27: Contratos/Canales clasifica y redacta motivos sensibles de
bloqueo definitivo WhatsApp. `Arrendatario.clean()` y el endpoint de bloqueo
rechazan nuevos `whatsapp_bloqueo_motivo` con URLs, correos, tokens o
credenciales; la API y snapshot de Contratos redactan motivos heredados antes
de exponerlos, y readiness Etapa 2 reporta
`stage2.whatsapp.block_motive_sensitive` sin imprimir el valor.

Nota 2026-05-27: PlataformaBase recupera `core.tests_migration_pipeline`
para comunidades mixtas con empresa participante. La resolucion manual de
owners valida de forma controlada que una empresa participante activa tenga
participaciones completas antes de crear comunidad/propiedad, y las fixtures
del flujo actual representan esa estructura patrimonial antes de reimportar
contratos.

Nota 2026-05-27: PlataformaBase/Core cierra superficie admin cruda.
`ScopeAdmin`, `RoleScopeAdmin`, `UserScopeAssignmentAdmin`,
`PlatformSettingAdmin` y `OperationalRuntimeSignalAdmin` reemplazan metadata,
permission sets, valores y refs runtime por vistas redactadas, eliminan
busquedas por campos sensibles, mantienen cerrada el alta y borrado manual de
settings, y mantienen cerradas el alta, edicion y borrado manual de signals
runtime desde Django admin.

Nota 2026-05-28: PlataformaBase/RBAC cierra borrado manual destructivo desde
admin. `ScopeAdmin`, `RoleAdmin`, `RoleScopeAdmin` y
`UserScopeAssignmentAdmin` conservan gestion operativa controlada, pero
deshabilitan el borrado manual para que scopes se inactiven, asignaciones
cierren vigencia y cambios de permisos conserven trazabilidad.

Nota 2026-05-27: PlataformaBase/Auth redacta metadata de usuario expuesta.
`CurrentUserSerializer` devuelve `User.metadata` con redaccion recursiva, el
login demo conserva la firma de cache solo como hash interno y no la envia al
cliente, y `LeaseManagerUserAdmin` muestra metadata redactada sin exponer el
campo crudo ni permitir borrado manual de usuarios.

Nota 2026-05-27: Auditoria cierra superficie admin cruda. `AuditEventAdmin` y
`ManualResolutionAdmin` reemplazan identificadores, resumenes, rationales,
request ids y metadata por vistas redactadas, eliminan busquedas por campos
sensibles y mantienen cerradas alta/borrado manual desde Django admin para no
saltar los flujos auditados del backoffice.

Nota 2026-05-27: Compliance cierra superficie admin de politicas de retencion.
`PoliticaRetencionDatosAdmin` ya no expone ni busca `evento_inicio` crudo,
muestra una version redactada de politicas heredadas con URLs, tokens o
credenciales y mantiene cerrados el alta y borrado manual desde admin.

Nota 2026-05-28: Compliance cierra borrado manual de exportaciones sensibles.
`ExportacionSensibleAdmin` mantiene campos sensibles fuera del admin crudo,
muestra versiones redactadas y deshabilita alta/edicion/borrado manual para que
preparacion, descarga, expiracion y revocacion sigan pasando por API, servicios
y auditoria.

Nota 2026-05-27: Compliance valida el bootstrap demo de politicas de
retencion antes de persistir. `bootstrap_demo_compliance_policies` construye
candidatos `PoliticaRetencionDatos`, ejecuta `full_clean()` sobre todo el set
canonico y solo aplica cambios dentro de una transaccion si no hay campos
invalidos o sensibles, evitando escrituras parciales desde parametros de
bootstrap.

Nota 2026-05-27: SII cierra superficie admin para refs y payloads
tributarios sensibles heredados. Los admins de capacidades SII, DTE, F29,
ProcesoRentaAnual, DDJJ y F22 reemplazan certificados, evidencias, tracking,
borradores, paquetes, resumenes y observaciones crudas por vistas redactadas,
eliminan busquedas por campos sensibles y mantienen el alta manual cerrada
desde backoffice.

Nota 2026-05-27: SII separa la consulta de estado DTE de la emision. Los
DTE en `enviado_manual_controlado` siguen revalidando `DTEEmision`, mientras
que estados finales `aceptado`, `rechazado` o `anulado` exigen
`DTEConsultaEstado` abierta y lista; readiness Etapa 4 bloquea snapshots con
DTE finales sin esa capacidad de consulta.

Nota 2026-05-27: Canales cierra superficie admin para refs, payloads,
restricciones y motivos sensibles heredados. Los admins de gates de mensajeria,
mensajes salientes, configuraciones de notificacion y recordatorios programados
reemplazan los campos crudos por vistas redactadas, eliminan busquedas por
refs sensibles y mantienen el alta manual cerrada desde backoffice.

Nota 2026-05-27: Contabilidad cierra superficie admin para refs y payloads
sensibles heredados. Los admins de eventos contables, movimientos de asiento,
obligaciones, libros, balances, cierres y efectos de reapertura reemplazan
payloads, `storage_ref`, `centro_resultado_ref`, motivos y evidencias crudas
por vistas redactadas, eliminan busquedas por campos sensibles y cierran el
alta manual de artefactos generados.

Nota 2026-05-27: Conciliacion cierra superficie admin para referencias
bancarias sensibles heredadas. Los admins de conexiones bancarias, movimientos
importados, cuadraturas y transferencias intercuenta reemplazan refs,
responsables, criterios o motivos crudos por vistas redactadas, eliminan
busquedas por campos sensibles y mantienen el alta manual cerrada desde
backoffice.

Nota 2026-05-27: Conciliacion exige contexto no sensible en resoluciones
manuales. Los cierres de ingresos desconocidos, cargos bancarios y
transferencias internas rechazan criterios o motivos con URLs, correos, tokens
o credenciales, y readiness Etapa 3 clasifica snapshots heredados con esos
valores sin imprimirlos.

Nota 2026-05-27: CobranzaActiva cierra superficie admin para referencias y
payloads sensibles heredados. Los admins de UF manual, pagos mensuales, gates
WebPay, intentos WebPay, garantias y repactaciones reemplazan refs, motivos y
payloads crudos por vistas redactadas, eliminan busquedas por campos sensibles
y mantienen el alta y borrado manual cerrados desde backoffice.

Nota 2026-05-28: CobranzaActiva completa el cierre de alta manual para
artefactos operativos derivados. `CodigoCobroResidualAdmin` y
`EstadoCuentaArrendatarioAdmin` mantienen el alta y borrado manual
deshabilitados para que los residuales nazcan por generacion controlada y los
estados de cuenta por rebuild de pagos, repactaciones y codigos activos.

Nota 2026-05-27: Patrimonio bloquea la inactivacion de empresas y comunidades
que aun conservan participaciones o representaciones propias activas vigentes.
La salida operativa exige transferir o cerrar esa estructura antes de marcar el
owner como inactivo, y el auditor Etapa 1 detecta snapshots heredados que
conserven ownership vigente bajo owners cerrados.

Nota 2026-05-27: Operacion redacta `evidencia_operativa_ref` sensible heredada
en cuentas recaudadoras tanto en list/detail API como en snapshot operativo. La
validacion de escritura sigue rechazando nuevas evidencias sensibles y el
auditor Etapa 1 conserva la deteccion de snapshots heredados defectuosos.

Nota 2026-05-27: Contratos cierra la superficie admin de refs/motivos
contractuales. `ContratoAdmin`, `PeriodoContractualAdmin` y `AvisoTerminoAdmin`
ya no exponen los campos crudos de entrega de llaves, prorrata, politica base
de renovacion ni resolucion guiada de conflicto; muestran versiones redactadas
y mantienen el alta manual cerrada.

Nota 2026-05-26: El flujo GitHub no debe reutilizar PRs cerrados por nombre de
rama. `scripts/codex-github-package.ps1` solo considera PR existente si su
estado es `OPEN`; si `gh pr view <branch>` devuelve un PR `MERGED` o `CLOSED`,
el paquete crea un PR nuevo para que el merge afecte realmente a `main`.

Nota 2026-05-26: Canales endurece el fallback critico de WhatsApp desde
servicio. Cuando `prepare_message()` bloquea un mensaje WhatsApp, crea
`ManualResolution` `canales.whatsapp.fallback_requerido` con actor trazable y
evento `canales.whatsapp.fallback_required` alineado al motivo/contexto del
mensaje; readiness Etapa 2 ya no acepta alertas heredadas sin actor, sin evento
dedicado o con motivo desalineado como fallback suficiente.

Nota 2026-05-26: Contratos y Canales mueven la traza de bloqueo y
rehabilitacion WhatsApp a servicios. `block_whatsapp_contact()` exige actor
trazable, bloquea el contacto, crea `ManualResolution`
`canales.whatsapp.bloqueo_definitivo` y evento
`contratos.arrendatario.whatsapp_blocked` con motivo/evidencia alineados en la
misma transaccion; `rehabilitate_whatsapp_contact()` resuelve alertas y audita
la rehabilitacion. Readiness Etapa 2 exige actor y alineacion de evento/alerta.

Nota 2026-05-26: Cobranza mueve la auditoria de cargas UF manuales a la capa
de servicio. `save_uf_value()` exige actor trazable para fuentes manuales,
guarda el `ValorUFDiario` y crea el `AuditEvent`
`cobranza.valor_uf.manual_loaded` con evidencia, motivo y responsable
alineados en la misma transaccion; los campos de procedencia manual se
normalizan antes de persistir para que API, servicio, auditoria y readiness
comparen una traza canonica. API y bootstrap delegan esa responsabilidad y
readiness exige que el motivo del evento coincida con el valor UF.

Nota 2026-05-26: Cobranza mueve la auditoria de repactaciones parciales a la
capa de servicio. `save_repayment_plan()` exige actor trazable cuando el plan
cubre menos que la deuda original, guarda la repactacion y crea el `AuditEvent`
`cobranza.repactacion_deuda.partial_exception` con referencia y motivo
alineados en la misma transaccion; referencia y motivo de excepcion parcial se
normalizan antes de persistir para que API, servicio, auditoria y readiness
comparen una traza canonica. Los endpoints HTTP delegan esa responsabilidad y
readiness exige que el motivo del evento coincida con la repactacion.

Nota 2026-05-26: Cobranza mueve la auditoria de cierre excepcional de pagos a
la capa de servicio. `update_payment_operational_fields()` exige actor trazable
para estados `condonado` o `pagado_por_acuerdo_termino`, sincroniza mora y
distribucion, guarda el pago y crea el `AuditEvent`
`cobranza.pago_mensual.exceptional_state_resolved` con resolucion alineada en
la misma transaccion; el endpoint HTTP delega esa responsabilidad para no
duplicar eventos.

Nota 2026-05-26: Canales mueve la auditoria de envio manual a la capa de
servicio. `mark_message_as_sent()` exige actor trazable, marca el mensaje como
`enviado` y crea el `AuditEvent`
`canales.mensaje_saliente.sent_manually` con `external_ref` alineado en la
misma transaccion; el endpoint HTTP delega esa responsabilidad para no duplicar
eventos.

Nota 2026-05-26: WebPay mueve la auditoria de confirmacion manual a la capa de
servicio. `confirm_webpay_intent_manually()` exige actor trazable, revalida el
gate, marca el intento y el pago en una transaccion y crea el `AuditEvent`
`cobranza.webpay_intento.confirmed_manually` con `external_ref`,
`pago_mensual_id` y `fecha_pago_webpay` alineados; el endpoint HTTP delega esa
responsabilidad para no duplicar eventos.

Nota 2026-05-26: Contratos reserva `renovacion_automatica` para el flujo
guiado con auditoria. `PeriodoContractual.full_clean()` exige el `AuditEvent`
dedicado para tramos con ese origen, el servicio de renovacion conserva la
excepcion interna para crear tramo y evento en la misma operacion, y la API de
contratos rechaza payloads anidados que intenten marcar un tramo como
automatico sin pasar por el endpoint.

Nota 2026-05-26: Contratos mueve la auditoria de prorrata por terminacion
anticipada parcial a guard de dominio. `Contrato.full_clean()` exige que un
contrato terminado anticipadamente con ultimo mes parcial y decision de
prorrata conserve el `AuditEvent` dedicado; la API mantiene el flujo guiado que
crea esa traza despues de guardar y el auditor Etapa 1 conserva la deteccion de
snapshots heredados.

Nota 2026-05-26: SII endurece payloads tributarios locales sin conectar SII ni
leer certificados. `ultimo_resultado`, `resumen_formulario`, `resumen_anual`,
`resumen_paquete` y `resumen_f22` rechazan valores y claves sensibles como
`api_key`, `access_token` o `credential`; readiness Etapa 4 detecta payloads
heredados sensibles sin imprimirlos y mantiene el cierre condicionado a fuente
autorizada.

Nota 2026-05-26: Renta Anual y Reporting clasifican explicitamente payloads
anuales sensibles heredados. Los readiness de Etapa 6 y Etapa 7 reportan
`resumen_anual`, `resumen_paquete` y `resumen_f22` con URLs, tokens,
credenciales, correos o claves sensibles como brecha bloqueante sin imprimir
valores, manteniendo el cierre condicionado a fuente autorizada.

Nota 2026-05-26: Compliance datos sensibles exige trazabilidad de revocacion.
Las exportaciones sensibles en estado `revocada` deben conservar evento
`compliance.exportacion_sensible.revoked`; readiness bloquea snapshots heredados
sin esa auditoria y el endpoint de revocacion mantiene el evento dedicado.

Nota 2026-05-26: Compliance datos sensibles exige actor trazable en auditoria
de exportaciones sensibles. Readiness reporta eventos `prepared`, `accessed`,
`access_denied` o `revoked` sin `actor_user` como brecha bloqueante mediante
conteos/codigos, sin exponer payloads ni metadata sensible.

Nota 2026-05-26: Compliance datos sensibles exige target auditable valido. Los
eventos `prepared`, `accessed`, `access_denied` o `revoked` deben apuntar a
`entity_type=exportacion_sensible` y `entity_id` de una exportacion existente;
readiness reporta eventos huerfanos o mal vinculados sin exponer ids.

Nota 2026-05-26: Compliance datos sensibles alinea la auditoria de
exportaciones sensibles con la exportacion real. Los eventos `prepared`,
`accessed`, `access_denied` y `revoked` conservan metadata no sensible de
categoria, tipo de exportacion, scope, hash, estado, hold, expiracion y creador;
readiness reporta `compliance.export_prepared_audit_event_unaligned`,
`compliance.export_revoked_audit_event_unaligned` y
`compliance.audit_metadata_unaligned` para eventos heredados incompletos o
desalineados.

Nota 2026-05-26: Compliance datos sensibles clasifica referencias sensibles en
fuente y evidencia final. `audit_compliance_data_readiness` distingue refs
faltantes de refs con URLs, tokens, correos o credenciales para
`SourceLabel`, `AuthorizationRef`, politica aprobada, responsables, controles,
evidencia archivada y validacion legal-operativa, sin imprimir valores.

Nota 2026-05-26: El login publico deja de renderizar mensajes internos de
error. La superficie anonima usa `publicSafeApiErrorMessage()` para permitir
solo detalles HTTP acotados y no sensibles, y reemplaza nombres de variables o
configuracion por estados publicos genericos.

Nota 2026-05-26: Documentos ajusta la firma de codeudor al alcance real del
contrato. `DocumentoEmitido.validate_formalization()` exige
`firma_codeudor_registrada` cuando la politica lo pide y el expediente apunta a
un contrato con `CodeudorSolidario` activo; contratos sin codeudor activo no se
bloquean solo por el flag de politica. Readiness reporta
`documents.codebtor_signature_missing` para formalizados heredados que incumplan
esa condicion.

Nota 2026-05-26: Patrimonio mueve la identidad unica de propiedades activas a
guard de escritura. `Propiedad.full_clean()` y la API rechazan nuevas
propiedades activas con ROL de avaluo normalizado duplicado o identidad
operativa duplicada; `audit_stage1_matrix` mantiene la deteccion de snapshots
heredados.

Nota 2026-05-26: Contratos mueve la regla de gastos comunes estructurados a
guard de escritura. Contratos vigentes/futuros con `tiene_gastos_comunes=True`
requieren un `ServicioPropiedad` activo de tipo gasto comun en la propiedad
principal desde `Contrato.full_clean()` y API; el auditor Etapa 1 conserva la
deteccion de snapshots heredados.

Nota 2026-05-26: Contratos mueve la cobertura minima de canal operativo a
guard de escritura. Contratos vigentes/futuros requieren al menos una
`AsignacionCanalOperacion` activa con `IdentidadDeEnvio` activa en su mandato
desde `Contrato.full_clean()` y API; el auditor Etapa 1 conserva la deteccion
de snapshots heredados.

Nota 2026-05-26: Contratos mueve el readiness operativo de arrendatario a
guard de escritura. Contratos vigentes/futuros requieren arrendatario con
estado de contacto activo, email o telefono, domicilio de notificaciones y
contacto de pago activo estructurado desde `Contrato.full_clean()` y API; el
auditor Etapa 1 conserva la deteccion de snapshots heredados.

Nota 2026-05-26: Contratos mueve el respaldo de cierre para contratos futuros
a guard de dominio. `Contrato.full_clean()` valida que un contrato futuro
tenga AvisoTermino registrado sobre el contrato vigente de la propiedad
principal, terminacion anticipada ejecutada o resolucion guiada no sensible si
existe conflicto con renovacion ya ejecutada; API y auditor Etapa 1 conservan
la misma regla para escrituras y snapshots heredados.

Nota 2026-05-26: Contratos mueve el cambio de arrendatario futuro a guard de
escritura. `Contrato.full_clean()` y API rechazan contratos futuros con
arrendatario distinto al vigente si no provienen del flujo guiado de cambio de
arrendatario o no conservan el `AuditEvent` exacto que vincula contrato
anterior, aviso y contrato nuevo; el servicio guiado conserva la excepcion
interna necesaria para crear el contrato y su auditoria en la misma
transaccion, y el auditor Etapa 1 mantiene la deteccion de snapshots heredados.

Nota 2026-05-26: Contratos mueve la entrega de llaves a guard de dominio.
`Contrato.full_clean()` y API rechazan crear o actualizar contratos con
`fecha_entrega` operativa si no existe garantia cubierta o autorizacion
auditada con referencia no sensible y motivo trazable; el auditor Etapa 1
mantiene la deteccion de snapshots heredados sin garantia suficiente ni
autorizacion.

Nota 2026-05-26: CobranzaActiva y Canales endurecen los gates externos sin
abrir integraciones. `restricciones_operativas` de Email/WhatsApp/WebPay
rechaza valores sensibles y tambien nombres de claves sensibles como
`api_key`, `access_token` o `credential`; las claves canonicas de referencia
no sensible, como `credencial_validada_ref`, siguen permitidas cuando su valor
es trazable y no sensible. Readiness Etapa 2 bloquea snapshots heredados con
estas claves sensibles sin imprimir sus valores.

Nota 2026-05-26: CobranzaActiva refuerza que `CodigoCobroResidual` es
post-contrato. `fecha_activacion` debe ser posterior a
`Contrato.fecha_fin_vigente`; dominio/API rechazan nuevas escrituras durante la
vigencia y readiness Etapa 2 reporta `stage2.residual_code.invalid_model` para
snapshots heredados con codigos residuales prematuros.

Nota 2026-05-26: CobranzaActiva exige coherencia saldo/estado en
`CodigoCobroResidual`. Un codigo `activa` mantiene saldo pendiente mayor que
cero; `pagada` o `cancelada` deben quedar con `saldo_actual=0`, y readiness
Etapa 2 bloquea snapshots heredados que oculten saldo bajo estados cerrados.

Nota 2026-05-26: Conciliacion restringe el match exacto automatico de cobranza
residual a la cuenta recaudadora del movimiento bancario. Una referencia
`CCR-XXXXXX` valida pero asociada a otra cuenta queda como ingreso desconocido
para resolucion manual auditada; readiness Etapa 3 sigue bloqueando snapshots
heredados con targets residuales de cuenta incorrecta.

Nota 2026-05-26: CobranzaActiva canoniza la procedencia de `ValorUFDiario`.
`source_key` solo acepta `UF.BancoCentral`, `UF.CMF`, `UF.MiIndicador` o
`UF.CargaManualExtraordinaria`; el bootstrap demo exige `--source-key`
explicito, el backoffice usa selector cerrado y readiness Etapa 2 reporta
`stage2.uf_value.source_not_canonical` para fuentes heredadas libres.

Nota 2026-05-26: CobranzaActiva persiste el efecto economico del codigo
efectivo en `PagoMensual.monto_efecto_codigo_efectivo_clp`, lo valida como
`monto_calculado_clp - monto_facturable_clp`, registra auditoria
`cobranza.pago_mensual.effective_code_applied` cuando el efecto no es cero y
readiness Etapa 2 reporta `stage2.payment.effective_code_effect_mismatch` o
`stage2.payment.effective_code_event_missing`.

Nota 2026-05-26: CobranzaActiva exige resolucion trazable para pagos mensuales
cerrados como `pagado_por_acuerdo_termino` o `condonado`. El dominio/API
requieren referencia no sensible y motivo, registran auditoria
`cobranza.pago_mensual.exceptional_state_resolved`, el snapshot/backoffice
exponen la resolucion redactada y readiness Etapa 2 reporta
`stage2.payment.exceptional_resolution_missing` o
`stage2.payment.exceptional_resolution_event_missing` para datos heredados.

Nota 2026-05-26: Patrimonio exige evidencia formal no sensible cuando una
comunidad usa representacion `designado`. `RepresentacionComunidad` conserva
`evidencia_ref`, API/snapshot/backoffice la exponen con redaccion de valores
sensibles y el auditor Etapa 1 reporta
`stage1.representacion.designada_evidencia_faltante` o
`stage1.representacion.designada_evidencia_sensible` para snapshots heredados.

Nota 2026-05-26: Contabilidad evita doble contabilizacion efectiva del mismo
hecho economico. Si ya existe un `EventoContable` `contabilizado` para la misma
empresa, tipo y entidad origen, un evento nuevo con otra `idempotency_key` queda
en `pendiente_revision_contable`; `EventoContable.full_clean` rechaza
duplicados posteados y readiness Etapa 5 reporta `stage5.duplicate_posted_events`
para snapshots heredados.

Nota 2026-06-12: Contabilidad normaliza refs/textos operativos antes de
`full_clean` y persistencia. `MovimientoAsiento`, snapshots ledger,
`LiquidacionMensual`, `LineaLiquidacionMensual` y efectos de reapertura limpian
espacios de refs, evidencias, motivos y descripciones antes de validadores de
campo, `save()`, snapshot/backoffice, readiness y auditoria, evitando valores
canonicos rechazados por longitud cruda o persistidos con espacios.

Nota 2026-05-25: Documentos incorpora emision local de PDF generado por sistema
mediante endpoint dedicado. El PDF canonico se renderiza sin dependencia
externa, el checksum SHA-256 y `storage_ref` derivan del contenido, se rechaza
contenido sensible, el endpoint generico rechaza `origen=generado_sistema` y
readiness bloquea documentos `generado_sistema` sin auditoria
`documentos.documento_emitido.generated_pdf`.

Nota 2026-05-26: Documentos incorpora vista previa auditada para PDF generado.
`documentos-emitidos/previsualizar-pdf/` deriva checksum/storage sin persistir
documento y registra `documentos.documento_emitido.previewed_pdf`; la emision
generada exige una preview auditada del mismo contenido y readiness reporta
`documents.generated_pdf_preview_missing` para snapshots heredados.

Nota 2026-05-26: Documentos alinea la auditoria de PDF generado y preview con
el contenido emitido. Los eventos `documentos.documento_emitido.generated_pdf`
y `documentos.documento_emitido.previewed_pdf` conservan actor y metadata de
checksum, `storage_ref`, version, tipo documental y expediente; readiness
reporta `documents.generated_pdf_audit_unaligned` y
`documents.generated_pdf_preview_unaligned` para eventos heredados incompletos
o desalineados.

Nota 2026-05-26: Documentos exige `evidencia_formalizacion_ref` no sensible al
formalizar documentos. API/modelo rechazan formalizaciones sin referencia o con
referencia sensible, list/detail/snapshot/backoffice redactan evidencia
heredada sensible y `audit_document_readiness` reporta
`documents.formalization_evidence_missing` o
`documents.formalization_evidence_sensitive` para snapshots heredados.

Nota 2026-05-26: Documentos alinea la auditoria de formalizacion con el acto
formalizado. El endpoint `formalizar/` registra actor y metadata no sensible de
evidencia, firmas, recepcion y comprobante notarial; readiness reporta
`documents.formalization_audit_unaligned` cuando un snapshot conserva evento
sin actor o metadata desalineada.

Nota 2026-05-26: Documentos alinea tambien la auditoria de versiones
correctivas. El evento `documentos.documento_emitido.corrective_version_created`
conserva actor y metadata de origen, expediente, tipo, version, checksum,
`storage_ref` y `correccion_ref`; readiness reporta
`documents.corrective_version_audit_unaligned` para snapshots heredados con
evento incompleto o desalineado.

Nota 2026-05-26: Documentos separa en readiness las brechas notariales
heredadas. `audit_document_readiness` reporta documentos formalizados con
politica notarial sin recepcion, sin comprobante, con comprobante de tipo
incorrecto, de otro expediente o en estado no permitido, sin exponer valores
sensibles ni leer storage real.

Nota 2026-05-25: Patrimonio incorpora flujo operacional de transferencia o
redistribucion de participaciones. El endpoint cierra la participacion origen,
crea destinos desde la fecha efectiva, conserva el 100% del owner, exige motivo
y evidencia no sensible, y registra auditoria
`patrimonio.participacion.transfer_executed`. El auditor Etapa 1 bloquea
sucesiones heredadas con sucesor inmediato sin evento auditable.

Nota 2026-05-26: El auditor Etapa 1 ya no acepta cualquier evento de
transferencia patrimonial como evidencia suficiente. Para sucesiones inmediatas
exige actor y metadata alineada a owner, participacion origen, participante
origen, fecha efectiva, destinos, porcentaje transferido, motivo y evidencia no
sensible; reporta `stage1.participacion.transferencia_auditoria_desalineada`
cuando un snapshot conserva auditoria incompleta, reciclada o sensible.

Nota 2026-05-27: Patrimonio rechaza motivos sensibles en transferencias de
participaciones. El endpoint `participaciones/transferir/` no permite motivos
con URLs, correos, tokens o credenciales, y el auditor Etapa 1 clasifica
auditorias heredadas con `stage1.participacion.transferencia_motivo_sensible`.

Nota 2026-05-26: Patrimonio cierra la ruta de reescritura directa de
participaciones en empresas/comunidades existentes. Los serializers rechazan
`participaciones` en updates genericos para no borrar/recrear historia con
`bulk_create`; la creacion inicial sigue permitida y los cambios posteriores
deben pasar por `participaciones/transferir/`, que conserva auditoria.

Nota 2026-05-25: Conciliacion bloquea snapshots heredados donde un abono
parcial o complementario queda `conciliado_exacto` contra un `PagoMensual` sin
resolucion manual auditada. Los pagos parciales o en varios abonos siguen
permitidos solo por resolucion manual trazable de ingreso desconocido.

Nota 2026-05-25: Conciliacion acota el match exacto automatico de pagos al
periodo economico del movimiento bancario. Un abono de otro mes ya no cierra
automaticamente un `PagoMensual` aunque coincidan cuenta y monto; queda como
ingreso desconocido/manual. Readiness Etapa 3 bloquea snapshots heredados con
movimientos conciliados exactos apuntando a pagos de otro periodo.

Nota 2026-05-25: CobranzaActiva calcula y persiste `score_pago` al recalcular
`EstadoCuentaArrendatario`, expone porcentaje, meses evaluados, pagos en plazo
y pagos fuera de plazo en `resumen_operativo`, y readiness Etapa 2 reporta
`stage2.account_state.missing_score` o `stage2.account_state.stale_score` para
snapshots heredados sin score trazable o desalineado con pagos operativos.

Nota 2026-05-24: CobranzaActiva/Canales incorpora guard local para que
WhatsApp solo opere con telefonos en formato internacional. El modelo rechaza
opt-in nuevo con numero local o ambiguo, Canales bloquea preparacion/envio con
datos heredados invalidos y readiness Etapa 2 reporta `stage2.whatsapp.phone_invalid`.

Nota 2026-05-27: Etapa 1 explicita la misma brecha en su auditor de matriz. Un
contrato vigente o futuro cuyo arrendatario tenga opt-in WhatsApp con telefono
local o ambiguo queda clasificado con
`stage1.arrendatario.whatsapp_telefono_invalido`, sin depender solo de la
validacion generica del modelo.

Nota 2026-05-24: Canales registra traza explicita de fallback cuando WhatsApp
queda bloqueado, y readiness Etapa 2 reporta
`stage2.whatsapp.fallback_trace_missing` para mensajes heredados bloqueados o
fallidos sin Email alternativo ni alerta critica trazable.

Nota 2026-05-24: Contratos agrega bloqueo definitivo y rehabilitacion manual
de WhatsApp con motivo, evidencia no sensible, fecha, evento auditable y alerta
administrativa. Readiness Etapa 2 reporta bloqueos heredados sin traza, evento
o alerta, y referencias sensibles de bloqueo/rehabilitacion.

Nota 2026-05-24: Canales incorpora cadencias de notificacion por contrato y
canal habilitado. La API normaliza dias, exige canal activo del mandato,
redacta evidencia sensible heredada y readiness Etapa 2 reporta contratos
vigentes/futuros con canal habilitado sin cadencia activa o configuraciones
invalidas.

Nota 2026-05-24: Contratos incorpora `ContactoPagoArrendatario` como dato
estructurado para cobranza. La API valida contactos activos con nombre y
email/telefono, redacta evidencia sensible heredada, el snapshot expone la
lista estructurada y, desde el guard de escritura 2026-05-26, contratos
vigentes/futuros quedan bloqueados por API/modelo si el arrendatario no tiene
contacto de pago activo.

Nota 2026-05-24: Patrimonio incorpora `ServicioPropiedad` para servicios y
gastos comunes estructurados. La API valida proveedor/administracion, numero de
cliente y evidencia no sensible, el snapshot redacta evidencia heredada y el
auditor Etapa 1 bloquea contratos con gastos comunes sin gasto comun activo en
la propiedad principal.

Nota 2026-05-24: Contratos referencia `PoliticaFirmaYNotaria` para politica
documental contractual. Contratos vigentes/futuros exigen politica activa de
tipo `contrato_principal`, el snapshot la expone y el auditor Etapa 1 bloquea
politicas faltantes, inactivas o de tipo documental incorrecto.

Nota 2026-05-24: Politica documental de contrato principal puede exigir perfil
documental del arrendatario persona natural. `Arrendatario` conserva
nacionalidad, estado civil y profesion, la API bloquea contratos vigentes o
futuros cuando la politica lo exige y faltan esos datos, y `audit_stage1_matrix`
detecta snapshots heredados incompletos.

Nota 2026-05-24: Compliance mueve reglas de retencion desde solo readiness a
dominio/API. `PoliticaRetencionDatos` rechaza eventos de inicio sensibles,
plazos minimos cero, falta de hold para tributario/documental y purga fisica
para documental/secreto; `audit_compliance_data_readiness` conserva la deteccion
de politicas heredadas invalidas sin exponer valores sensibles.

Nota 2026-05-24: Compliance bloquea nuevas exportaciones operativas sobre
categoria `secreto` desde dominio y servicio de preparacion. Readiness mantiene
la deteccion de exportaciones heredadas de secreto como brecha bloqueante sin
exponer payloads ni referencias.

Nota 2026-05-24: Compliance trata `expirada` como estado terminal de
exportacion sensible y exige coherencia con vencimiento cumplido y sin hold
activo. Readiness reporta exportaciones heredadas con estado expirado
inconsistente sin exponer payloads.

Nota 2026-05-24: Compliance registra evento auditable
`compliance.exportacion_sensible.access_denied` cuando se intenta descargar una
exportacion sensible revocada o expirada. Readiness cuenta esos eventos sin
exponer payloads ni metadata sensible.

Nota 2026-05-25: Compliance verifica la integridad de exportaciones sensibles
tambien al descargar. Si el payload cifrado ya no coincide con `payload_hash`,
la descarga se niega, queda auditoria de acceso denegado y readiness reporta
`compliance.export_payload_hash_mismatch` para snapshots heredados.

Nota 2026-05-25: Compliance trata payloads cifrados no descifrables como
acceso denegado controlado. La API no expone error interno, registra auditoria
y readiness reporta `compliance.export_payload_unreadable` para datos heredados
corruptos o no verificables.

Nota 2026-05-25: Contratos registra avisos de termino fuera de plazo sin
inventar fechas, compara el timestamp real de registro contra las `23:59:59`
del ultimo dia permitido y expone/audita la situacion como advertencia
`stage1.aviso_termino.registro_fuera_plazo`, sin convertirla en bloqueo por si
sola.

Nota 2026-05-25: Contratos/garantias permite representar garantias recibidas
por sobre lo pactado solo si el exceso queda clasificado, devuelto,
regularizado o bloqueado con referencia no sensible y motivo auditable. API,
snapshot, backoffice y auditor Etapa 1 reportan `stage1.garantia.exceso_sin_resolucion`
para snapshots heredados sin esa traza.

Nota 2026-05-25: Contratos registra autorizacion auditada para entrega de
llaves cuando la garantia exigida aun no esta cubierta. La API protege
actualizaciones de `fecha_entrega`, redacta referencias sensibles, el
backoffice expone la traza y el auditor Etapa 1 reporta entregas heredadas sin
garantia suficiente ni autorizacion no sensible.

Nota 2026-05-25: Contratos/garantias exige que devoluciones, retenciones o
aplicaciones de garantia apunten al deposito origen, no usen movimientos
derivados como origen y no superen el monto del deposito trazado. La API valida
la regla antes de persistir y el auditor Etapa 1 clasifica snapshots heredados
sin esa traza como defectuosos.

Nota 2026-05-25: Contratos exige que una renovacion de contrato con tramos use
como base el ultimo tramo vigente. Si cambia monto o moneda, el periodo debe
tener referencia no sensible y motivo trazable de politica documentada; API y
auditor Etapa 1 bloquean renovaciones heredadas sin esa traza.

Nota 2026-05-25: Contratos incorpora renovacion automatica operacional. El
endpoint crea el tramo `renovacion_automatica`, extiende `fecha_fin_vigente`,
bloquea `AvisoTermino` registrado, conserva la regla de politica cuando cambia
base y registra auditoria dedicada; el auditor Etapa 1 bloquea renovaciones
automaticas heredadas sin ese evento.

Nota 2026-05-25: Contratos incorpora flujo operacional de cambio de
arrendatario. El endpoint crea `AvisoTermino` registrado y contrato futuro con
nuevo arrendatario en una transaccion, conserva contrato/deuda historica sin
reescritura, copia propiedades contractuales, crea periodo inicial de origen
`cambio_arrendatario` y registra evento auditable; `Contrato.full_clean()` y
API bloquean escrituras directas de futuros con arrendatario distinto que no
usen ese flujo o no conserven esa traza, y el auditor Etapa 1 bloquea futuros
heredados con arrendatario distinto si falta esa traza.

Nota 2026-05-27: Documentos endurece metadata de auditoria documental. Los
builders de auditoria de PDF generado, preview PDF, formalizacion y version
correctiva redactan defensivamente referencias sensibles, y readiness Etapa 5
clasifica eventos heredados con metadata sensible mediante codigos especificos
sin exponer `storage_ref`, evidencia de formalizacion ni referencias de
correccion.

Nota 2026-05-29: Contabilidad/Etapa 5 incorpora liquidaciones mensuales
trazables. Un cierre mensual aprobado debe tener `LiquidacionMensual` de
empresa preparada/aprobada para el mismo periodo y cierre; si aplica comision
de administracion, exige `LineaLiquidacionMensual` explicita con beneficiario,
monto positivo, evidencia no sensible y traza a `EventoContable`. Readiness
bloquea cierres sin liquidacion, liquidaciones o lineas invalidas, comisiones
sin linea, lineas economicas sin traza contable y refs/explicaciones sensibles
sin exponer valores.

Nota 2026-05-31: Documentos/Etapa 5 refuerza el guard de plantillas a nivel
dominio. `DocumentoEmitido.clean()` exige `PlantillaDocumental` activa para el
mismo tipo documental y version, de modo que escrituras internas o servicios que
llamen `full_clean()` no puedan saltarse el control ya existente en API y
readiness.

Nota 2026-06-02: Compliance/Etapa 0 trata el estado auditado de
exportaciones sensibles como dato historico del evento. Readiness sigue
detectando metadata desalineada, actores faltantes y targets invalidos, pero
ya no marca como falso bloqueo un `accessed` valido en estado `preparada`
cuando la exportacion pasa despues a `revocada` o `expirada`; `access_denied`
conserva el estado observado al negar el acceso.

Nota 2026-06-06: Compliance/Etapa 0 alinea backoffice con el contrato de
revocacion sensible. La UI muestra motivo y scope visible ya redactados,
exige motivo no sensible antes de habilitar `Revocar` y envia ese motivo a la
API para que la revocacion persista `revocation_reason` en auditoria.

Nota 2026-06-12: Conciliacion/Etapa 3 normaliza referencias de movimientos
bancarios antes de persistir. `MovimientoBancarioImportado.clean()` y `save()`
recortan `evidencia_importacion_ref`, `referencia`, `transaction_id_banco` y
`notas_admin`, de modo que API, snapshot, readiness y constraint de unicidad
por conexion comparen referencias canonicas sin espacios crudos.

Nota 2026-06-12: Conciliacion/Etapa 3 normaliza referencias de conexiones
bancarias antes de persistir. `ConexionBancaria.clean()` y `save()` recortan
`provider_key`, `scope`, `credencial_ref`, `evidencia_gate_ref`,
`prueba_conectividad_ref`, `prueba_movimientos_ref` y `prueba_saldos_ref`,
para que API, snapshot, readiness y unicidad por proveedor trabajen con valores
canonicos.

Nota 2026-06-12: Conciliacion/Etapa 3 normaliza cuadraturas bancarias antes
de persistir. `CuadraturaBancaria.clean()` y `save()` recortan
`periodo_economico`, `evidencia_cuadratura_ref`, `responsable_ref` y
`rationale`, manteniendo canonicas las refs y motivos que readiness y
Contabilidad usan para cuadrar banco/sistema por cuenta y periodo.

Nota 2026-06-12: Conciliacion/Etapa 3 normaliza transferencias intercuenta
antes de persistir. `TransferenciaIntercuenta.full_clean()`, `clean()` y
`save()` recortan `periodo_economico`, `criterio_conciliacion`,
`evidencia_transferencia_ref`, `responsable_ref` y `rationale`, evitando que
modelo, snapshot, readiness, auditoria y Contabilidad comparen contexto de
transferencia con espacios crudos.

Nota 2026-06-12: Conciliacion/Etapa 3 alinea normalizacion previa a
`full_clean` en conexiones, movimientos y cuadraturas bancarias.
`ConexionBancaria.full_clean()`, `MovimientoBancarioImportado.full_clean()` y
`CuadraturaBancaria.full_clean()` recortan refs/motivos antes de los
validadores de campo de Django, evitando rechazos por espacios crudos antes de
canonizar y manteniendo consistente el camino modelo/API/readiness.

Nota 2026-06-12: Documentos/Etapa 5 normaliza referencias y textos operativos
antes de `full_clean` y persistencia. `ExpedienteDocumental`,
`PlantillaDocumental` y `DocumentoEmitido` recortan entidad, owner, version,
refs de plantilla, checksums, `storage_ref`, evidencia de formalizacion y refs
de correccion antes de validadores de campo, snapshot/backoffice, readiness y
auditoria, evitando valores canonicos rechazados por longitud cruda o
persistidos con espacios.

Nota 2026-06-13: Documentos/Etapa 5 canoniza checksums documentales como
digest SHA-256 lowercase de 64 caracteres sin prefijo `sha256:`. Modelo/API
normalizan mayusculas y espacios antes de persistir, rechazan prefijos o
etiquetas libres, y readiness bloquea documentos o plantillas activas heredadas
con checksums no canonicos mediante `documents.invalid_checksum` y
`documents.active_template_invalid`.

Nota 2026-06-14: Renta Anual/Etapa 6 enlaza bienes raices a fuente de
contribuciones revisable. `AnnualRealEstateSection` conserva
`official_contribution_source` hacia `AnnualTaxOfficialSource` SII/experta de
contribuciones o F22/Dossier, y `AnnualRealEstateItem` carga montos solo desde
`AnnualTaxSourceBundle.resumen_fuentes.real_estate_contribuciones.values_by_property_id`.
Si falta fuente o valor por propiedad, el item queda con warning
`contribuciones_source_not_loaded_v1` o `contribuciones_value_not_loaded_v1`, y
readiness bloquea el cierre sin convertir la seccion inmobiliaria en calculo
fiscal final.

Nota 2026-06-15: La carpeta consolidada `EDIG/` se inventario completa como
referencia funcional no normativa y queda ignorada por Git. La evidencia local
confirma tres lineas separadas: Contabilidad produce libros, F29, balance de
ocho columnas y DJ1847; Remuneraciones produce liquidaciones, Previred, LRE,
DJ1887, certificados y centralizacion contable; Renta transforma esas fuentes
en RLI/CPT/RAI/SAC/DDJJ/F22 mediante una capa anual intermedia. Esto refuerza
que Etapa 6 debe aceptar fuente laboral/previsional revisable cuando aplique,
pero no habilita payroll completo, copia de EDIG, reglas fiscales propias ni
presentacion SII automatica.

Nota 2026-06-16: Renta Anual/Etapa 6 agrega `real_estate` al paquete
controlado AC/AT. El writer valida fuente revisada, propiedades, evidencia no
sensible y contribuciones; materializa `Propiedad` y una
`AnnualTaxOfficialSource` experta/controlada por ano tributario. El mirror anual
usa esa fuente para generar `AnnualRealEstateItem` con snapshot congelado y
contribuciones cargadas, sin SII real, EDIG, `.env`, outputs finales como input
ni calculo tributario final. En la corrida AC2024/AT2025 con SQLite local
ignorada, el gate Etapa 6 pasa de `stage6.real_estate_item_missing` a
`classification=resuelto_confirmado`, `ready_for_stage6_renta_anual=true` y
sin issues.

Nota 2026-06-15: Renta Anual/Etapa 6 agrega writer DB local controlado para la
prueba espejo Inmobiliaria Puig AC2024/AT2025. `apply_annual_tax_controlled_db_load`
acepta solo un paquete JSON normalizado, opera en dry-run salvo `--apply`,
materializa cierres, libros, balance, obligaciones, F29 y MonthlyTaxFact, y
rechaza Balance/RLI/CPT/RAI/DDJJ/F22 finales como insumos. La arquitectura aun
no queda completa de punta a punta: faltan paquete normalizado desde fuentes
AC2024, capa anual y comparacion contra outputs esperados.

Nota 2026-06-15: Renta Anual/Etapa 6 agrega `ownership` al paquete controlado
AC/AT. El writer valida fuente patrimonial no sensible, fecha `as_of`, socios
con RUT valido, vigencias y porcentajes que suman 100.00%, y materializa
`Socio` + `ParticipacionPatrimonial` en DB local/controlada. El mirror anual
usa esas participaciones para registros RETIROS/DIVIDENDOS y elimina
`participation_source_missing` cuando la fuente existe. Para Inmobiliaria Puig
AC2024 real sigue pendiente localizar o cargar esa fuente societaria
independiente; no se infiere desde cuentas de retiro ni desde F22/DDJJ finales.

Nota 2026-06-15: `build_annual_tax_source_manifest` agrega
`ownership_source_input` como insumo requerido para la prueba espejo anual. El
manifiesto real AC2024/AT2025 confirma RCV 12/12, F29 controlado 12/12, DDJJ,
F22, libros anuales y registros tributarios esperados completos, pero mantiene
`ready_for_mirror_source_bundle=false` porque `ownership_source_present=false`.
Esta regla adelanta el bloqueo al inventario de fuentes y evita iniciar una
prueba anual completa sin fuente societaria independiente.

Nota 2026-06-15: el manifiesto AC2024/AT2025 ahora distingue fuente societaria
controlada de candidatos legales. Escrituras, extractos, inscripciones o Diario
Oficial en contexto societario quedan como `ownership_source_candidate`
soporte/revision, no como input de calculo. La corrida real encuentra 15
candidatos (`ownership_source_candidate_present=true`) y mantiene
`ownership_source_present=false`, por lo que la prueba anual sigue bloqueada
hasta convertir una fuente suficiente en snapshot controlado de socios y
participaciones vigentes. Las escrituras de propiedades no se clasifican como
ownership societario.

Nota 2026-06-15: `review_annual_tax_ownership_candidates` revisa esos
candidatos sin texto bruto, RUTs ni nombres en el JSON. La corrida real
AC2024/AT2025 confirma que los PDFs no entregan capa de texto util por
`pdftotext`; quedan 10 documentos legales como
`manual_review_required_legal_candidate`, 3 documentos nulos/sin efecto
excluidos y 2 aportes/propiedades como soporte. Esto permite avanzar a OCR o
revision manual controlada para preparar el snapshot, pero no cierra
`ownership_source_input` ni genera socios/porcentajes automaticamente.

Nota 2026-06-15: `build_annual_tax_ownership_snapshot_template` convierte esa
revision en un template seguro para completar `ownership` despues de OCR o
revision manual. La corrida real genera 10 fuentes candidatas, deja
`participants=[]`, `ready_for_controlled_db_load=false` y
`can_patch_controlled_db_load_package_after_manual_completion=true`. El template
calza con el writer anual, pero exige completar socios, RUTs, porcentajes,
vigencias y evidencia no sensible antes de cargar DB o ejecutar el mirror final.

Nota 2026-06-15: `build_annual_tax_ownership_visual_review_packet` renderiza
las primeras paginas de esos candidatos a PNG bajo `local-evidence` para OCR o
revision manual. La corrida real genera 19 paginas de 10 candidatos, sin errores
de render. Las imagenes pueden contener datos sensibles y no se versionan; el
indice JSON conserva solo hashes, `path_ref`, tipos documentales y nombres de
archivo locales. Este paquete deja preparada la revision visual, pero no cierra
ownership ni autoriza DB hasta completar el template con fuente suficiente.

Nota 2026-06-15: `audit_annual_tax_controlled_package_readiness` separa readiness
de writer DB y readiness anual. El draft AC2024/AT2025 v3 queda con
`ready_for_db_writer=true` y `missing_paths_count=0`, pero
`ready_for_annual_generation=false` por `ownership_snapshot_missing`. Esta regla
evita declarar completa la prueba espejo si faltan socios/participaciones
vigentes, aunque la contabilidad mensual ya pueda cargarse.

Nota 2026-06-15: Renta Anual/Etapa 6 agrega template de paquete normalizado
AC2024/AT2025. `build_annual_tax_controlled_db_load_template` toma el
manifiesto read-only, prearma 12 meses para carga controlada, separa refs de
entrada y objetivos de comparacion, y no escribe DB. El siguiente trabajo es
completar esos valores por parser o carga manual controlada y aplicar el
writer local antes de generar/comparar artefactos AT2025.

Nota 2026-06-15: Renta Anual/Etapa 6 agrega auditor de completitud para el
paquete controlado AC2024/AT2025. `audit_annual_tax_controlled_package_readiness`
lee un template/paquete JSON, no escribe DB, no lee documentos fuente y reporta
campos faltantes antes del writer. Contra el template real Inmobiliaria Puig
confirma 12 meses, sin meses faltantes y con objetivos de comparacion, pero
mantiene `ready_for_db_writer=false` por 132 campos normalizados pendientes.

Nota 2026-06-15: Renta Anual/Etapa 6 agrega draft de valores AC2024 y aplica
writer local controlado para Inmobiliaria Puig. `build_annual_tax_controlled_values_draft`
extrae Libro Diario, Libro Mayor, F29 y remuneraciones desde fuentes permitidas,
rellena 176 campos, deja `ready_for_db_writer=true` y `apply_annual_tax_controlled_db_load`
materializa 12 `MonthlyTaxFact` normalizados en SQLite local ignorado. El gate
queda parcial porque faltan capacidades anuales DDJJ/F22, source bundle en DB,
proceso anual, DDJJ/F22/documento soporte y comparacion contra outputs esperados.

Nota 2026-06-15: Renta Anual/Etapa 6 agrega run anual controlado AC2024/AT2025.
`AnnualTaxSourceBundle` diferencia meses con obligacion declarada de meses con
hecho tributario mensual normalizado, permitiendo F29 `no_aplica` sin inventar
obligaciones. `run_annual_tax_controlled_mirror` crea capacidades DDJJ/F22,
TaxYearRuleSet, mappings, layouts, fuente de balance anual preview, bundle
`snapshot_controlado`, ProcesoRentaAnual, DDJJ/F22, matriz, dossier, export y
checklist sobre SQLite local ignorado. El gate ya no falla por falta de proceso
anual, DDJJ/F22 o source bundle; queda parcial por revision tributaria, bienes
raices/respaldo y comparador de valores pendiente.

Nota 2026-06-15: Renta Anual/Etapa 6 agrega comparador de cobertura de outputs
esperados AC2024/AT2025. `compare_annual_tax_expected_outputs` lee el
manifiesto y la DB local/controlada, no escribe DB, no usa SII real y mantiene
Balance/RLI/CPT/RAI/DDJJ/F22 finales como comparacion, no como input. Contra
SQLite local de Inmobiliaria Puig confirma cobertura completa de balance
tributario, workbooks CPT/RLI, registros DIVIDENDOS/RAI/RETIROS/SAC, DDJJ
1835/1837/1847/1887/1926/1948 y F22. La prueba espejo sigue parcial por
warnings/revision de artefactos generados y gates finales; la comparacion v5 ya
cubre semantica documental DDJJ/F22 y presencia de 138/138 valores comparables
sin usar outputs finales como input.

Nota 2026-06-16: la corrida controlada real AC2024/AT2025 desde la fuente
externa de Inmobiliaria Puig confirma que el paquete detallado ya puede entrar
al writer DB (`ready_for_db_writer=true`) y que LeaseManager genera una capa
anual preliminar completa en SQLite local ignorada: 12 `MonthlyTaxFact`, 10
F29/obligaciones, `AnnualTaxSourceBundle`, workbooks, registros empresariales,
matriz, dossier, export, DDJJ y F22 preparados. El gate unico queda parcial,
no por falta de pipeline, sino por limites correctos de cierre: fuente
societaria/ownership no cargada como snapshot independiente, bienes raices sin
items, artefactos con warnings/revision pendiente y checklist no completado.
Esto fija la proxima accion objetiva: completar snapshot controlado de
ownership/bienes raices y revisar artefactos anuales, no reabrir goal prompts,
EDIG ni metatareas ya cerradas.

| Frente | Fuentes rectoras | Areas de codigo/docs | Etapa | Estado actual | Gate/evidencia requerida | Proxima accion |
| --- | --- | --- | --- | --- | --- | --- |
| Gobierno documental | Fuente de verdad, AGENTS, README, cursor operativo | `docs/governance`, `AGENTS.md`, `ORDEN_DE_LECTURA.md`, `.gitignore`, `docs/product/EXECUTION_CURSOR_MAYO_2026.md` | 0 | resuelto_confirmado | PR con CI verde y docs consistentes | Mantener actualizado al cambiar fuentes; bloqueos y evidencia son controles operativos de cierre, no arquitectura de producto; el cursor gobierna reanudaciones, worktrees tacticos y metatareas cerradas; artefactos locales de herramienta como `.codex-spreadsheet/`, `.playwright-cli/`, capturas PNG en el root y archivos manuales `CONFIDENCIAL`/`NO_SUBIR` quedan ignorados para no ensuciar `main` ni confundirse con paquetes activos; acceptance ejecuta `assert-repo-hygiene.ps1 -IncludeUntracked` para detectar artefactos sensibles no versionados ni ignorados sin leer secretos. |
| PRD vigente | `01_Set_Vigente/PRD_CANONICO.md` | `01_Set_Vigente`, `docs/product` | 0 | resuelto_confirmado | PRD Mayo 2026 aceptado y promovido | Usarlo como contrato rector unico. |
| PlataformaBase | PRD, ADR stack | `backend/core`, `users`, `audit`, `health`, `frontend`, `scripts/run-acceptance-workflows.ps1`, `scripts/codex-github-package.ps1` | 0 | resuelto_confirmado | CI main verde, acceptance local, build frontend, guard Etapa 1 no evidencial, readiness local Etapa 1 anti-bucle, snapshot evidencial vacio de Etapa 1 cubierto en acceptance como `bloqueado_dato_real`, `real_autorizado` protegido contra migraciones desde el gate Etapa 1, redaccion de metadata sensible en APIs de auditoria y Auth/Users, firma interna de cache demo no expuesta al cliente, admin de usuario sin metadata cruda ni borrado manual, detector transversal de referencias sensibles cubre claves `authorization`/`private_key` sin marcar valores `AuthorizationRef` no sensibles, guards transversales de outputs versionables con limite real de directorio en wrappers PowerShell y cierre GitHub por CLI/API con fallback seguro a Git Credential Manager cuando `gh auth status` no esta logueado | Mantener como baseline y no rehacer. |
| Compliance datos sensibles | PRD, ADR secretos y auditoria, matriz gates | `backend/compliance`, `backend/core/compliance_data_readiness.py`, `scripts/run-compliance-data-readiness-gate.ps1`, backoffice compliance | 0 | parcial | Exports cifrados con motivo, scope, usuario, expiracion, auditoria, metadata visible no sensible, `encrypted_ref` no sensible y readiness `Compliance.DatosPersonalesChile2026` | Exportes sensibles cifran payload, exigen `payload_hash` SHA-256 hexadecimal de 64 caracteres, verifican que el payload descifrado coincida con ese hash antes de descargar, niegan como acceso controlado los payloads no descifrables, rechazan nuevas URLs, correos, tokens, bearer, api keys o credenciales en `motivo`/`scope_resumen`/`encrypted_ref`, bloquean categoria `secreto`, exigen categoria canonica por tipo de exportacion, motivo operativo y actor creador trazable, y politica de retencion activa tambien desde `prepare_sensitive_export`, bloquean nuevas exportaciones preparadas sin hold que excedan 30 dias de vigencia, tratan `expirada` como estado terminal no descargable ni revocable, impiden revocar dos veces una exportacion sensible, normalizan una exportacion preparada vencida sin hold a `expirada` antes de rechazar su revocacion con `access_denied` atomico y sin crear evento `revoked`, auditan intentos denegados de descarga revocada/expirada, revocacion vencida, payload desalineado o payload no descifrable, redactan `evento_inicio` sensible heredado de politicas de retencion en API/admin y redactan metadata visible sensible heredada y `encrypted_ref` sensible heredado antes de exponer list/detail al backoffice; `PoliticaRetencionDatos` normaliza `evento_inicio`, `ExportacionSensible` normaliza `motivo`, `scope_resumen`, `payload_hash` y `encrypted_ref` antes de validar/persistir, y readiness bloquea metadata visible no canonica heredada; al revocar desde API o servicio exige actor trazable y motivo no sensible, y persiste `revocation_reason` en auditoria; el admin Django de politicas y exportaciones sensibles no expone campos crudos sensibles, quita `evento_inicio`/`encrypted_ref` de busqueda, muestra solo versiones redactadas y deshabilita alta, edicion y borrado manual para que cambios de politicas, preparacion, descarga, expiracion y revocacion pasen por API, servicios, dominio y auditoria; `audit_compliance_data_readiness` consolida politicas de retencion por categoria, hold tributario/documental, purga restringida, integridad/auditoria de exportes, metadata sensible heredada, motivo faltante, `encrypted_ref` sensible heredado, categoria secreto heredada, hashes no canonicos, metadata visible no canonica heredada, payloads cifrados desalineados con hash, payloads no descifrables, expiraciones preparadas mayores a 30 dias heredadas, estados expirados inconsistentes, conteo de accesos denegados, eventos de auditoria sin actor, sin target de exportacion existente, con metadata desalineada frente a categoria, tipo, scope, hash, hold, expiracion y creador, validando `estado` como valor historico del evento para no bloquear accesos validos que luego fueron revocados o expirados, revocados sin motivo no sensible o revocados con motivo sensible clasificado explicitamente; refs finales, deadline 2026-12-01 y fuente autorizada sin leer secretos ni datos reales. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel`, `AuthorizationRef`, politica aprobada, responsables, controles, evidencia archivada y validacion legal-operativa no sensibles. |
| Patrimonio | PRD, modelo canonico | `backend/patrimonio`, backoffice patrimonio | 1 | implementado_sin_evidencia | Datos reales/snapshot y validacion de entidades | API y auditor Etapa 1 validan socios, empresas, comunidades, participaciones actualmente vigentes, participantes patrimoniales activos, transferencia/reemplazo/redistribucion auditada de participaciones conservando 100%, con motivo no sensible y evidencia no sensible, duplicidad de participantes en el set vigente, representaciones actualmente vigentes, ventanas efectivas de representacion sin solapes, evidencia no sensible en representaciones designadas, observaciones de representacion sin referencias sensibles, propiedades, servicios/gastos comunes estructurados y duplicidad de identidad por rol de avaluo o identidad operativa fuerte; `Propiedad.full_clean()` y API bloquean nuevas propiedades activas duplicadas por ROL de avaluo normalizado o identidad operativa, mientras el auditor mantiene deteccion de snapshots heredados; `RepresentacionComunidad` exige `evidencia_ref` formal trazable cuando el modo es `designado`, valida representantes patrimoniales contra participaciones activas solapadas con la ventana de la representacion, rechaza observaciones con URLs, correos, tokens o credenciales, la API redacta observaciones heredadas sensibles, snapshots/backoffice redactan evidencia sensible heredada y el admin Django no expone ni busca `evidencia_ref` cruda, mostrando solo version redactada; `ServicioPropiedad` exige proveedor/administracion, numero de cliente, evidencia no sensible y gasto comun activo estructurado cuando un contrato vigente/futuro declara gastos comunes; la activacion de empresas/comunidades no acepta participaciones futuras como vigentes, participantes inactivos/no listos ni participantes vigentes repetidos, comunidades activas tampoco aceptan representaciones futuras como vigentes, la planificacion futura no solapada queda permitida y los solapes heredados quedan defectuosos, incluyendo representaciones patrimoniales futuras con participacion futura alineada, y las desactivaciones no pueden dejar propiedades, representaciones actualmente vigentes, participaciones activas, cuentas recaudadoras activas, mandatos operativos activos ni identidades de envio activas colgando de entidades no operativas; el admin Django bloquea alta, edicion y borrado manual de socios, empresas, comunidades, participaciones, representaciones, propiedades y servicios de propiedad. Ejecutar `scripts/run-stage1-snapshot-gate.ps1` contra snapshot/DB autorizada. |
| Operacion | PRD, ADR identidad envio | `backend/operacion`, backoffice operacion | 1 | implementado_sin_evidencia | Cuentas, mandatos e identidades validadas | Cuentas/recaudador soportan empresa, comunidad o socio; cuentas recaudadoras activas exigen uso operativo declarado, modo `manual_controlado` o `gate_bancario`, y evidencia operativa trazable no sensible; entidad facturadora exige `ConfiguracionFiscalEmpresa` activa con regimen tributario activo y cuenta recaudadora activa propia; mandatos activos que comunican o facturan documentos exigen autoridad operativa con nombre, RUT valido normalizado y evidencia trazable no sensible; identidades de envio activas exigen `credencial_ref` trazable no sensible y la API redacta referencias sensibles heredadas; el admin Django de Operacion no expone ni busca `evidencia_operativa_ref`, `credencial_ref` ni `autoridad_operativa_evidencia_ref` crudos y muestra solo versiones redactadas; cuentas recaudadoras no pueden pausarse/inactivarse si sostienen mandatos activos, mandatos no pueden inactivarse si sostienen contratos vigentes/futuros ni recortar su vigencia fuera del rango contractual dependiente, la planificacion futura no solapada de mandatos queda permitida y los solapes heredados quedan defectuosos, identidades no pueden suspenderse/inactivarse si sostienen asignaciones activas ni mutar canal u owner si dejan incompatibles esas asignaciones, y la ultima asignacion activa de un mandato con contratos vigentes/futuros no puede inactivarse; auditor Etapa 1 exige identidad/asignacion de canal activa por mandato de contrato vigente/futuro y detecta cuentas activas sin evidencia operativa, facturadoras activas sin cuenta propia, credenciales sensibles existentes, autoridad operativa faltante/invalida/sensible, identidad ajena a administrador/facturadora y uso de identidad distinta del propietario sin autorizacion de comunicacion; usar `scripts/run-stage1-snapshot-gate.ps1` contra snapshot/DB autorizada. |
| Contratos | PRD, reglas contractuales | `backend/contratos`, backoffice contratos | 1 | implementado_sin_evidencia | Matriz contrato-propiedad-periodo-garantia | Usar `scripts/run-stage1-snapshot-gate.ps1`; la fuente debe tener al menos un contrato vigente o futuro, no solo contratos historicos; arrendatarios, contactos de pago estructurados con rol operativo no vacio exigidos por dominio/API/auditor y capturados/visibles desde backoffice, codeudores solidarios con snapshot nombre/RUT valido desde API anidada y auditor, maximo 3 activos, sin duplicados y capturados/visibles desde backoffice para contratos simples, contacto/domicilio operativo, perfil documental de persona natural cuando la politica contractual exige nacionalidad/estado civil/profesion, `Contrato.full_clean()` y API exigen canal operativo activo por mandato para contratos vigentes/futuros, vigencia del mandato cubriendo contrato, override opcional de `IdentidadDeEnvio` validado contra identidad activa y owner autorizado por mandato y selector backoffice filtrado por identidades activas elegibles del mandato, politica documental activa de tipo `contrato_principal`, y representante legal de arrendatario empresa exigido por API/modelo con nombre y RUT valido normalizado, auditado en datos heredados y capturado/visible desde backoffice para contratos vigentes/futuros; contratos, vinculos contrato-propiedad, periodos, garantias y avisos de termino existentes se validan globalmente, incluyendo filas historicas; la clasificacion agregada de `contratos_activos_o_futuros` queda acotada a contratos/avisos vigentes o futuros para no atribuirle defectos historicos; calendario mensual, continuidad de periodos, periodos existentes acotados a la vigencia contractual, al calendario mensual y a numeracion cronologica, minimo operativo, renovaciones de contratos con tramos usando por defecto la base del ultimo tramo vigente o politica documentada no sensible cuando cambia monto/moneda, renovacion automatica operacional que extiende la vigencia creando `PeriodoContractual` auditable y queda bloqueada por `AvisoTermino` registrado, propiedad principal o vinculada activa en contratos vigentes/futuros, `Contrato.full_clean()` y API exigen gasto comun activo estructurado cuando `tiene_gastos_comunes` aplica, y el backoffice de Contratos muestra/bloquea esa cobertura desde el mandato seleccionado, composicion de roles principal/vinculada, contrato acotado a una propiedad o pareja principal/vinculada, propiedad vinculada sin contrato independiente, pareja principal/vinculada con mismo codigo efectivo, contrato futuro con aviso/terminacion, avisos de termino con fecha efectiva dentro del contrato y timestamp real `registrado_at` obligatorio para medir oportunidad sin inventar fechas, transiciones de estado contractual bloquean regresiones como `vigente` a `pendiente_activacion` y reaperturas directas de estados terminales, cancelacion contractual bloqueada si el contrato ya conserva pagos mensuales, garantia operativa, entrega de llaves o aviso registrado, con deteccion explicita `stage1.contrato.cancelado_con_efectos_irreversibles` para snapshots heredados, conflicto entre aviso, renovacion ya ejecutada y contrato futuro resuelto con referencia no sensible y motivo trazable sin cancelar ni reescribir efectos producidos, terminacion anticipada con ultimo mes parcial solo con regla o decision de prorrata no sensible y evento auditable dedicado, entrega de llaves con garantia cubierta o autorizacion auditada no sensible cuando `fecha_entrega` queda registrada, codigo efectivo `001-999` en contrato, pagos existentes alineados a la propiedad principal, al periodo contractual y al vencimiento del mes operativo, contratos retroactivos registrados despues del dia 5 alertados para posible notificacion manual sin bloquear por si solos, bloqueo de reconstruccion automatica de cobros vencidos antes del registro operativo, pagos existentes de cobro pasado retroactivo marcados defectuosos, pagos en estado pagado efectivo con monto y fecha trazable, ajustes contractuales existentes normalizados al primer dia del mes, acotados a la vigencia contractual y sin dejar meses CLP bajo el minimo operativo de 1.000, pagos/distribuciones existentes, respaldo `ValorUFDiario` valido para pagos dependientes de UF, con procedencia manual trazable cuando aplique, coherencia de garantias con `HistorialGarantia`, fechas de recepcion/cierre, movimiento final de garantia, cronologia de movimientos derivados, garantias parciales abiertas con aceptacion formal trazable o marca de incompletitud y garantias con exceso sobre lo pactado solo con resolucion no sensible, y admin Django sin alta, edicion ni borrado manual para arrendatarios, contactos, contratos, relaciones, periodos, codeudores y avisos ya tienen gate local. |
| CobranzaActiva | PRD, gates canales/WebPay | `backend/cobranza`, `canales`, frontend, `backend/core/stage2_cobranza_readiness.py`, `scripts/run-stage2-readiness-gate.ps1` | 2 | parcial | Cobros reproducibles sin envios reales accidentales | Cadencias de notificacion por contrato/canal habilitado se normalizan, exigen canal activo del mandato, redactan evidencia sensible heredada y son bloqueantes en readiness si faltan para contratos vigentes/futuros; los pagos mensuales pendientes/atrasados con cadencia activa materializan recordatorios locales por pago/canal/dia sin enviar proveedores, se exponen en snapshot/backoffice y readiness bloquea pagos cobrables sin programacion, con programacion heredada invalida, ligada a configuracion inactiva, omitida sin motivo operativo no sensible o preparada con mensaje saliente no alineado al pago/contrato/arrendatario; pagos mensuales abiertos vencidos se refrescan contra fecha de corte, pasan de `pendiente` a `atrasado`, recalculan `dias_mora`, sincronizan estado de cuenta y readiness bloquea pendientes vencidos o mora atrasada; dominio, API y servicio operacional comparten la matriz de transiciones de `PagoMensual` para impedir saltos como `pendiente` a `en_repactacion` aunque exista plan; el efecto economico del codigo efectivo queda persistido como `monto_efecto_codigo_efectivo_clp`, debe cuadrar con `monto_calculado_clp - monto_facturable_clp` y, si no es cero, conservar evento auditable `cobranza.pago_mensual.effective_code_applied` con actor y montos alineados; el score de pago excluye pagos sin registro operativo valido y expone `score_meses_sin_registro_operativo` para detectar estados heredados desalineados; los pagos `pagado_por_acuerdo_termino` o `condonado` requieren referencia no sensible, motivo y evento auditable `cobranza.pago_mensual.exceptional_state_resolved` con actor y resolucion alineada; pagos originales en `en_repactacion` o `pagado_via_repactacion` deben enlazar una `RepactacionDeuda` del mismo contrato/arrendatario, conservar `dias_mora` y mantener estado compatible del plan activo/cumplido; registro manual de envio exige `external_ref` trazable no sensible y revalida gate/identidad/destinatario/mandato; `MensajeSaliente.clean()` rechaza estados `preparado`/`enviado` sin gate abierto, readiness Email, identidad activa, destinatario, mandato operativo, contexto WhatsApp valido o documento formalizado cuando la politica lo exige, y tambien exige `external_ref` no sensible, `enviado_at`, motivo de bloqueo no sensible y evento auditable con actor para mensajes enviados; Email abierto exige `evidencia_ref`, prueba aislada/envio, OAuth/credencial validada, `IdentidadDeEnvio` activa y `AsignacionCanalOperacion` activa sobre mandato operativo activo, todo con refs no sensibles; mensajes con `DocumentoEmitido` cuya politica exige firma/notaria solo se preparan o marcan enviados si el documento ya esta formalizado; WhatsApp queda cerrado por defecto sin opt-in evidenciado con referencia no sensible, template aprobado, ventana permitida, identidad y asignacion activas cuando se abre, sin refs sensibles en gate ni evidencia de opt-in; un bloqueo definitivo de WhatsApp debe marcar el contacto con motivo, evidencia no sensible, fecha, evento auditable y alerta administrativa, la rehabilitacion manual conserva la traza del bloqueo, y un bloqueo/fallo de mensaje WhatsApp debe conservar Email alternativo preparado/enviado o alerta critica/fallback trazable; WebPay tiene gate `WebPay.IntentoPago` con `evidencia_ref` no sensible, intento local con `return_url_ref` no sensible, `motivo_bloqueo` no sensible, `fecha_pago_webpay` separada y confirmacion manual solo con `external_ref` no sensible, pago mensual pagado con la misma fecha WebPay y gate revalidado; garantias recibidas parcialmente exponen brecha, incompletitud y aceptacion formal no sensible hasta regularizarse; repactaciones existentes se validan contra coherencia saldo/estado, total de plan y excepcion formal auditable cuando no cubren toda la deuda original; codigos residuales existentes se validan contra formato canonico `CCR-XXXXXX` con caracteres no ambiguos; estados de cuenta existentes deben estar recalculados contra pagos abiertos, repactaciones activas y codigos residuales activos; valores UF manuales requieren evidencia, motivo, responsable no sensibles y evento auditable con actor; APIs y snapshots redactan refs sensibles, `restricciones_operativas`, `provider_payload` sensible, `motivo_bloqueo` sensible heredado en mensajes salientes e intentos WebPay, `motivo_estado` sensible heredado en notificaciones de cobranza, evidencia opt-in/bloqueo/rehabilitacion WhatsApp heredada y `storage_ref` documental expuesto por Canales ya persistidos en gates, mensajes salientes e intentos WebPay antes de exponerlos al backoffice, y el admin Django de Canales conserva inspeccion redactada sin alta, edicion ni borrado manual; el modelo rechaza nuevas escrituras de mensajes salientes e intentos WebPay con `provider_payload` o `motivo_bloqueo` sensible; `audit_stage2_cobranza_readiness` detecta UF manual sin procedencia/evento auditable, refs sensibles en gates, opt-in WhatsApp, bloqueos definitivos sin traza/evento/alerta, mensajes WhatsApp bloqueados/fallidos sin fallback trazable, mensajes enviados sin timestamp, sin evento auditable o con evento auditable sin actor/`external_ref` no sensible alineado, mensajes con motivo de bloqueo sensible heredado, mensajes/confirmaciones WebPay con `external_ref` sensible o desalineacion con el pago mensual, documentos no formalizados en mensajes preparados/enviados cuando la politica exige firma/notaria, pagos pendientes vencidos o mora desactualizada, efecto de codigo efectivo descuadrado o sin evento auditable, pagos excepcionales sin resolucion trazable o sin evento auditable, pagos en estados de repactacion sin plan trazable o con plan incompatible, estados de cuenta faltantes o desactualizados, repactaciones inconsistentes, repactaciones parciales sin excepcion formal o sin evento auditable, codigos residuales no canonicos e intentos WebPay con `return_url_ref`, `motivo_bloqueo` o `provider_payload` sensible, y `run-stage2-readiness-gate.ps1` consolida readiness sin llamar proveedores, exige `SourceLabel`/`AuthorizationRef` para fuentes evidenciales y solo cierra con `source_kind` `snapshot_controlado` o `real_autorizado`. Falta prueba externa real/controlada de correo/WebPay y datos de Etapa 1 confirmados para cierre. |
| Conciliacion | ADR banca, gates banco | `backend/conciliacion`, `backend/core/stage3_conciliacion_readiness.py`, `scripts/run-stage3-readiness-gate.ps1`, frontend | 3 | parcial | Saldo sistema igual a saldo banco con data controlada | Conexion bancaria activa/primaria exige referencias no sensibles de gate, credencial, conectividad, movimientos y saldos segun capacidad; movimientos `provider_sync` solo entran por conexion primaria lista con `transaction_id_banco` no sensible y no duplicado por conexion, reforzado por modelo y constraint DB, toda `referencia` bancaria de movimiento debe ser no sensible, y carga manual exige evidencia de importacion no sensible; movimientos conciliados exactos existentes deben mantener target coherente con pago mensual pagado, codigo residual pagado o transferencia intercuenta trazada de la misma cuenta recaudadora; ingresos desconocidos existentes deben coincidir con movimiento bancario, cuenta, monto, fecha, descripcion, tipo abono y estado de conciliacion; ingresos desconocidos resueltos manualmente requieren pago mensual, contrato, periodo economico canonico `YYYY-MM` alineado al mes/anio del `PagoMensual`, criterio aplicado, evidencia no sensible y motivo; los cargos bancarios conciliados exactos requieren resolucion manual resuelta, y los cargos bancarios resueltos manualmente requieren `CategoriaMovimiento`, entidad afectada, periodo economico canonico `YYYY-MM`, criterio de reparto, evidencia no sensible y motivo; las transferencias internas/intercuenta resueltas manualmente requieren par cargo/abono, cuentas distintas, monto opuesto equivalente, periodo economico canonico `YYYY-MM`, owner origen/destino, criterio de conciliacion no sensible, evidencia no sensible, responsable y motivo no sensible, y readiness detecta pares o resoluciones heredadas cerradas sin contexto, con periodo/target inconsistente, con evidencia sensible o con criterio/motivo sensible; resoluciones manuales abiertas que quedan obsoletas por match exacto u otra resolucion manual se cierran como `superseded` con motivo, metadata y evento de auditoria alineado, y readiness bloquea supersesiones sin metadata, motivo o evento de auditoria alineado; `CuadraturaBancaria` registra saldo sistema, saldo banco, diferencia calculada, fecha de cuadratura alineada al periodo economico, evidencia, responsable y motivo no sensible por cuenta/periodo, y readiness bloquea cierres sin registro para cada cuenta/periodo con movimientos, sin estado cuadrado, con refs/motivos sensibles, con periodo/fecha desalineados o con diferencia distinta de cero; API/snapshot/admin redactan refs bancarias, incluyendo `referencia` de movimientos, refs de cuadratura y contexto sensible de cuadraturas/transferencias ya persistido; el admin Django no permite borrar conexiones ni mutar/borrar movimientos, ingresos desconocidos, cuadraturas o transferencias fuera de APIs/servicios auditados; `audit_stage3_conciliacion_readiness` y `run-stage3-readiness-gate.ps1` consolidan conexiones, movimientos, ingresos desconocidos, resoluciones manuales, transferencias intercuenta, cuadraturas, senales de saldo, continuidad local de saldos reportados, referencias finales, cargos exactos sin resolucion y deteccion de refs sensibles existentes sin llamar bancos. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel` y `AuthorizationRef` no sensibles. Falta banco real o snapshot autorizado, evidencia Etapa 2, prueba bancaria, cuadratura sistema/banco y responsable para cierre. |
| Contabilidad | ADR contabilidad nativa | `backend/contabilidad`, `backend/core/stage5_contabilidad_readiness.py`, `scripts/run-stage5-readiness-gate.ps1`, reporting | 5 | parcial | Eventos, reglas, asientos y cierre mensual | Preparar y aprobar cierre mensual exige eventos posteados, asientos balanceados, `periodo_contable` coherente con `fecha_contable`, `hash_integridad` presente y vigente para asientos contabilizados, movimientos de asiento obligatorios que sumen los totales debe/haber y cuentas contables de la misma empresa del evento; `EventoContable` evita doble contabilizacion efectiva del mismo hecho economico dejando en revision un evento nuevo si ya existe otro contabilizado para la misma empresa, tipo y entidad origen, y readiness reporta `stage5.duplicate_posted_events` para snapshots heredados; `MovimientoAsiento.clean()` bloquea nuevas escrituras con cuentas de otra empresa y readiness bloquea snapshots heredados con esa incoherencia; tambien bloquea si existen movimientos bancarios no resueltos del periodo para cuentas de la empresa y exige `CuadraturaBancaria` cuadrada para cada cuenta recaudadora con movimientos del periodo, con readiness `stage5.close_bank_square_missing` o `stage5.close_bank_square_not_square` para cierres heredados. Las transferencias intercuenta conciliadas que involucren cuentas recaudadoras con owner empresa generan eventos contables idempotentes de salida/entrada (`TransferenciaIntercuentaSalida`, `TransferenciaIntercuentaEntrada`) y `audit_stage5_contabilidad_readiness` bloquea snapshots con transferencias de empresa sin eventos alineados a empresa, fecha, moneda y monto del movimiento bancario correspondiente. Un cierre aprobado solo se reabre con `PoliticaReversoContable` activa para `reapertura_cierre_mensual`, que permita reapertura y exija aprobacion; ademas la reapertura debe aplicar un efecto contable posterior (`reverso` o `asiento_complementario`) con motivo, efecto esperado, monto, evidencia no sensible y `EventoContable` contabilizado bajo regla/matriz activa. `audit_stage5_contabilidad_readiness` marca como brecha los cierres aprobados sin politica, cierres reabiertos sin efecto, efectos sin evento contabilizado y efectos con referencias sensibles. APIs, reporting y admin redactan payloads, `storage_ref` y refs de centro de resultado sensibles ya persistidos en eventos, movimientos, obligaciones, libros, balances y cierres; el dominio rechaza nuevas escrituras sensibles, el admin deja artefactos generados en solo lectura sin borrado manual y `audit_stage5_contabilidad_readiness` detecta referencias sensibles como brecha bloqueante sin exponer valores. `audit_stage5_contabilidad_readiness` y `run-stage5-readiness-gate.ps1` consolidan configuracion fiscal, reglas/matriz, eventos, asientos, hash vigente, integridad de movimientos, snapshots, cierres, efectos de reapertura, transferencias intercuenta y conciliacion/cuadratura bancaria del periodo sin conectar servicios externos. Reporting financiero mensual expone `control_cierre_mensual` como vista local de control de cierre contable, movimientos bancarios no resueltos, banco cuadrado, obligaciones PPM/F29 y bloqueadores del periodo. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel` y `AuthorizationRef` no sensibles. Sigue faltando Conciliacion cerrada, ledger/reportes controlados y responsable para cierre. |
| Documentos | ADR estrategia documental | `backend/documentos`, `scripts/run-stage5-documents-readiness-gate.ps1`, backoffice documentos, docs operativos | 5 | parcial | PDF canonico, origen, firma/notaria definida | Documentos emitidos exigen `storage_ref` PDF no sensible, `checksum` SHA-256 canonico, `usuario` responsable, politica activa para su tipo documental y plantilla activa para su tipo/version; `DocumentoEmitido.clean()` bloquea nuevas escrituras sin responsable, sin politica activa o sin plantilla activa, la API valida create usando el usuario autenticado antes de persistir, el endpoint generico no puede crear, convertir ni mutar documentos `generado_sistema`, y `PoliticaFirmaYNotaria.clean()` evita desactivar politicas ya usadas por documentos existentes. Expedientes documentales exigen `entidad_tipo`, `entidad_id` y `owner_operativo` no sensibles; dominio/API rechazan nuevas URLs, correos, tokens o credenciales, API/snapshot/admin redactan valores heredados sensibles y `audit_document_readiness` reporta `documents.expediente_invalid` o `documents.expediente_sensitive_reference` sin imprimir valores. APIs, snapshot y admin/backoffice redactan `storage_ref`, `evidencia_formalizacion_ref` y `correccion_ref` sensibles heredados antes de exponer documentos, conservan metadata trazable y quitan esas refs de la busqueda administrativa; readiness documental detecta referencias sensibles, checksums heredados no canonicos, documentos sin usuario y documentos heredados sin politica activa como brechas bloqueantes sin imprimir valores. Formalizacion bloquea comprobantes notariales borrador/cancelados, documentos borrador/archivados/cancelados, cualquier intento de pasar a `formalizado` por create/update generico, mutaciones posteriores de documentos formalizados y re-formalizaciones, obligando el endpoint `formalizar/` con auditoria especifica desde estado `emitido`; las correcciones posteriores se registran como versiones correctivas con `documento_origen` formalizado, mismo expediente/tipo documental, PDF/checksum propios, `correccion_ref` no sensible y auditoria `documentos.documento_emitido.corrective_version_created`, y el endpoint generico bloquea conversiones o mutaciones posteriores de esa traza auditada; `audit_document_readiness` bloquea formalizados sin evento `documentos.documento_emitido.formalized`, versiones correctivas heredadas invalidas o sin auditoria dedicada, y formalizados con politica notarial sin recepcion, sin comprobante, con comprobante de tipo incorrecto, de otro expediente o en estado no permitido. `audit_document_readiness` y `run-stage5-documents-readiness-gate.ps1` consolidan politicas activas por tipo documental, metadata, responsables y prueba PDF controlada sin leer storage real, y rechazan outputs dentro del repo fuera de `local-evidence/` antes de recolectar readiness. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel` y `AuthorizationRef` no sensibles. Falta decision final de politica firma/notaria, prueba PDF controlada y responsable para cierre. |
| SII | ADR SII, matriz gates | `backend/sii`, `backend/core/stage4_sii_readiness.py`, `scripts/run-stage4-readiness-gate.ps1`, backoffice SII | 4 | parcial | Certificacion/ambiente SII y regla fiscal validada | Capacidad SII abierta exige refs no sensibles de certificado, evidencia, prueba de flujo, autorizacion de ambiente, regla fiscal y `ConfiguracionFiscalEmpresa` activa de la misma empresa dentro del regimen fiscal automatizable v1; el dominio/API rechaza capacidades abiertas sin esa configuracion activa, y una empresa fuera de ese regimen no puede abrir automatizacion tributaria oficial. DTE/F29/anuales bloquean referencias sensibles en tracking, borradores o paquetes, rechazan por dominio nuevas escrituras asociadas a empresas sin `ConfiguracionFiscalEmpresa` activa propia, y APIs/snapshot/auditoria de cambios DTE redactan refs o payloads sensibles heredados antes de exponerlos o persistir metadata operativa; borradores/estados revalidan readiness local y presentaciones finales siguen bloqueadas hasta gate externo autorizado. DTE, consulta de estado DTE, F29, DDJJ y F22 validan la familia tributaria correspondiente (`DTEEmision`, `DTEConsultaEstado`, `F29Preparacion`, `DDJJPreparacion`, `F22Preparacion`); `enviado_manual_controlado` revalida emision, los estados finales DTE `aceptado`/`rechazado`/`anulado` revalidan consulta de estado, y readiness bloquea snapshots heredados con capacidad cruzada o DTE final sin `DTEConsultaEstado` lista. F29, DDJJ y F22 en estado preparado, aprobado, observado o rectificado revalidan capacidad SII abierta/lista, y `audit_stage4_sii_readiness` bloquea DTE externo o preparaciones tributarias avanzadas con capacidad condicionada, cerrada o invalida. `audit_stage4_sii_readiness` y `run-stage4-readiness-gate.ps1` consolidan configuracion fiscal por empresa, capacidades, DTE, F29 y preparacion anual sin conectar SII ni leer certificados, y detectan refs sensibles existentes. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel` y `AuthorizationRef` no sensibles. Falta ambiente SII real/controlado autorizado, evidencia de ledger, regla fiscal validada y responsable para cierre. |
| Renta Anual | PRD, SII, contabilidad, documentos | `backend/sii`, `backend/reporting`, `backend/core/stage6_renta_anual_readiness.py`, `scripts/run-stage6-readiness-gate.ps1`, documentos tributarios | 6 | parcial | Doce cierres mensuales, reglas fiscales, DDJJ/F22 y certificados trazables | `audit_stage6_renta_anual_readiness` y `run-stage6-readiness-gate.ps1` consolidan configuracion fiscal, capacidades anuales DDJJ/F22, cierres aprobados, obligaciones mensuales, AnnualTaxSourceBundle, TaxYearRuleSet/TaxCodeMapping, ProcesoRentaAnual, AnnualTaxTrialBalance/Line, AnnualTaxWorkbook/Line, AnnualEnterpriseRegisterSet/Movement, AnnualRealEstateSection/Item, AnnualTaxDDJJFormLayout, AnnualTaxF22ExportLayout, AnnualTaxArtifactMatrix/Item, AnnualTaxDossier, AnnualTaxExport, AnnualTaxReviewChecklist, DDJJ, F22 y respaldos tributarios PDF sin conectar SII ni leer certificados reales; capacidades anuales, proceso, DDJJ y F22 bloquean si pertenecen a empresas sin configuracion fiscal activa propia, y el dominio/API rechaza nuevas escrituras equivalentes. `AnnualTaxSourceBundle` congela fuentes anuales no sensibles por empresa/ano tributario con hash SHA-256 del payload normalizado; la generacion anual crea o reutiliza ese bundle antes de preparar ProcesoRentaAnual/DDJJ/F22, y readiness bloquea procesos heredados sin bundle, con bundle no congelado, desalineado o con metadata/hash distinta. La generacion anual exige `TaxYearRuleSet` aprobado por ano tributario/regimen, `hash_normativo`, fuente/responsable no sensibles y al menos un `TaxCodeMapping` activo validado; el resumen anual conserva version/hash/conteos por destino sin copiar reglas EDIG ni exponer secretos. `AnnualTaxTrialBalance`/`AnnualTaxTrialBalanceLine` preparan el balance anual de ocho columnas desde `BalanceComprobacion` aprobado, fuente oficial/experta y rule set; readiness bloquea procesos sin balance preparado, resumen alineado, lineas activas o revision de warnings, sin declarar calculo final. `AnnualTaxWorkbook`/`AnnualTaxWorkbookLine` y `AnnualEnterpriseRegisterSet`/`AnnualEnterpriseRegisterMovement` preparan RLI/CPT/RAI/SAC/retiros/dividendos con hashes, refs no sensibles y readiness bloqueante si faltan lineas, movimientos, resumen alineado o hay warnings pendientes; conservan `final_tax_calculation=false`. `AnnualRealEstateSection`/`AnnualRealEstateItem` preparan bienes raices/arriendos por propiedad desde Propiedad, DistribucionCobroMensual y ContratoPropiedad, congelan snapshots anuales, cargan contribuciones solo desde fuente oficial/experta trazada cuando existe y bloquean readiness si falta seccion, item activo, fuente/valor de contribuciones, resumen alineado o revision de warnings; tambien conservan `final_tax_calculation=false`. `AnnualTaxDDJJFormLayout` y `AnnualTaxF22ExportLayout` materializan medios/formato revisables antes de la matriz; readiness bloquea formularios DDJJ o layout F22 faltantes, invalidos, con warnings o resumen anual desalineado. `AnnualTaxArtifactMatrix`/`AnnualTaxArtifactMatrixItem` conectan configuracion fiscal, mapeos, source bundle, resumen anual, RLI/CPT, registros, bienes raices, layouts DDJJ y layout F22 hacia destinos DDJJ/F22 revisables, con medio SII, fuente, responsable, hash y payload no sensible; readiness bloquea procesos sin matriz, sin items DDJJ/F22, con resumen desalineado, invalidos, warnings pendientes o items bloqueados, manteniendo `final_tax_calculation=false`. `AnnualTaxExport` queda como preview local con `official_format=false`, `sii_submission=false` y `final_tax_calculation=false`, pero debe enlazar fuente oficial/experta de formato/certificacion F22 y conservar layout F22 en payload/resumen antes de cierre. El dominio SII rechaza F29, ProcesoRentaAnual, DDJJ y F22 en estados aprobados, presentados, observados o rectificados si falta la referencia final trazable correspondiente, y readiness clasifica explicitamente referencias finales sensibles en ProcesoRentaAnual, DDJJ y F22 sin exponer valores. Los eventos anuales `status_updated` de DDJJ/F22 tambien deben conservar `responsable_revision_ref` no sensible cuando avanzan a estados finales de revision; readiness bloquea auditorias heredadas sin responsable o con responsable sensible sin imprimir valores. ProcesoRentaAnual, DDJJ y F22 tambien validan que sus resumenes anuales apunten al ano comercial inmediatamente anterior al `anio_tributario`, y readiness bloquea snapshots heredados con `fiscal_year` desalineado. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel` y `AuthorizationRef` no sensibles. Falta evidencia final con doce cierres/snapshot controlado, regla fiscal validada, certificados/respaldos controlados, dossier revisable y responsable tributario. |
| Reporting | PRD, contabilidad, SII | `backend/reporting`, `backend/core/stage7_reporting_readiness.py`, `scripts/run-stage7-readiness-gate.ps1`, frontend reporting | 7 | parcial | Reportes trazables a ledger/datos/documentos | Resumen financiero mensual exige cierre aprobado y eventos con asiento posteado, balanceado, con movimientos y `hash_integridad` vigente; la API bloquea antes de entregar reporte asientos contabilizados sin hash, con hash desactualizado o sin movimientos contables trazables; ademas expone `control_cierre_mensual` en API y backoffice, unificando por empresa cierre contable, movimientos bancarios no resueltos, banco cuadrado, obligaciones mensuales, F29 cuando aplica y bloqueadores del periodo sin llamar bancos ni SII. Libros por periodo exigen snapshots contables aprobados, balance cuadrado y cierre aprobado, y redactan `storage_ref`/resumen sensibles heredados antes de exponerlos; resumen tributario anual exige proceso/DDJJ/F22 con resumen trazable, `fiscal_year` alineado al ano comercial inmediatamente anterior al `anio_tributario`, `ConfiguracionFiscalEmpresa` activa propia por empresa incluida y DDJJ/F22 asociados al mismo proceso anual, empresa y ano tributario antes de exponer el reporte como verificado; la API bloquea DDJJ/F22 en estados no trazables aunque conserven resumen heredado, bloquea eventos `status_updated` DDJJ/F22 incompletos para documentos incluidos en el reporte, bloquea eventos anuales avanzados sin `responsable_revision_ref` auditado o con responsable sensible, y bloquea `paquete_ref`, `borrador_ref` y payloads anuales sensibles heredados antes de entregar el reporte como valido; `audit_stage7_reporting_readiness` consolida esos origenes mas prueba API, visualizacion backoffice y responsables sin ejecutar smoke publico ni leer datos reales, bloquea procesos/DDJJ/F22 heredados con ejercicio anual desalineado, DDJJ/F22 ligados a proceso de otra empresa/anio, DDJJ/F22 sin estado trazable, payloads anuales sensibles, referencias sensibles y auditorias anuales sin responsable no sensible sin exponer valores. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel` y `AuthorizationRef` no sensibles, reenviados por `run-stage7-readiness-gate.ps1` como `ReportingSourceLabel` y `ReportingAuthorizationRef`. Falta evidencia con cierres/snapshot controlado y datos reales autorizados para cierre final. |
| Migracion legacy | Fuente de verdad, migration README | `migration/`, `scripts/assert-repo-hygiene.ps1` | 1 | parcial | Extractores read-only, clasificacion migrable, contexto sensible externo y bundles no versionados | Inventario metadata/schema-only detecto `.env`, CSV/SQL, Excel/JSON y varias `.db`/`.sqlite3` legacy con esquema compatible de Etapa 1; mientras no haya fuente autorizada, `scripts/run-stage1-local-readiness.ps1` y acceptance verifican preparacion segura con `source_kind=local`, sin solicitar secretos ni simular `snapshot_controlado`, y acceptance tambien verifica que un `snapshot_controlado` vacio falle como `bloqueado_dato_real` con `stage1.data_missing`; `scripts/assert-repo-hygiene.ps1` bloquea regresion de `.env`, DBs, bundles generados, dumps, snapshots, certificados y evidencia local versionada en el root activo; exportador y reportes de migracion rechazan salidas dentro del repo fuera de `migration/bundles/` antes de leer legacy, bundles o DBs; para cierre, autorizar una fuente concreta y validar snapshot/bundle controlado con `scripts/run-stage1-snapshot-gate.ps1`, que exige `SourceLabel`, `AuthorizationRef` y `ResponsibleRef` no sensibles; decidir tratamiento de historial Git/savegames para `BLK-008`. |
| Operacion productiva | Runbooks, gates externos | `backend/health`, `backend/core/operational_observability.py`, `backend/core/models.py`, `backend/core/views.py`, `frontend/src/backoffice/workspaces/OverviewWorkspace.tsx`, `docs/operations`, `scripts/run-postgres-restore-rehearsal.ps1`, `scripts/run-stage7-readiness-gate.ps1`, infra, CI | 7 | parcial | Backup/restore, monitoreo, smoke, rollback, aceptacion | Health/readiness publicos redactan fallas de dependencias; hay rehearsal PostgreSQL local sintetico para preparar backup/restore sin datos reales, y su wrapper rechaza outputs dentro del repo fuera de `local-evidence/` antes de generar plan o tocar Docker; auditoria local de observabilidad agrega gates, integraciones, backlogs y senales runtime, y rechaza outputs dentro del repo fuera de `local-evidence/` antes de auditar; `OperationalRuntimeSignal` permite registrar latencia mensual, cola/tareas, webhooks fallidos y crons fallidos con evidencia y payload no sensibles, normaliza refs/notas runtime antes de validar o persistir, rechaza tambien claves de payload con forma de secreto o credencial, y `record_operational_runtime_signal` imprime stdout redactado sin `evidence_ref`, refs de autorizacion ni payload bruto, pero solo `snapshot_controlado` o `real_autorizado` con `source_label`, `authorization_ref` y observacion dentro de las ultimas 24 horas habilitan cierre productivo; `security.admin_mfa_control` normaliza modo, refs, vigencia y descripcion antes de evaluar el control administrativo; API/backoffice autenticados muestran observabilidad operativa con referencias y valores runtime redactados, y Django admin solo permite inspeccion redactada de senales runtime sin alta, edicion ni borrado manual; el release gate ejecuta readiness local Etapa 7, exige Reporting listo con fuente autorizada, observabilidad runtime autorizada y reciente, restore de backup/snapshot autorizado, smoke publico autorizado y aceptacion final autorizada con referencias no sensibles; para restore y smoke `authorization_ref` debe ser explicito y `responsible_ref` no lo sustituye, y las referencias o payloads sensibles en evidencia de restore/smoke/aceptacion final se clasifican con codigos especificos sin exponer valores. La evidencia de restore no puede usar archivos, rutas, URLs ni ubicaciones crudas como respaldo de cierre, incluyendo aliases como `backup_file`, `backupPath`, `backup_url`, `snapshotPath`, `dumpFile` o `planned_backup_file`; solo cuentan `backup_ref` o `backup_evidence_ref` no sensibles. La salida evidencial del smoke publico mantiene validaciones internas de pantalla, pero no emite usuarios, extractos de pantalla, rutas de screenshot ni errores crudos; solo conserva estado, rol, flujo, resumen operativo, `errorCode` y confirmacion booleana de screenshot, y el release gate rechaza evidencia de smoke con esos campos crudos aunque los roles y refs pasen, incluyendo aliases como `user_name`, `screen_text`, `bodyText`, `screenshot_path`, `screenshot_file`, `screenshotUrl`, `screenshotLocation`, `errorMessage` o `stackTrace`. Confirma que resultados sinteticos/locales, mediciones antiguas, referencias simples o payloads sensibles no cierran Operacion productiva. Falta ejecutar restore con backup/snapshot autorizado, medir senales recientes en ambiente real/controlado, smoke real autorizado, Reporting autorizado y aceptacion final autorizada. |
