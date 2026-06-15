# Referencia funcional EDIG descargas AT2026

Estado: referencia externa no normativa. No contiene binarios EDIG.

## Alcance

Este documento registra el inventario seguro de las descargas EDIG vigentes
revisadas el 2026-06-15 para complementar la referencia previa de Renta AT2026:

- Contabilidad + IFRS.
- Renta A.T. 2026.
- Remuneraciones.

EDIG se usa solo como benchmark funcional. No se copia codigo, no se ejecutan
instaladores, no se versionan binarios, no se usan licencias, datos reales,
RUTs, claves ni certificados, y cualquier ejecucion futura queda limitada al
runbook `docs/operations/EDIG_AT2026_SANDBOX_RUNBOOK.md`.

El usuario consolido posteriormente las tres lineas EDIG completas bajo
`D:\Proyectos\10_ACTIVOS\LeaseManager\EDIG\`, incluyendo Renta AT2026 con
master, actualizaciones y carpetas extraidas. Esa carpeta tambien queda fuera
de Git mediante `.gitignore` y debe tratarse como material externo read-only.

## Fuentes verificadas

- Pagina oficial EDIG: `https://edig.cl/descargas/`.
- Notas EDIG Contabilidad: `https://edig.cl/notas-de-versiones-software-contabilidad/`.
- Notas EDIG Renta: `https://edig.cl/notas-version-renta/`.
- Notas EDIG Remuneraciones: `https://edig.cl/notas-versiones-remuneraciones/`.
- Confirmacion SII F22 AT2026:
  `https://www.sii.cl/noticias/2026/060226noti02pcr.htm`.
- Medios DDJJ Renta 2026:
  `https://www.sii.cl/ayudas/ayudas_por_servicios/2120-medios_dj_renta_2026-2171.html`.
- Casas software DDJJ 2026:
  `https://www.sii.cl/ayudas/ayudas_por_servicios/2120-casas_sw_2026-2171.html`.
- Certificacion F29:
  `https://www.sii.cl/ayudas/ayudas_por_servicios/2055-procesocertificacion-2056.html`.

La pagina de descargas declara instaladores y actualizaciones para:

| Linea EDIG | Descargas observadas |
| --- | --- |
| Contabilidad | instalador, actualizacion `1.0.134`, notas de versiones |
| Renta A.T. 2026 | master Renta 2026, actualizador Renta `1.4`, master F22, actualizacion F22 `1.1`, plantillas/importador E-DJ 2026, notas |
| Remuneraciones | instalador, actualizacion `1.0.222`, notas |

## Contraste oficial SII 2026-06-15

La segunda iteracion posterior al inventario consolidado confirma con SII que
la lectura funcional de EDIG es consistente con el camino oficial, pero no
habilita copiar ni ejecutar EDIG como fuente normativa:

- SII convoco a certificar softwares que generan archivos para Formulario 22
  AT2026. La misma fuente explicita que SII acredita recepcion correcta, pero
  no certifica contenido ni consistencia del F22. Por tanto, el boundary de
  LeaseManager debe conservar `final_tax_calculation=false` y
  `sii_submission=false` hasta revision responsable, formato/certificacion y
  autorizacion.
- La matriz SII de medios DDJJ Renta 2026 muestra que los formularios se
  declaran por combinaciones de formulario electronico, transferencia,
  importador, upload, software comercial y asistentes. Esto valida la capa
  propia `AnnualTaxDDJJFormLayout`.
- SII lista a EDIG como casa software DDJJ 2026 para formularios que tambien
  aparecen en las plantillas locales EDIG, incluyendo 1847, 1879, 1887, 1926,
  1947, 1948 y 1949. Esto confirma que EDIG es un benchmark funcional real
  para DDJJ AT2026, no una fuente de reglas para LeaseManager.
- F29 sigue el patron de upload/certificacion de archivo. Puede alimentar el
  dossier anual como fuente controlada, pero no abre presentacion mensual ni
  anual automatica.
- No se identifico una API REST publica general para F22/DDJJ. El camino seguro
  sigue siendo preparacion local revisable, export/layout certificable si
  corresponde, y presentacion/gate externo supervisado.

## Evidencia externa archivada

