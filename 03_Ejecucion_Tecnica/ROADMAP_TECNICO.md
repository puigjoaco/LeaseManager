# Roadmap tecnico - LeaseManager

## 1. Objetivo

Construir el v1 activo de LeaseManager en un orden que minimice retrabajo y respete las dependencias reales entre dominio, operacion, conciliacion, contabilidad, documentos y SII.

## 2. Principios de secuencia

- primero se construye lo transaccional y auditable;
- luego lo que depende de hechos economicos confirmados;
- despues lo documental y multicanal;
- al final lo tributario que consume cierre mensual y cierre anual.

## 3. Fases tecnicas

### Fase 0. Base de plataforma

Objetivo:

- dejar lista la base tecnica y de seguridad para que el resto no nazca sobre cimientos inestables.

Incluye:

- proyecto backend y frontend base;
- auth, RBAC y scope operativo;
- secretos, configuracion y entornos;
- auditoria base y resolucion manual;
- observabilidad minima;
- pipeline de tareas async;
- storage documental.

Salida:

- skeleton operativo listo para modelar dominio;
- autenticacion, permisos y auditoria funcionando;
- despliegue local y ambiente de integracion utilizables.

### Fase 1. Dominio patrimonial y operativo

Objetivo:

- modelar la base sobre la que viven contratos, cobros y tributacion.

Incluye:

- `Socio`, `Empresa`, `ParticipacionPatrimonial`, `Propiedad`;
- `MandatoOperacion`, `CuentaRecaudadora`, `IdentidadDeEnvio`, `AsignacionCanalOperacion`;
- validaciones de ownership, porcentajes y alcance por rol.

Salida:

- una propiedad queda elegible para contratar solo si su base patrimonial y operativa es valida.

### Fase 2. Contratos y cobranza activa

Objetivo:

- cerrar el ciclo contractual mensual con cobro calculado y estados operativos.

Incluye:

- `Arrendatario`, `CodeudorSolidario`;
- `Contrato`, `ContratoPropiedad`, `PeriodoContractual`, `AvisoTermino`;
- `PagoMensual`, `AjusteContrato`, `GarantiaContractual`, `HistorialGarantia`;
- `EstadoCuentaArrendatario`, `RepactacionDeuda`, `CodigoCobroResidual`.

Salida:

- se puede crear contrato, renovar, terminar y generar cobro mensual con formula canonica.

### Fase 3. Conciliacion y hechos economicos

Objetivo:

- capturar pagos reales, conciliarlos y transformar la operacion en hechos economicos confiables.

Incluye:

- `ProviderBancario`, `ConexionBancaria`;
- ingesta de movimientos;
- conciliacion exacta, asistida y manual;
- `IngresoDesconocido`;
- generacion de `EventoContable` a partir de hechos confirmados.

Salida:

- los pagos confirmados ya alimentan el ledger.

### Fase 4. Contabilidad nativa y cierre mensual

Objetivo:

- convertir eventos en asientos y cerrar el mes contable/tributario.

Incluye:

- `RegimenTributarioEmpresa`, `ConfiguracionFiscalEmpresa`;
- `ReglaContable`, `MatrizReglasContables`, `CuentaContable`;
- `AsientoContable`, `MovimientoAsiento`;
- `LibroDiario`, `LibroMayor`, `BalanceComprobacion`;
- `CierreMensualContable`, `PoliticaReversoContable`, `ObligacionTributariaMensual`.

Salida:

- ledger balanceado;
- cierre mensual aprobable;
- `F29Preparacion` alimentada por datos internos.

### Fase 5. Documentos y canales

Objetivo:

- formalizar la operacion con expediente, PDF canonico y comunicaciones.

Incluye:

- `ExpedienteDocumental`, `DocumentoEmitido`, `PoliticaFirmaYNotaria`;
- generacion PDF;
- flujo de firma y notaria;
- email operacional;
- WhatsApp gated.

Salida:

- contrato, anexos, avisos y terminos quedan trazados documentalmente y se notifican por canales validos.

### Fase 6. Tributacion mensual y anual del v1

Objetivo:

- preparar mensualmente y anualmente lo que el boundary activo soporta.

Incluye:

- `CapacidadTributariaSII` para `DTEEmision`, `DTEConsultaEstado`, `F29Preparacion`, `F29Presentacion`, `DDJJPreparacion`, `F22Preparacion`;
- `ProcesoRentaAnual`;
- flujos de aprobacion por `AdministradorGlobal`.

Salida:

- el sistema prepara `F29`, `DDJJ` y `F22` dentro del boundary activo;
- cualquier presentacion final sigue gobernada por gates y aprobacion interna.

## 4. Orden recomendado de entrega

1. Fase 0
2. Fase 1
3. Fase 2
4. Fase 3
5. Fase 4
6. Fase 5
7. Fase 6

## 5. Regla de progreso

No avanzar a una fase nueva si la anterior no cumple sus criterios de salida y deja deuda estructural en:

- integridad del modelo;
- permisos;
- auditoria;
- idempotencia;
- consistencia del ledger;
- gating externo.

