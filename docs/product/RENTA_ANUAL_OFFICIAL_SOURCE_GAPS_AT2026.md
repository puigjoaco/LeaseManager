# Brechas oficiales Renta Anual AT2026

Estado: matriz operativa de fuentes y limites.

Este documento fija el limite entre preparacion local de LeaseManager y cierre
tributario final. Su objetivo es evitar que la Etapa 6 avance por inferencia,
por EDIG, por automatizacion de navegador o por IA autonoma cuando la evidencia
necesaria es una fuente SII vigente, una certificacion o una revision experta.

Fecha de corte: 2026-06-17.

EDIG AT2026 queda como referencia funcional no normativa: permite entender que
un software de renta real separa contribuyente, regimen, contabilidad, F29/PPM,
balance, RLI/CPT, registros empresariales, DDJJ, F22, reportes y upload/export.
No permite copiar reglas, tablas, formulas, formatos, flujos propietarios ni
convertir una coincidencia visual de plantilla en regla LeaseManager.

## Lectura ejecutiva

LeaseManager v1 puede mecanizar fuentes, hechos mensuales, RLI/CPT, registros
empresariales, bienes raices, DDJJ/F22 revisables, dossier y export local. No
debe decidir ni presentar renta final de forma autonoma.

Las fuentes SII revisadas muestran tres familias distintas:

| Familia | Lectura | Tratamiento LeaseManager |
| --- | --- | --- |
| DTE | Existen instructivos, web services y documentacion tecnica para factura/boleta electronica, sujetos a certificado digital y gates. | Integracion tecnica posible bajo Etapa 4, no prueba API F22/DDJJ. |
| F29/DDJJ/F22 | El camino oficial visible es formato, upload, medios por formulario, certificacion y revision responsable. | Preparar paquete/export revisable; no presentar ni marcar formato oficial sin gate. |
| Criterio tributario | Las instrucciones F22/DJ y reglas por regimen requieren interpretacion y responsabilidad. | Versionar fuentes y warnings; el cierre exige responsable experto/oficial. |

## Confirmacion SII posterior al mapeo EDIG

La iteracion del 2026-06-17 contra fuentes oficiales SII confirma que el
mapeo EDIG va en la direccion correcta, pero no cambia el boundary:

- F22 AT2026 se maneja como proceso de certificacion de software que genera
  archivos para Declaracion Anual. SII acredita recepcion correcta de los
  archivos enviados, pero no certifica contenido ni consistencia tributaria del
  Formulario 22. LeaseManager puede preparar layout/export revisable, no
  declarar calculo final autonomo.
- DDJJ Renta 2026 tiene matriz oficial de medios por formulario: formulario
  electronico, transferencia de archivos/importador, upload, software comercial
  y asistentes. El hecho de que un formulario admita software comercial obliga
  a modelar `AnnualTaxDDJJFormLayout`; no autoriza copiar plantillas EDIG ni
  presentar sin certificacion/responsable.
- La lista SII de casas software DDJJ 2026 incluye a EDIG para formularios
  relevantes del mapeo local, entre ellos 1847, 1879, 1887, 1926, 1947, 1948 y
  1949. Esto confirma a EDIG como benchmark funcional de DDJJ, no como fuente
  normativa ni como prueba de una API F22/DDJJ publica.
- El subdominio oficial `alerce.sii.cl` publica ayudas de autoverificacion y
  manual de importador DDJJ. Esto confirma caminos de revision/importacion por
  archivo, no una API REST general ni una autorizacion para presentar desde el
  core de LeaseManager.
- La pregunta frecuente SII de F22 sin propuesta mantiene caminos de
  formulario en pantalla, recuperacion de datos guardados o software comercial.
  Es consistente con el boundary de portal supervisado o archivo certificado,
  no con presentacion autonoma por API.
- La ayuda oficial `Formato de Registro F22 AT2026` publica registros
  fixed-width de largo 90 para F22: registro tipo 0 de cabecera/datos para
  internet y registro tipo 1 de datos de declaracion con cuatro codigos por
  registro. Esto permite construir un contrato local verificable de archivo
  candidato, no una presentacion SII ni calculo tributario final.
- F29 confirma el mismo patron: upload/certificacion de archivo, validacion en
  sitio SII y responsabilidad de la casa de software por contenido,
  consistencia y validaciones. Por eso F29 debe entrar al dossier anual como
  fuente trazable controlada, no como presentacion automatica.