Las carpetas descargadas desde el escritorio fueron copiadas, no movidas, a:

`D:\Joaquin Puig\Contabilidad historia\EMPRESAS PUIG\Reorganizacion Contabilidad\99_REFERENCIAS_SOFTWARE_EXTERNO\EDIG_DESCARGAS_2026-06-15`

La copia se verifico con SHA-256 contra el inventario del escritorio:

| Carpeta | Archivos | Tamano aprox. | Hash |
| --- | ---: | ---: | --- |
| `EDIG CONTABILIDAD` | 596 | 271.92 MB | 0 diferencias |
| `EDIG RENTA` | 6 | 488.80 MB | 0 diferencias |
| `EDIG REMUNERACIONES` | 837 | 300.53 MB | 0 diferencias |
| Total | 1439 | 1.04 GB | 0 faltantes, 0 diferencias |

El manifiesto completo queda en la base documental externa como
`desktop-edig-file-inventory.csv`. La evidencia local temporal se genero en
`local-evidence/edig-downloads-2026-06-15/`, ignorada por Git.

## Evidencia local consolidada posterior

El 2026-06-15 se reinvento la carpeta consolidada
`D:\Proyectos\10_ACTIVOS\LeaseManager\EDIG\` desde cero, una linea a la vez,
sin ejecutar software ni instalar componentes. La evidencia local ignorada se
genero en `local-evidence/edig-full-inventory-2026-06-15/`.

| Linea EDIG | Estructura principal observada | Archivos | Tamano aprox. | EXE | MSI | MDB | RPT |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `EDIG CONTABILIDAD` | `Instalador eContabilidad 1.0.71`, `SYSCONT2001 1.0.134`, notas | 1.080 | 621.06 MB | 20 | 1 | 11 | parte de 1.467 globales |
| `EDIG REMUNERACIONES` | `InseRemuneraciones`, `ediRemuneraciones`, notas | 837 | 297.00 MB | 28 | 1 | 11 | parte de 1.467 globales |
| `EDIG RENTA` | `EDIG AT2026 SOFTWARE RENTA`, `ACTUALIZACION`, `ACTUALIZACION 1.1 F22`, `MASTER F22`, anexos E-DJ | 655 | 1.884.27 MB | 64 | 0 | 41 | parte de 1.467 globales |
| Total | tres lineas EDIG completas | 2.572 | 2.802.33 MB | 112 | 2 | 63 | 1.467 |

Ademas se calcularon hashes SHA-256 de artefactos ejecutables/base/archivo
comprimido (`EXE`, `MSI`, `DLL`, `OCX`, `MDB`, `ZIP`, `RAR`) en evidencia local
ignorada. Los archivos EDIG no se versionaron.

La extraccion de esquemas MDB se hizo desde copias temporales y sin leer filas:

| Linea EDIG | MDB analizados | Abiertos | Tablas | Columnas | Lectura funcional |
| --- | ---: | ---: | ---: | ---: | --- |
| Contabilidad | 11 | 11 | 496 | 10.407 | cuentas, libros, F29, balance, reportes, certificados |
| Remuneraciones | 11 | 11 | 586 | 10.343 | trabajadores, liquidaciones, Previred, LRE, DJ1887, centralizacion |
| Renta | 41 | 40 | 867 | 15.304 | F22, DDJJ, regimenes, RLI/CPT/RAI/SAC, F29/PPM, import/export |

El unico MDB no abierto fue un artefacto menor de limpieza (`GNClean.mdb`). No
afecta la lectura funcional porque los MDB principales de Renta (`PRO26`,
`F2226`, `Reg14`, `R14PARA26`, `DDJJAT26`, `F29LGH`) abrieron correctamente.

Los PDFs de Renta/F22/F29/Admin se pudieron convertir a texto con Poppler para
conteos e indices tematicos. Las plantillas XLSX E-DJ AT2026 se inspeccionaron
solo por hojas, dimensiones y muestras estructurales: incluyen formularios y
anexos como 1832, 1835, 1837, 1847, 1862, 1866, 1879, 1887, 1891, 1926 B/C,
1929, 1945, 1946, 1947, 1948, 1949, comunas, paises, monedas, conceptos,
balance de 8 columnas, ajustes tributarios, socios, accionistas y retiros.

Adicionalmente, al detectar que Remuneraciones no conservaba el descargable
original de la actualizacion `1.0.222`, se bajo el enlace oficial EDIG a la
base documental externa como
`DESCARGAS_OFICIALES_PENDIENTES/EDIG_Remuneraciones_Actualizacion_1.0.222_descarga_sharepoint.bin`.
Se dejo extension `.bin` para reducir riesgo de ejecucion accidental. El hash
SHA-256 es `2F5FB8F0B5E3864701C7E4DED6875C9EA125742804E6ED07BCA21FE20FBF401F`
y 7-Zip lo clasifica como instalador MSI/CAB con `Plantilla222.mdb`,
`NEWEMPX222.mdb`, `NEWEMPRE222.MDB` y `REPORTES.mdb`, calzando con la carpeta
`ediRemuneraciones/` ya expandida.

## Clasificacion por linea

### Contabilidad

Artefactos locales relevantes:

- `Instalador eContabilidad 1.0.71/`.
- `SYSCONT2001 1.0.134/`.
- `NOTAS VERSIONES CONTABILIDAD.txt`.

La actualizacion `1.0.134 (15/05/2026)` agrega habilitacion/configuracion de
codigos SII y conceptos de partidas para la DJ1847 del balance de 8 columnas.
Las senales estaticas de 7-Zip y notas cubren balance 8 columnas normal,
oficial e IFRS, libros de compras, ventas, boletas, honorarios, mayor,
certificados, F29 HTML, estados de resultado e informes contables.

Lectura para LeaseManager: Contabilidad debe producir salidas oficiales y
anuales trazables, especialmente balance 8 columnas/DJ1847, como insumo hacia
RLI/CPT. No debe saltar desde asientos directamente a F22.

### Renta A.T. 2026

Artefactos locales relevantes:

- `MRTA2026.exe`: master Renta 2026.
- `ARTA2614.exe`: actualizador Renta `1.4`.
- `MF222610 (1).exe`: master F22.
- `AF222611.exe`: actualizacion F22 `1.1`.
- `Anexo Importador y Formato Plantillas Importacion e-DJ AT 2026.rar`.
- `Notas Versiones.pdf`.

Notas AT2026 extraidas:

- F22 `1.1`: reajuste art. 72 LIR para declaraciones con pago, `1.2%`.
- Master F22 `1.0`: F22 certificado por SII, traspasos desde Regimenes
  Tributarios, Declaraciones Juradas y Proyeccion Renta hacia F22, generacion
  HTML e impresion.
- Renta `1.4`: retiros/dividendos con cargo a ISIF, correccion de importador
  de retiros/remesas/dividendos, eliminacion de oficina virtual para DJ1835.
- Renta `1.3`: DDJJ AT2026 1811, 1822, 1832, 1835, 1837, 1847, 1862, 1866,
  1867, 1870, 1879, 1887, 1891, 1904, 1909, 1926, 1929, 1932, 1943, 1945,
  1946, 1947, 1948, 1949 y 1952; plantillas/anexos E-DJ actualizados; F29
  honorarios AC2026 al `15.25%`.
- Renta `1.2`: ano comercial 2026 y envio por correo F29.
- Renta `1.1`: PPM a tres decimales.
- Renta `1.0`: regimenes con traspaso AT2025, Control de Rentas
  Empresariales, ISIF, Zona Franca/Navarino y Proyeccion Renta/F22.

Senales estaticas de carpetas extraidas:

- `PRO26.MDB`, `Reg14.MDB`, `R14PARA26.MDB`.
- `F2226.MDB`, `DDJJAT26.MDB`, `F29LGH.MDB`, `GnParDJ26.mdb`.
- `eR14A26`, `eR14D326`, `eR14D826`, `eR14G26`.
- `eRenta26`, `GNPRO26`, `GNDJ26`, `GNF2226`, `ImpDJ26`.
- `MASTER F22`, `ACTUALIZACION`, `ACTUALIZACION 1.1 F22`.
- Reportes y plantillas para RLI, RAI, CPT, F29, F22, DDJJ y E-DJ.
- PDFs `f2226.pdf`, `f2225.pdf`, manuales F22/F29/Admin.
- XLSX de importador E-DJ AT2026 y anexos.

Lectura para LeaseManager: Renta anual requiere motor anual versionado por ano
tributario y regimen, con RLI/CPT/RAI/SAC/DDJJ/F22 como capas revisables, no
automatizacion final autonoma.

### Remuneraciones

Artefactos locales relevantes:

- `InseRemuneraciones/`: instalador base historico, incluye
  `eRemuneraciones 1.0.116.msi`.
- `ediRemuneraciones/`: carpeta actualizada con ejecutable 2026 y MDB
  `NEWEMPRE222.MDB`, `NEWEMPX222.mdb`, `Plantilla222.mdb`.
- `PDF.pdf`: notas de versiones.

Comparacion contra la pagina:

- El instalador base esta presente.
- La actualizacion `1.0.222` esta presente como carpeta ya expandida
  `ediRemuneraciones/`.
- El descargable oficial de actualizacion `1.0.222` tambien quedo archivado
  fuera de Git como `.bin` no ejecutado, con hash SHA-256 y listado 7-Zip.

Notas visuales relevantes:

- `1.0.220 (31/12/2025)`: cambios Previred para tipo de trabajador y ajustes
  de remuneracion imponible en gratificaciones.
- `1.0.220 (22/08/2025)`: cotizacion `0.1%`, expectativa de vida, Fondo
  Autonomo de Proteccion Previsional, archivo Previred de 105 campos y
  parametrizacion centralizada.
- `1.0.219 (31/12/2024)`: reliquidaciones Previred y apertura 2025.
- `1.0.218 (05/09/2024)`: regimen previsional SIP/AFP y jubilados/licencia.
- `1.0.217 (23/07/2024)`: Ley 21.330, SIS, licencias, ausentismo y jornada de
  44 horas.
- `1.0.214 (04/03/2024)`: archivo para DJ1887 importador SII.

Senales funcionales:

- Libro de Remuneraciones Electronico.
- Liquidaciones, haberes, descuentos, vacaciones y ausentismo.
- Previred.
- Reliquidaciones y gratificaciones.
- Impuesto unico.
- DJ1887.
- Certificados.
- Centralizacion contable.

Lectura para LeaseManager: Remuneraciones cierra el ciclo contable-tributario
aunque exista un solo trabajador. Para v1 no implica crear un payroll completo
si el alcance no lo requiere; como minimo, el motor anual debe poder recibir
fuentes laborales/previsionales revisables: liquidaciones, LRE, Previred,
DJ1887/certificados, impuesto unico y centralizacion contable. Esa frontera
debe modelarse como fuente anual laboral/previsional importable o revisable,
no como deduccion desde EDIG ni como IA libre. Un modulo de remuneraciones
completo debe tratarse como producto separado, con fuente legal, fuente DT/
Previred/SII vigente y revision experta.

## Decision arquitectonica

EDIG refuerza la arquitectura vigente:

```text
cierres mensuales + ledger + F29/PPM + documentos + patrimonio + socios
  + remuneraciones laborales/previsionales
    -> source bundle anual
    -> normalizador tributario versionado por AT/regimen
    -> RLI/CPT/RAI/SAC/DDJJ/F22/dossier
    -> preview/export local revisable
    -> gate externo SII solo con fuente oficial, formato/certificacion,
       responsable, autorizacion y evidencia
```

No se debe usar EDIG como fuente rectora, ni copiar logica propietaria, ni
presentar F22/DDJJ desde inferencia EDIG. EDIG sirve para validar que
LeaseManager debe producir una capa anual intermedia y un dossier revisable.

## Siguientes paquetes utiles

1. Cruce Remuneraciones -> LeaseManager: matriz de fuentes minimas laborales
   para Stage 6 (`LRE`, `Previred`, `DJ1887`, certificados, centralizacion).
2. Fuente oficial SII/DT/Previred para remuneraciones AT2026 antes de cualquier
   regla.
3. Mapping Contabilidad -> DJ1847 -> RLI/CPT con fuente oficial/experta.
4. Sandbox EDIG solo si se necesita observar flujo interactivo, con VM,
   snapshot, red bloqueada al inicio y datos ficticios.

