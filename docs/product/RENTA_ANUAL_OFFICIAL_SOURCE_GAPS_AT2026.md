# Brechas oficiales Renta Anual AT2026

Estado: matriz operativa de fuentes y limites.

Este documento fija el limite entre preparacion local de LeaseManager y cierre
tributario final. Su objetivo es evitar que la Etapa 6 avance por inferencia,
por EDIG, por automatizacion de navegador o por IA autonoma cuando la evidencia
necesaria es una fuente SII vigente, una certificacion o una revision experta.

Fecha de corte: 2026-06-14.

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
| Instrucciones F22 Renta 2026 | `https://www.sii.cl/servicios_online/renta/guia_trib_suplemento_2026.html` | Fuente para bajar codigos/instrucciones a `TaxCodeMapping` con hash y responsable. |
| Medios DDJJ Renta 2026 | `https://www.sii.cl/ayudas/ayudas_por_servicios/2120-medios_dj_renta_2026-2171.html` | Fuente para determinar medio por formulario: electronico, transferencia, upload, software comercial o asistentes. |
| Formularios y plazos DDJJ AT2026 | `https://www.sii.cl/ayudas/ayudas_por_servicios/2120-formularios_y_plazos_2026-2171.html` | Fuente para instrucciones, certificados, resoluciones, vencimientos y layouts por DDJJ. |
| Casas software DDJJ 2026 | `https://www.sii.cl/ayudas/ayudas_por_servicios/2120-casas_sw_2026-2171.html` | Evidencia de que el camino por archivo certificado existe por formulario, sin entregar logica fiscal. |
| DJ1847 AT2026 | `https://www.sii.cl/ayudas/ayudas_por_servicios/renta/2026/instrucciones_dj1847.pdf` | Fuente prioritaria para balance 8 columnas, clasificador de cuentas, ajustes RLI y valores tributarios de activos/pasivos. |
| Certificacion F29 | `https://www.sii.cl/ayudas/ayudas_por_servicios/2055-procesocertificacion-2056.html` | Fuente para entender archivo/upload F29 y validaciones; F29 alimenta renta, pero su presentacion sigue bajo gate. |

## Brechas por capa EDIG -> LeaseManager -> SII

| Capa | EDIG muestra | LeaseManager ya tiene | Falta para cierre real |
| --- | --- | --- | --- |
| Contribuyente/regimen | Maestros, productos y regimenes por AT. | `Empresa`, `ConfiguracionFiscalEmpresa`, capacidades SII y responsables. | Fuente oficial/experta de regimen aplicable y estado de revision por empresa. |
| F29/PPM | F29 mensual como insumo anual. | Obligaciones mensuales y hechos anuales trazables. | Evidencia controlada de F29/PPM declarado si se usa como credito/fuente final. |
| Balance/RLI/CPT | Capa de balance, RLI, CPT y parametros. | `AnnualTaxWorkbook` RLI/CPT preparatorio. | DJ1847/DJ1926/F22 bajadas a reglas y mapping plan de cuentas. |
| RAI/SAC | Registros empresariales y saldos. | `AnnualEnterpriseRegisterSet` preparatorio. | Saldos historicos, creditos y movimientos con fuente aprobada. |
| Bienes raices | Arriendos, propiedades y contribuciones. | `AnnualRealEstateSection` con warnings y `not_loaded_v1`. | Fuente oficial/experta de contribuciones, creditos y codigos F22. |
| DDJJ | Formularios, certificados y medios. | `AnnualTaxArtifactMatrix` revisable. | Instrucciones/layout/medio por formulario aplicable a LeaseManager. |
| F22 | Preview, plantilla, export/upload. | `AnnualTaxExport` local con `official_format=false`. | Formato/certificacion F22, casos controlados, responsable y autorizacion. |
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
2. `stage6-dj1847-balance-cpt-mapping`: convertir plan de cuentas y balance de
   ocho columnas en fuente trazable para RLI/CPT, sin cerrar calculo final.
3. `stage6-ddjj-official-media-layouts`: declarar formularios DDJJ aplicables,
   medio SII, vencimiento, layout/certificado y campos propios.
4. `stage6-real-estate-official-source`: cargar contribuciones/codigos con
   respaldo SII/experto y mantener warnings hasta aprobacion.
5. `stage6-f22-official-export-format`: evaluar formato/certificacion F22 solo
   con material oficial, casos controlados y autorizacion.
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
