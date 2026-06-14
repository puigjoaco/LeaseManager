# Mapeo EDIG AT2026 para Renta Anual LeaseManager

Estado: referencia local no normativa.

Este documento traduce el analisis del software EDIG AT2026 instalado en
`EDIG AT2026 SOFTWARE RENTA/` a una matriz implementable para LeaseManager. EDIG
es material externo read-only: no se copia codigo, no se versionan binarios, no
se usan licencias, RUTs, claves, certificados ni datos reales, y cualquier
ejecucion queda limitada al runbook de sandbox.

## Hallazgo central

EDIG une contabilidad y renta mediante una capa tributaria intermedia. No se
observa un flujo sano de "asiento contable directo a F22". El patron visible es:

1. Administrar contribuyentes, usuarios, productos y licencias.
2. Seleccionar regimen tributario anual.
3. Importar o capturar datos contables, balance, socios, retiros, dividendos,
   F29/PPM, certificados y datos patrimoniales.
4. Construir registros tributarios: RLI, CPT, RAI, SAC, registros de rentas,
   DDJJ y respaldos.
5. Mapear resultados a codigos F22/DDJJ.
6. Validar contra reglas/formato del ano tributario.
7. Generar HTML, reportes, archivo de upload/export y estado de declaracion.

LeaseManager debe replicar ese patron conceptual con reglas propias, fuentes
oficiales y trazabilidad propia. No debe depender de EDIG ni reproducir logica
propietaria.

## Inventario interpretado

| Area EDIG observada | Evidencia local | Interpretacion | Equivalente LeaseManager |
| --- | --- | --- | --- |
| Administracion central | `BIN/admin26.exe`, `CENTRAL/comun.MDB`, campos `tblContribuyente`, `tblUser`, `nDetRenta`, `nEF22`, `nEF29` | Maestro de contribuyentes, usuarios, productos y estado de modulos | `Empresa`, `ConfiguracionFiscalEmpresa`, capacidades SII, responsables y auditoria |
| Launcher tributario | `BIN/eRenta26.exe` referencia `e-Formulario 22`, `e-Formulario 29`, `eR14A26`, `eR14D326`, `eR14D826`, `eR14G26` | Familia de aplicaciones por formulario/regimen | Modulos internos por dominio: mensual, anual, regimen y reporting |
| Formulario 22 | `BIN/GNPRO26.EXE`, `CENTRAL/PlantillaPRO_26.htm`, `compactoPRO_26.htm` | Generacion/revision F22, HTML, upload y estado de declaracion | `F22PreparacionAnual`, preview, resumen, ref final, responsable y export certificable |
| Regimen 14A | `BIN/eR14A26.exe`, reportes `Rep_RLI14A26`, `Rep_CPT_14A26`, tokens RLI/CPT/RAI/SAC | Motor de regimen semi integrado | Motor `ATYYYY.Regimen14A` solo si se valida fuente oficial/experta |
| Regimen 14D3 | `BIN/eR14D326.exe`, reportes `Rep_RLID326`, `Rep_Ctrl14D326` | Motor ProPyme general | Motor `ATYYYY.Regimen14D3` |
| Regimen 14D8 | `BIN/eR14D826.exe`, reporte `Rep_RLID826` | Motor ProPyme transparente | Motor `ATYYYY.Regimen14D8` |
| Regimen 14G | `BIN/eR14G26.exe`, reporte `Rep_RLI14G26` | Motor organizaciones sin fines de lucro | Motor `ATYYYY.Regimen14G`, fuera de v1 salvo ADR/gate |
| Parametria tributaria | `CENTRAL/R14PARA26.MDB`, tokens `tblParam_CodDJ`, `tblParam_ItmRLI`, `tblParam_CodRzCPT` | Parametros de codigos, items RLI, DDJJ, CPT por AT/regimen | Tablas versionadas `TaxRuleSet`, `TaxCodeMapping`, `AnnualTaxFormula` |
| Datos de proceso F22 | `DATOS/PRO26.MDB`, tokens `TblADOBieRaiz`, `PROYContabCompleta`, `cCertificado`, `RLI`, codigos F22 | Storage anual de F22/proyeccion/certificados | `ProcesoRentaAnual.resumen_anual`, `F22PreparacionAnual.resumen_f22` |
| Registros 14 | `DATOS/Reg14.MDB`, tokens `tblReg_RLITotal`, `tblReg_RLIDeta`, `tblReg_CPTTotal`, `ndMonRAI`, `ndSAC_*` | Capa intermedia RLI/CPT/RAI/SAC | Normalizador anual tributario LeaseManager |
| F29/PPM mensual | `DATOS/F29LGH.MDB`, `BIN/IVASTD26.EXE`, plantillas `PlantillaF29_*.htm` | F29, IVA, retenciones, PPM y arrastres alimentan renta | `F29PreparacionMensual`, obligaciones mensuales y cierres aprobados |
| Plantillas visuales | `#fld####` en `PlantillaPRO_26.htm`; `$Fld###$` en F29 | Render separado de calculo | Render/preview anual separado del motor de calculo |
| Reportes de respaldo | `DATOS/*.rpt` RLI, RAI, CPT, PPUA, Control 14A/14D3, SAC | Evidencia contable-tributaria revisable | PDFs canonicos y dossier anual con hash/traza |
| Conectividad | `WS/WAppConnect*`, metodos folios, DTE, PDF, UTM, licencias, certificados | Servicios auxiliares; no prueba API F22 | Mantener SII separado por capacidad/gate |