- No se identifico una API REST general oficial para presentar F22/DDJJ desde
  LeaseManager. El camino seguro sigue siendo archivo/layout certificado,
  portal/upload supervisado o integracion formal futura bajo gate.

`backend/core/stage6_official_compatibility.py` baja esta lectura a una matriz
testeable de compatibilidad AT2026. La matriz conserva
`public_api_general_available=false`, `official_submission_allowed=false` y
`final_tax_calculation=false`; cualquier cambio que intente habilitar API,
presentacion oficial o calculo final debe fallar en tests hasta tener fuente,
certificacion, autorizacion y responsable.

## Matriz de brechas

| Capacidad | Fuente oficial o estado | Estado v1 | Accion segura |
| --- | --- | --- | --- |
| DTE y documentos electronicos | Instructivo tecnico DTE y servicios de factura electronica. | `external_gate_required` | Mantener en gate DTE con certificado, CAF, auditoria y rollback. |
| F29 mensual | Proceso de certificacion para declarar F29 por software, archivo/upload y validaciones. | `preparation_allowed_submission_blocked` | Usar como fuente anual trazable solo con evidencia/control autorizado. |
| DDJJ Renta 2026 | Medios por formulario: formulario electronico, transferencia, upload, software comercial y asistentes. | `media_matrix_required` | Construir matriz DDJJ aplicable por formulario antes de cualquier export oficial. |
| DJ1847, balance, RLI y CPT | Instrucciones SII DJ1847 AT2026. | `official_mapping_required` | Mapear plan de cuentas -> RLI/CPT/DJ1847 solo con fuente oficial/experta. |
| F22 Renta anual | Certificacion AT2026 para software que genera archivos F22. | `local_export_only` | Mantener `AnnualTaxExport` como preview local hasta certificacion/formato/autorizacion. |
| Instrucciones F22 2026 | Guia/Suplemento tributario Renta 2026. | `review_source_required` | Referenciar codigos e instrucciones como fuente, no como calculo autonomo final. |
| Bienes raices, arriendos y contribuciones | Fuente oficial/experta pendiente. | `source_gap` | Mantener warnings y `not_loaded_v1` hasta respaldo aprobado. |
| Automatizacion por navegador SII | No hay API REST general F22/DDJJ identificada en fuentes verificadas. | `last_resort_supervised` | Solo asistencia supervisada con runbook, datos controlados y autorizacion explicita. |

## Consecuencia de arquitectura

El core de LeaseManager debe terminar la Etapa 6 en un paquete revisable:

```text
fuentes anuales trazables
  -> normalizacion mensual y anual
  -> RLI/CPT/RAI/SAC/DDJJ/F22 revisables
  -> dossier y export local hasheado
  -> revision responsable / IA asistida fuera del core automatico
  -> gate SII o ejecucion manual controlada
```

La IA puede asistir analisis, explicacion, conciliacion de instrucciones y
prellenado supervisado. No reemplaza al responsable tributario ni convierte
un export local en presentacion oficial.

## Fuentes SII AT2026 verificadas

| Fuente | URL | Uso correcto |
| --- | --- | --- |
| Certificacion F22 AT2026 | `https://www.sii.cl/noticias/2026/060226noti02pcr.htm` | Probar que existe camino de archivo/certificacion F22 2026; no prueba consistencia tributaria del contenido. |
| Formato de Registro F22 AT2026 | `https://alerce.sii.cl/dior/ren_mp/pdf/6_Formato_de_Registro_F22_AT2026.pdf` | Fuente exacta para contrato fixed-width local: registros tipo 0 y tipo 1 de largo 90. |
| Instrucciones F22 Renta 2026 | `https://www.sii.cl/servicios_online/renta/guia_trib_suplemento_2026.html` | Fuente para bajar codigos/instrucciones a `TaxCodeMapping` con hash y responsable. |
| Medios DDJJ Renta 2026 | `https://www.sii.cl/ayudas/ayudas_por_servicios/2120-medios_dj_renta_2026-2171.html` | Fuente para determinar medio por formulario: electronico, transferencia, upload, software comercial o asistentes. |
| Formularios y plazos DDJJ AT2026 | `https://www.sii.cl/ayudas/ayudas_por_servicios/2120-formularios_y_plazos_2026-2171.html` | Fuente para instrucciones, certificados, resoluciones, vencimientos y layouts por DDJJ. |
| Casas software DDJJ 2026 | `https://www.sii.cl/ayudas/ayudas_por_servicios/2120-casas_sw_2026-2171.html` | Evidencia de que el camino por archivo certificado existe por formulario, sin entregar logica fiscal. |
| Autoverificacion DDJJ AT2026 | `https://alerce.sii.cl/dior/dej/html/dj_autoverificacion.html` | Evidencia de ayudas SII para revision de archivos DDJJ; no certifica contenido tributario. |
| Manual importador DDJJ | `https://alerce.sii.cl/dior/dej/html/manual/DJ_Manual/01.html` | Evidencia de flujo de importador/archivo DDJJ; no prueba API REST general. |
| Opciones declaracion F22 sin propuesta | `https://www.sii.cl/preguntas_frecuentes/declaracion_renta/001_140_8395.htm` | Evidencia de formulario web, datos guardados o software comercial; no habilita automatizacion autonoma. |
| DJ1847 AT2026 | `https://www.sii.cl/ayudas/ayudas_por_servicios/renta/2026/instrucciones_dj1847.pdf` | Fuente prioritaria para balance 8 columnas, clasificador de cuentas, ajustes RLI y valores tributarios de activos/pasivos. |
| Certificacion F29 | `https://www.sii.cl/ayudas/ayudas_por_servicios/2055-procesocertificacion-2056.html` | Fuente para entender archivo/upload F29 y validaciones; F29 alimenta renta, pero su presentacion sigue bajo gate. |

