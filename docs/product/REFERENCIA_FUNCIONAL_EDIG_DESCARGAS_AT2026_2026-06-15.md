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

## Fuentes verificadas

- Pagina oficial EDIG: `https://edig.cl/descargas/`.
- Notas EDIG Contabilidad: `https://edig.cl/notas-de-versiones-software-contabilidad/`.
- Notas EDIG Renta: `https://edig.cl/notas-version-renta/`.
- Notas EDIG Remuneraciones: `https://edig.cl/notas-versiones-remuneraciones/`.

La pagina de descargas declara instaladores y actualizaciones para:

| Linea EDIG | Descargas observadas |
| --- | --- |
| Contabilidad | instalador, actualizacion `1.0.134`, notas de versiones |
| Renta A.T. 2026 | master Renta 2026, actualizador Renta `1.4`, master F22, actualizacion F22 `1.1`, plantillas/importador E-DJ 2026, notas |
| Remuneraciones | instalador, actualizacion `1.0.222`, notas |

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
- `ediContabilidadVersion134.exe`.
- `PDF Contabilidad + IFRS.pdf`.

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

Senales estaticas de instaladores:

- `PRO26.MDB`, `Reg14.MDB`, `R14PARA26.MDB`.
- `eR14A26`, `eR14D326`, `eR14D826`, `eR14G26`.
- `eRenta26`, `GNPRO26`, `GNDJ26`, `GNF2226`, `ImpDJ26`.
- Reportes y plantillas para RLI, RAI, CPT, F29, F22 y E-DJ.

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
DJ1887/certificados, impuesto unico y centralizacion contable. Un modulo de
remuneraciones completo debe tratarse como frontera separada, con fuente legal
y revision experta, no como deduccion desde EDIG.

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

