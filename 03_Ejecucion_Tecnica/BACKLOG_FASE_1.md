# Backlog Fase 1 - Nucleo operacional

## 1. Objetivo de la fase

Dejar operativo el nucleo transaccional de LeaseManager hasta llegar a:

- activos validos;
- mandato operativo;
- contratos vigentes;
- cobro mensual calculado;
- conciliacion exacta o manual;
- ledger base con eventos y asientos;
- expediente documental basico;
- email operativo.

## 2. Bloques de trabajo

### B1. Plataforma base

| ID | Entrega | Depende de | Criterio de listo |
|---|---|---|---|
| `F1-B1-01` | proyecto backend base | ninguna | app levanta con configuracion por ambiente |
| `F1-B1-02` | auth y RBAC base | `F1-B1-01` | roles y scopes operativos funcionan |
| `F1-B1-03` | auditoria y resolucion manual base | `F1-B1-01` | eventos sensibles quedan trazados |
| `F1-B1-04` | storage documental y secretos | `F1-B1-01` | secretos y archivos quedan segregados |
| `F1-B1-05` | cola async y observabilidad minima | `F1-B1-01` | tareas y salud quedan visibles |

### B2. Patrimonio y operacion

| ID | Entrega | Depende de | Criterio de listo |
|---|---|---|---|
| `F1-B2-01` | `Socio`, `Empresa`, `ParticipacionPatrimonial` | `F1-B1-02` | ownership `100%` validado |
| `F1-B2-02` | `Propiedad` y reglas de comunidad | `F1-B2-01` | propiedad valida y unica por owner |
| `F1-B2-03` | `CuentaRecaudadora` | `F1-B1-04` | cuenta operativa modelada |
| `F1-B2-04` | `MandatoOperacion` | `F1-B2-02`, `F1-B2-03` | ownership recaudacion/facturacion/comunicacion resuelto |
| `F1-B2-05` | `IdentidadDeEnvio` y asignacion canal | `F1-B2-04` | email activo por identidad valida |

### B3. Contratos y cobranza activa

| ID | Entrega | Depende de | Criterio de listo |
|---|---|---|---|
| `F1-B3-01` | `Arrendatario` y onboarding | `F1-B1-02` | alta asistida operativa |
| `F1-B3-02` | `Contrato`, `ContratoPropiedad`, `PeriodoContractual` | `F1-B2-04`, `F1-B3-01` | contrato se crea sin romper invariantes |
| `F1-B3-03` | `AvisoTermino` y contratos futuros | `F1-B3-02` | flujo y bloqueos validados |
| `F1-B3-04` | `PagoMensual` y formula canonica | `F1-B3-02` | monto calculado correcto con UF/codigo |
| `F1-B3-05` | `AjusteContrato`, `GarantiaContractual`, `HistorialGarantia` | `F1-B3-04` | ajustes y garantias trazados |
| `F1-B3-06` | `EstadoCuentaArrendatario`, `RepactacionDeuda`, `CodigoCobroResidual` | `F1-B3-05` | deuda y residual visibles |

### B4. Conciliacion bancaria

| ID | Entrega | Depende de | Criterio de listo |
|---|---|---|---|
| `F1-B4-01` | interfaz `ProviderBancario` y `ConexionBancaria` | `F1-B2-03`, `F1-B1-05` | provider inicial integrable |
| `F1-B4-02` | ingesta de movimientos Banco de Chile | `F1-B4-01` | movimientos almacenados y trazados |
| `F1-B4-03` | match exacto y `IngresoDesconocido` | `F1-B3-04`, `F1-B4-02` | pagos exactos se asignan sin ambiguedad |
| `F1-B4-04` | flujo manual auditado | `F1-B4-03`, `F1-B1-03` | el sistema sigue operando en degradado |

### B5. Contabilidad base

| ID | Entrega | Depende de | Criterio de listo |
|---|---|---|---|
| `F1-B5-01` | `RegimenTributarioEmpresa` y `ConfiguracionFiscalEmpresa` | `F1-B2-01` | empresa fiscalmente configurable |
| `F1-B5-02` | plan de cuentas y `MatrizReglasContables` v1 | `F1-B5-01` | cuentas obligatorias disponibles |
| `F1-B5-03` | `EventoContable` desde pagos/garantias/ajustes | `F1-B3-05`, `F1-B4-03` | hechos economicos generados sin duplicacion |
| `F1-B5-04` | `AsientoContable` y `MovimientoAsiento` | `F1-B5-02`, `F1-B5-03` | `debe = haber` siempre |
| `F1-B5-05` | `LibroDiario`, `LibroMayor`, `BalanceComprobacion` | `F1-B5-04` | ledger consultable por periodo |

### B6. Documentos y email

| ID | Entrega | Depende de | Criterio de listo |
|---|---|---|---|
| `F1-B6-01` | `ExpedienteDocumental` y `DocumentoEmitido` | `F1-B1-04`, `F1-B3-02` | expediente por entidad operativa |
| `F1-B6-02` | `PoliticaFirmaYNotaria` | `F1-B6-01` | requisitos documentales configurados |
| `F1-B6-03` | generacion PDF canonico | `F1-B6-02` | contrato y anexos emitibles |
| `F1-B6-04` | email operacional | `F1-B2-05`, `F1-B6-03` | envio por identidad activa |

## 3. Definicion de cierre de Fase 1

La fase cierra solo si:

- se puede activar una propiedad y crear un contrato valido;
- se puede generar `PagoMensual` con formula canonica;
- un pago exacto conciliado genera `EventoContable` y `AsientoContable`;
- existe expediente documental y email operativo;
- no quedan huecos de permisos o auditoria en el flujo base.