## Decision sobre ejecutar EDIG

Con la evidencia estatica actual no es necesario ejecutar EDIG para avanzar la
arquitectura ni la implementacion propia. Ya estan cubiertos:

- instaladores y actualizaciones por linea;
- notas de version;
- esquemas MDB sin filas;
- manuales PDF F22/F29/Admin;
- plantillas XLSX E-DJ;
- reportes RPT;
- contraste oficial SII sobre F22, F29, DDJJ y casas software.

Ejecutar binarios EDIG solo seria util si falta observar comportamiento
interactivo que no pueda inferirse de fuentes estaticas, por ejemplo nombres de
archivos generados, secuencia exacta de pantallas, mensajes de validacion o
estructura de salida con datos ficticios. Esa ejecucion no puede ocurrir en el
root de desarrollo ni con datos reales; debe seguir el runbook sandbox y no
puede usarse para copiar reglas, formulas, tablas propietarias o formatos
finales.

## Brechas por capa EDIG -> LeaseManager -> SII

| Capa | EDIG muestra | LeaseManager ya tiene | Falta para cierre real |
| --- | --- | --- | --- |
| Contribuyente/regimen | Maestros, productos y regimenes por AT. | `Empresa`, `ConfiguracionFiscalEmpresa`, capacidades SII y responsables. | Fuente oficial/experta de regimen aplicable y estado de revision por empresa. |
| F29/PPM | F29 mensual como insumo anual. | Obligaciones mensuales y hechos anuales trazables. | Evidencia controlada de F29/PPM declarado si se usa como credito/fuente final. |
| Balance/RLI/CPT | Capa de balance, RLI, CPT y parametros. | `AnnualTaxTrialBalance` + `AnnualTaxWorkbook` RLI/CPT preparatorio. | Fuente DJ1847/DJ1926/F22 revisada por responsable para promover mappings desde preparacion a cierre. |
| RAI/SAC | Registros empresariales y saldos. | `AnnualEnterpriseRegisterSet` preparatorio. | Saldos historicos, creditos y movimientos con fuente aprobada. |
| Bienes raices | Arriendos, propiedades y contribuciones. | `AnnualRealEstateSection` enlaza fuente de contribuciones y valores por propiedad cuando existen; conserva warnings si falta fuente o valor. | Fuente oficial/experta de contribuciones, creditos y codigos F22 para cierre final. |
| DDJJ | Formularios, certificados y medios. | `AnnualTaxDDJJFormLayout` + `AnnualTaxArtifactMatrix` revisables. | Fuente oficial/experta y revision responsable para promover layout/medio a cierre real. |
| F22 | Preview, plantilla, export/upload. | `AnnualTaxF22ExportLayout` + `AnnualTaxExport` local con `official_format=false`. | Formato/certificacion F22 oficial/certificable, casos controlados, responsable y autorizacion para promover a cierre real. |
| Dossier | Reportes y respaldos. | `AnnualTaxDossier` hasheado y revisable. | Checklist tributario anual y aprobacion responsable. |

## Desbloqueos necesarios

- `TaxYearRuleSet` final: fuente SII/experta, version, hash, vigencia y
  responsable.