## Matriz implementable

| Flujo | Entrada requerida | Capa intermedia | Salida LeaseManager | Brecha actual |
| --- | --- | --- | --- | --- |
| Contribuyente anual | Empresa, regimen, giro, configuracion fiscal activa, representante/responsable | Perfil tributario anual | Proceso de renta creado con responsable y source trace | Falta matriz fiscal AT por regimen |
| Cierre mensual a renta | 12 cierres aprobados, ledger balanceado, F29/PPM, evidencias no sensibles | Agregador anual de obligaciones | Base anual revisable | Requiere normalizador tributario anual |
| Balance a CPT | Cuentas contables, saldos, ajustes tributarios, activos/pasivos/patrimonio | CPT positivo/negativo, razonabilidad CPT | Seccion CPT/RAI y respaldo PDF | Falta mapping plan de cuentas -> item CPT y DJ 1847 |
| Resultado a RLI | Ingresos, gastos aceptados/rechazados, agregados, deducciones, correcciones | RLI por regimen | RLI trazada y respaldo | Falta catalogo de ajustes AT/versionado |
| RAI/SAC | RLI, CPT, retiros/dividendos, creditos, saldos historicos | RAI, SAC, registros empresariales | Registro de rentas y creditos | Falta modelo anual de saldos empresariales |
| Arriendos y bienes raices | Contratos, pagos, propiedades, contribuciones, reajustes, certificados | Rentas de bienes raices y creditos | Codigos F22 de arriendos/contribuciones | LeaseManager tiene datos base; falta mapping F22 oficial |
| DDJJ | Socios, participaciones, retiros, dividendos, rentas, certificados | Paquetes DDJJ por formulario | `DDJJPreparacionAnual` con resumen y ref | Falta matriz DDJJ 2026 por medio/formato |
| F22 | Todos los componentes anteriores | Codigos F22 versionados | `F22PreparacionAnual`, preview y export | Falta formato/certificacion SII vigente |
| Validacion | Reglas oficiales, set de validaciones, casos de prueba | Validador por AT y regimen | Readiness anual y errores por codigo | Falta fuente oficial/casa software/certificacion |
| Presentacion | Archivo certificable, responsable, autorizacion y ambiente SII | Gate externo | Presentacion manual/controlada o podada | Sigue bloqueada sin certificacion y autorizacion |

## Cobertura estatica extendida

`scripts/analyze-edig-at2026.ps1` genera una matriz local ignorada en
`local-evidence/` con senales funcionales por area tributaria. La corrida local
read-only sobre EDIG AT2026 detecto cobertura para administracion de
contribuyentes, F22, F29/PPM, regimenes 14A/14D3/14D8/14G, RLI, CPT, RAI,
SAC, DDJJ, balance/contabilidad, bienes raices/arriendos, reportes/respaldo,
upload/export y conectividad auxiliar.

