# Auditoria de autosuficiencia del set activo

Estado: vigente  
Fecha: 15/03/2026  
Objetivo: demostrar que el set activo de LeaseManager puede implementarse sin depender de backlog abierto para el boundary activo del v1

## 1. Resultado

El set activo queda compuesto por:

- [PRD_CANONICO.md](./PRD_CANONICO.md)
- [MATRIZ_GATES_EXTERNOS.md](./MATRIZ_GATES_EXTERNOS.md)
- `ADR_ARQUITECTURA_001`, `002`, `003`, `004`, `005`, `006` y `008`
- [BACKLOG_INVESTIGACION.md](./BACKLOG_INVESTIGACION.md) solo para expansiones futuras fuera del boundary activo

El core del v1 ya no depende de items abiertos para:

- regimen tributario soportado;
- ownership operativo;
- plan de cuentas base;
- reglas contables minimas;
- politica de reversos;
- politica de firma y notaria;
- politica de retencion y exportacion;
- capacidades SII mensuales y anuales dentro del boundary activo.

## 2. Cierres explicitamente resueltos

| Tema antes abierto | Resolucion final | Artefacto de cierre |
|---|---|---|
| policy contractual mensual | se confirma como `Policy v1` de segmentacion del producto | `PRD_CANONICO` |
| ownership entre propietario, operador y facturador | se cierra via `MandatoOperacion` con autorizaciones explicitas | `PRD_CANONICO` |
| politica de retencion/exportacion | se define `PoliticaRetencionDatos` con minimos y hold | `PRD_CANONICO` |
| politica de firma/notaria | se define `PoliticaFirmaYNotaria` y no se asume notaria universal | `PRD_CANONICO` |
| plan de cuentas base | se fija estructura minima por grupos | `ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md` |
| reglas contables por hecho economico | se fija matriz minima v1 | `ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md` |
| politica de reversos y reaperturas | se fija `PoliticaReversoContable` y criterio de reverso/complemento | `PRD_CANONICO` + `ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md` |
| regimen tributario soportado | se cierra a `EmpresaContabilidadCompletaV1` como unico regimen automatizable del v1 | `PRD_CANONICO` + `ADR_ARQUITECTURA_003_CAPACIDADES_SII.md` |

## 3. Capacidades podadas del boundary activo

| Capacidad | Disposicion | Donde queda reflejado |
|---|---|---|
| `Portales.PortalInmobiliario` | `Podado` | `MATRIZ_GATES_EXTERNOS` + backlog de expansion |
| `Portales.Yapo` | `Podado` | `MATRIZ_GATES_EXTERNOS` + backlog de expansion |
| `IA.ClasificacionDocumental` | `Podado` | `MATRIZ_GATES_EXTERNOS` + backlog de expansion |
| `IA.Semantica` | `Podado` | `MATRIZ_GATES_EXTERNOS` + `ADR_ARQUITECTURA_007` historica |
| `IA.AsistenteConversacional` | `Podado` | `MATRIZ_GATES_EXTERNOS` + backlog de expansion |
| `SII.BoletaEmision` | `Podado` | `ADR_ARQUITECTURA_003` + `MATRIZ_GATES_EXTERNOS` |
| `SII.LibrosYArchivos` | `Podado` | `ADR_ARQUITECTURA_003` + `MATRIZ_GATES_EXTERNOS` |
| `SII.PresentacionAnualFinal` | `Podado` | `ADR_ARQUITECTURA_003` + `MATRIZ_GATES_EXTERNOS` |

## 4. Criterio de autosuficiencia alcanzado

El set activo se considera autosuficiente para el v1 porque:

- el backlog ya no define nada necesario para operar el core;
- las capacidades activas del v1 tienen dominio, reglas, gates y ADR cerrados;
- las capacidades no esenciales quedaron podadas o fuera del boundary activo;
- un implementador nuevo puede construir el v1 leyendo solo el set activo vigente.

## 5. Contraste externo final del core

Fuentes primarias contrastadas en el cierre final:

- SII confirma obligacion de conservacion de libros y documentacion tributaria por `6` anos, ampliable en ciertos casos segun articulo `200` del Codigo Tributario y situaciones como remanentes o amortizaciones.
- SII confirma conservacion de facturas, boletas y documentos tributarios por `6` anos calendario completos siguientes.
- SII explica que la propuesta parcial del `F29` a partir de IECV/RCV se obtiene manualmente y no se traspasa automaticamente a la declaracion; por eso el set activo cierra `F29Preparacion` como calculo interno de LeaseManager y no como dependencia automatica del SII.
- BCN consigna que la Ley `21.719` fue publicada el `13 de diciembre de 2024` y entra en vigencia el `1 de diciembre de 2026`, por eso el set activo mantiene el gate `Compliance.DatosPersonalesChile2026`.
- Google exige OAuth `2.0` para Gmail API en escenarios server-side; por eso el set mantiene `IdentidadDeEnvio` con ownership y credenciales explicitas.
- Twilio/WhatsApp mantiene restricciones de templates, canal y politicas del proveedor; por eso el set conserva gates separados y fallback de mensajeria.

Conclusion de contraste:

- el core contractual, contable y tributario del v1 queda defendible con fuentes oficiales;
- las capacidades no suficientemente defendibles hoy permanecen `Podadas` o fuera del boundary activo.