- `TaxCodeMapping` final: codigo F22/DDJJ, origen, formula, signo, validacion,
  evidencia y responsable.
- DJ1847/RLI/CPT: instrucciones oficiales aplicadas a plan de cuentas y balance
  de ocho columnas.
- Bienes raices/contribuciones: respaldo oficial o experto para montos,
  creditos y codigos.
- DDJJ: matriz por formulario y medio SII vigente.
- F22/export: certificacion/formato oficial vigente si se decide producir
  archivo certificable.
- Presentacion: autorizacion explicita, usuario/responsable, ambiente, rollback
  y evidencia no sensible.

## Orden de avance recomendado

1. `stage6-official-tax-source-registry`: modelo/documento para registrar
   fuente oficial AT2026 por documento, hash, fecha, formulario/codigo/regimen,
   alcance, responsable y estado de revision.
2. `stage6-dj1847-balance-cpt-mapping`: materializado como
   `AnnualTaxTrialBalance`/lineas y conexion de workbooks RLI/CPT a metricas
   del balance de ocho columnas. Sigue siendo preparacion revisable; no cierra
   calculo final ni presentacion.
3. `stage6-ddjj-official-media-layouts`: materializado como
   `AnnualTaxDDJJFormLayout`; declara formularios DDJJ aplicables, medios SII,
   vencimiento, layout/certificado, fuente oficial/experta y campos propios,
   alimentando la matriz DDJJ/F22 sin producir formato oficial ni presentacion.
4. `stage6-real-estate-official-source`: materializado como enlace de
   `AnnualRealEstateSection` a `AnnualTaxOfficialSource` de contribuciones o
   revision experta F22/Dossier, mas `values_by_property_id` en el bundle
   anual; mantiene warnings cuando falta fuente o monto por propiedad.
5. `stage6-f22-official-export-format`: materializado como
   `AnnualTaxF22ExportLayout`; declara formato/certificacion/instrucciones F22
   revisables, fuente oficial/experta, medio preferente, hash y boundary
   explicito, alimentando la matriz DDJJ/F22 y el export local sin producir
   presentacion SII ni calculo tributario final.
6. `stage6-annual-review-checklist`: materializado como
   `AnnualTaxReviewChecklist` para exigir revision responsable por regimen,
   evidencia no sensible y frontera explicita antes de tratar cualquier
   dossier/export anual como revisado.

## Herramienta local

`scripts/build-stage6-official-source-gap-matrix.ps1` genera una matriz local
ignorada bajo `local-evidence/stage6/official-source-gaps/`. No consulta SII,
no usa credenciales, no lee `.env`, no ejecuta EDIG, no abre navegador y no
produce archivos oficiales.

```powershell
scripts\build-stage6-official-source-gap-matrix.ps1
```

La salida sirve como evidencia operativa para decidir el proximo paquete sin
volver a debatir si LeaseManager debe "hacer la renta" de forma autonoma: no
debe. Debe preparar la informacion y dejar el cierre final bajo revision y
gate.

`AnnualTaxOfficialSource` es el registro vivo para bajar esta matriz al
sistema: cada fuente oficial/experta que se use en reglas, mappings, DDJJ, F22
o dossier debe quedar con ano tributario, tipo, URL publica SII segura si
aplica, referencia no sensible, hash, fecha de recuperacion, responsable y
alcance. El registro no guarda documentos SII, credenciales, sesiones ni
valores tributarios finales; solo prueba que una regla o mapping tiene respaldo
trazable.

`AnnualTaxTrialBalance` baja la brecha DJ1847/RLI/CPT a una capa operativa
propia: toma balance contable aprobado, clasificador por cuenta y fuente
oficial/experta revisada para preparar montos trazables. No convierte el
balance en declaracion de renta; cualquier warning de clasificacion, fuente o
criterio mantiene el cierre bajo revision responsable.

Los `TaxCodeMapping` que consumen `annual_trial_balance.*` deben declarar
`trial_balance_classifier` DJ1847 y solo alimentar RLI/CPT. Si un mapping
heredado intenta saltar desde balance anual directo a F22/DDJJ/RAI/SAC o no
trae clasificador, readiness lo bloquea como brecha de fuente/mapping oficial.
Esto mantiene la union contabilidad -> renta dentro de la capa intermedia
DJ1847/RLI/CPT antes de cualquier dossier, DDJJ o F22.

