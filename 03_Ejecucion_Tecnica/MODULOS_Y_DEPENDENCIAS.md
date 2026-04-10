# Modulos y dependencias - LeaseManager

## 1. Modulos del sistema

| Modulo | Responsabilidad | Dependencias duras | Entregable clave |
|---|---|---|---|
| `PlataformaBase` | auth, RBAC, auditoria, configuracion, async, storage | ninguna | base tecnica ejecutable |
| `Patrimonio` | socios, empresas, participaciones, propiedades | `PlataformaBase` | activos validos y ownership correcto |
| `Operacion` | mandato, cuenta recaudadora, identidades de envio | `PlataformaBase`, `Patrimonio` | propiedad elegible para contratar |
| `Contratos` | arrendatario, contrato, periodos, avisos, vinculadas | `Patrimonio`, `Operacion` | ciclo contractual vigente |
| `CobranzaActiva` | pagos, ajustes, garantias, repactacion, residual | `Contratos` | estado de cuenta y cobros mensuales |
| `Conciliacion` | provider bancario, movimientos, match, ingresos desconocidos | `Operacion`, `CobranzaActiva` | pago confirmado y trazado |
| `Contabilidad` | eventos, reglas, cuentas, asientos, cierre mensual | `Conciliacion`, `CobranzaActiva` | ledger balanceado |
| `Documentos` | expediente, PDF, politicas de firma y notaria | `Contratos`, `Operacion` | expediente documental formalizado |
| `Canales` | email y WhatsApp | `Operacion`, `Contratos`, `Documentos` | comunicaciones por canal valido |
| `SII` | DTE, F29, DDJJ, F22 dentro del boundary activo | `Contabilidad`, `Documentos` | preparacion tributaria |
| `Reporting` | dashboards, libros, reportes y exportaciones | todos los anteriores | vistas operativas y financieras |

## 2. Dependencias criticas

### Cadena operacional principal

1. `Patrimonio`
2. `Operacion`
3. `Contratos`
4. `CobranzaActiva`
5. `Conciliacion`
6. `Contabilidad`
7. `SII`

### Cadena documental y canales

1. `Operacion`
2. `Contratos`
3. `Documentos`
4. `Canales`

### Cadena de control y reporting

1. `PlataformaBase`
2. `Contabilidad`
3. `Reporting`

## 3. Reglas de implementacion

- `Contabilidad` no se implementa antes de que `Conciliacion` genere hechos confiables.
- `SII` no se implementa antes de que exista `ConfiguracionFiscalEmpresa`, ledger y cierre mensual.
- `Documentos` puede avanzar en paralelo con `Conciliacion`, pero no cierra su milestone sin `PoliticaFirmaYNotaria`.
- `Reporting` puede arrancar con vistas operativas tempranas, pero el reporting financiero final depende de `Contabilidad`.

## 4. Paralelismo seguro

Se puede trabajar en paralelo en:

- `PlataformaBase` y diseno de `Patrimonio`;
- `Documentos` y `Canales` una vez cerrado `Operacion`;
- `Reporting` operativo mientras madura `Contabilidad`.

No se recomienda paralelizar sin cerrar interfaces entre:

- `CobranzaActiva` y `Conciliacion`;
- `Conciliacion` y `Contabilidad`;
- `Contabilidad` y `SII`.