La matriz no copia reglas ni formulas EDIG. Solo clasifica nombres de artefactos
seguros, metadata de ejecutables, plantillas, reportes y tokens estructurales
filtrados de MDB nucleo. Las raices `CONTRIB/`, `LICENCIAS/`, `RESPUESTA/` y
`UPLOAD/` se excluyen o redactan para evitar arrastrar datos de usuario,
licencia o salidas de presentacion.

La lectura mas importante para LeaseManager es de diseno: EDIG evidencia una
separacion entre entrada contable, parametria por regimen, registros
intermedios y render/export. Por eso el motor propio debe avanzar por:

1. perfil tributario anual;
2. normalizador desde cierres/F29/ledger;
3. RLI/CPT/RAI/SAC y registros empresariales;
4. DDJJ/certificados;
5. F22 preview/export;
6. gate de presentacion externa.

## Linea de diseno propia

LeaseManager debe implementar un motor anual por ano tributario con estas
piezas minimas:

- `TaxYearRuleSet`: version, fuente oficial/experta, regimenes soportados,
  vigencia, hash documental y estado de aprobacion.
- `TaxCodeMapping`: codigo F22/DDJJ, descripcion, formula, fuente de dato,
  dependencia, signo, redondeo, validacion y responsable de aprobacion.
- `AnnualTaxNormalizer`: toma cierres, ledger, F29, patrimonio, contratos,
  certificados y socios; produce RLI/CPT/RAI/SAC/DDJJ/F22 intermedios.
- `AnnualTaxDossier`: respalda cada valor con origen, evidencia, calculo,
  warnings, responsable y estado.
- `AnnualTaxExport`: genera preview/archivo solo cuando existe formato oficial
  o certificacion aplicable.

## Fuentes oficiales verificadas

- F22: el SII invita a empresas de software a certificarse para generar
  archivos de declaracion anual Formulario 22 por Internet.
  `https://www.sii.cl/noticias/2025/120225noti01aav.htm`
- F29: el proceso Upload carga archivo, despliega el formulario, recalcula
  totalizadores y valida con set de validaciones.
  `https://www.sii.cl/ayudas/ayudas_por_servicios/2055-procesocertificacion-2056.html`
- DDJJ 2026: el SII publica medios disponibles por formulario, incluyendo
  transferencia, upload, importador y software comercial segun formulario.
  `https://www.sii.cl/ayudas/ayudas_por_servicios/2120-medios_dj_renta_2026-2171.html`
- DJ 1847 AT2026: las instrucciones SII piden informar el balance de ocho
  columnas, clasificacion de cuentas, ajustes para determinar RLI y valor
  tributario de activos/pasivos para CPT.
  `https://www.sii.cl/ayudas/ayudas_por_servicios/renta/2026/instrucciones_dj1847.pdf`

Estas fuentes prueban el camino archivo/upload/certificacion. No prueban una API
REST publica para presentar F22; por defecto ese camino queda bloqueado hasta
documento oficial vigente.

## Proximos paquetes tecnicos

1. `stage6-tax-mapping-foundation`: modelos o fixtures de regla versionada por
   ano tributario, sin formulas fiscales finales.
2. `stage6-annual-normalizer-readiness`: normalizador anual que arma estructura
   RLI/CPT/RAI/SAC vacia/trazada desde cierres y ledger controlados.
3. `stage6-real-estate-f22-mapping`: mapping oficial de arriendos, bienes
   raices y contribuciones a codigos F22 cuando exista fuente oficial/experta.
4. `stage6-ddjj-media-matrix`: matriz DDJJ aplicable a LeaseManager con medio
   SII permitido, datos requeridos y gate.
5. `stage6-export-gate`: export/preview controlado, sin presentacion final.

## Reglas de seguridad

- EDIG no se ejecuta en el root activo.
- Los MDB se analizan desde copias temporales.
- Las tablas o tokens de usuario/licencia se excluyen o redactan.
- No se versionan salidas de analisis, capturas, HTML generados ni archivos de
  upload.
- Ninguna inferencia desde EDIG se convierte en regla fiscal sin SII, normativa
  vigente o responsable experto.