`AnnualTaxDDJJFormLayout` baja la brecha de medios/formularios DDJJ a una capa
operativa propia: una fila por ano tributario y formulario conserva medios SII
permitidos, medio preferente, vencimientos, certificado, resolucion, refs de
layout/instrucciones/responsable, fuentes oficiales/expertas y hash. Esa capa
alimenta `AnnualTaxArtifactMatrix` como preparacion revisable, sin archivo
oficial, sin upload SII y sin decision tributaria final.

`AnnualRealEstateSection.official_contribution_source` baja la brecha de
contribuciones/codigos F22 a una referencia auditable: solo acepta fuente SII
de bienes raices/contribuciones o revision experta con alcance F22/Dossier y
metadata `real_estate_contributions=true`. Los montos controlados viajan en
`AnnualTaxSourceBundle.resumen_fuentes.real_estate_contribuciones.values_by_property_id`.
Si falta fuente, el item conserva `contribuciones_source_not_loaded_v1`; si
falta monto por propiedad, conserva `contribuciones_value_not_loaded_v1`.
Readiness impide tratar la seccion como cerrable en ambos casos.

`AnnualTaxF22ExportLayout` baja la brecha de formato/certificacion F22 a una
capa operativa propia: una fila por ano tributario conserva `form_code=F22`,
medio preferente, refs de certificacion/formato/instrucciones/responsable,
fuentes oficiales/expertas, warnings, payload no sensible y hash. Esa capa
alimenta `AnnualTaxArtifactMatrix`, `AnnualTaxDossier`, `AnnualTaxExport` y
`AnnualTaxReviewChecklist` como preparacion revisable, sin archivo oficial,
sin upload SII, sin presentacion autonoma y sin decision tributaria final.

`build_stage6_official_compatibility_matrix()` consolida la lectura oficial
AT2026 para F22 y DDJJ en codigo: certificacion F22, instrucciones F22,
opciones de portal/software comercial, medios DDJJ, formularios/plazos,
casas software DDJJ, autoverificacion e importador. Su validador rechaza URLs
fuera de dominios SII publicos, API asumida sin evidencia, presentacion oficial
habilitada, calculo final autonomo o certificacion de consistencia tributaria
por el solo hecho de existir un gate tecnico de archivo.

`build_f22_record_format_contract()` baja la fuente `Formato de Registro F22
AT2026` a un contrato local exacto para registros fixed-width de 90 caracteres:
tipo 0 para cabecera/datos de internet y tipo 1 para datos de declaracion en
cuatro pares codigo/signo/valor por linea. `build_f22_type0_record()` y
`build_f22_type1_record()` generan registros candidatos con datos sinteticos o
controlados, y `validate_f22_fixed_width_record()` rechaza largo, tipo,
constantes, posiciones y campos numericos invalidos. Esta capa sigue con
`official_submission_allowed=false` y `final_tax_calculation=false`.

`build_annual_tax_f22_fixed_width_export_candidate()` usa ese contrato desde un
`AnnualTaxExport` preparado para escribir un candidato F22 fixed-width local
solo cuando recibe entradas revisadas explicitamente con codigos SII numericos
de cuatro digitos y valores. `write_annual_tax_f22_fixed_width_export_candidate()`
preserva bytes ASCII exactos y
`verify_annual_tax_f22_fixed_width_export_candidate()` reabre archivo y
manifest desde disco para validar hash, tamano, largos y registros. La capa
rechaza codigos internos no numericos como `F22-PREVIEW`, no presenta SII, no
usa codigo de certificacion real y no declara calculo tributario final.
Ademas, cada entrada F22 fixed-width debe conservar evidencia no sensible por
linea: estado `approved_for_candidate`, fuente del codigo, fuente del valor y
responsable revisor. El manifest hashea esa evidencia y el verificador bloquea
duplicados, refs sensibles o evidencia alterada; esto acerca el archivo local a
un dossier revisable/certificable sin convertirlo en presentacion oficial.
`build_f22_fixed_width_entries_from_artifact_matrix()` conecta esa exigencia
con la matriz anual: solo deriva entradas desde items activos `F22` originados
en `TaxCodeMapping` del mismo rule set del export, con fuente oficial/experta
lista y metadata revisada para valor/signo/evidencia. Asi el valor candidato ya
no entra como lista manual aislada, sino como salida trazada desde la capa
tributaria intermedia. La brecha externa sigue abierta: esto no sustituye
certificacion SII, codigo de software, validacion tributaria experta ni envio
oficial.
