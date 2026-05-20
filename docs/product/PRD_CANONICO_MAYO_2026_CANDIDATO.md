# PRD Canonico Mayo 2026 - LeaseManager

Estado: candidato, no vigente hasta aprobacion del usuario.
Fecha de emision candidata: 2026-05-20.
Audiencia: producto, arquitectura, desarrollo, operaciones, contabilidad y cierre productivo.

## 1. Proposito documental

Este documento propone una nueva version canonica de producto para LeaseManager. Nivela hacia arriba los 26 PRD fuente, el PRD canonico vigente de marzo 2026, la Arquitectura Maestra LeaseManager, los documentos de production-readiness, el contexto del Excel legacy Mayo 2026, las correcciones confirmadas por el usuario, el codigo real y los gates existentes.

Mientras no sea aceptado formalmente, este documento no reemplaza al set vigente. Su funcion es servir como propuesta limpia para migrar el proyecto a una base profesional, sin herencia operativa innecesaria y sin arrastrar decisiones antiguas que ya no representan el estado real del producto.

## 2. Mision del producto

LeaseManager debe convertirse en el sistema principal para administrar arriendos, propiedades, sociedades, comunidades, socios, cobranza, conciliacion bancaria, facturacion cuando corresponda, contabilidad, liquidaciones, impuestos y operacion productiva de la cartera inmobiliaria familiar.

La mision no es solo construir pantallas o automatizaciones aisladas. La mision es reemplazar progresivamente el Excel legacy como fuente operativa diaria, manteniendo la logica real del negocio, pero normalizada en datos, flujos, auditoria, seguridad, evidencia y controles reproducibles.

El producto terminado debe permitir operar indefinidamente con datos reales, sin depender de supuestos ocultos, datos inventados, planillas paralelas no conciliadas, scripts sueltos, conocimiento tacito o intervenciones manuales no trazadas.

## 3. Frontera de producto

LeaseManager Produccion 1.0 cubre:

- Datos maestros reales de empresas, socios, comunidades, propiedades, participaciones, arrendatarios, contratos, cuentas bancarias y garantias.
- Contratos y periodos contractuales, incluyendo renovaciones, alertas, avisos de termino, contrato futuro, garantias, codeudores, ajustes, tramos y casos especiales.
- Cobranza mensual con UF exacta por fecha, moneda efectiva, WebPay/Transbank cuando corresponda, correos y mora.
- Banco de Chile como primer proveedor bancario operativo, sin convertirlo en limitacion eterna del dominio.
- Conciliacion bancaria por cuenta, con saldo sistema igual a saldo banco.
- Deuda, repactacion, cobranza residual post-contrato, estado de cuenta del arrendatario y score de pago.
- Facturacion SII DTE 34 solo para sociedades habilitadas y solo cuando el flujo tributario aplicable este validado.
- Contabilidad mensual, asientos, cierre mensual, liquidaciones, distribuciones, PPM y contabilidad personal de socios.
- Cierre tributario anual: renta, DDJJ, F22, certificados y reportes, siempre validado contra SII, normativa vigente o experto.
- Expediente documental contractual, respaldos tributarios, cartas, liquidaciones de garantia y evidencia de firma/notaria cuando aplique.
- Portal publico y superficies de arrendatario, con datos publicos limitados y sin exponer informacion interna.
- Seguridad, RLS/Auth, roles, 2FA/MFA administrativo, rate limit, webhooks fail-closed, audit_log, backups, restore, runbook y evidencia de operacion.

Queda fuera del boundary activo salvo reemision formal:

- Scraping bancario o credenciales de portal como mecanismo canonico.
- Automatizacion tributaria autonoma sin validacion oficial.
- Facturacion de comunidades o personas naturales.
- Portales inmobiliarios externos como automatizacion obligatoria.
- IA semantica/conversacional como mecanismo de acciones criticas.
- Reglas tributarias deducidas solo desde cursos, transcripciones o inferencias.
- Sistemas historicos de gestion de tareas como fuente de verdad productiva.

## 4. Fuentes y jerarquia

Si este candidato se acepta, la jerarquia propuesta queda asi:

1. PRD Canonico Mayo 2026 aceptado: mision, dominio, alcance, reglas de producto y acceptance.
2. Arquitectura Maestra LeaseManager: arquitectura integral de inicio a fin, capas, dependencias, gates, evidencia y Definition of Done.
3. Matriz de gates externos: estado real de base de datos, Banco, WebPay,
   correo, SII, dominio, jobs, webhooks y dependencias externas.
4. ADR activos: decisiones tecnicas y de implementacion que el PRD no debe congelar.
5. Contextos obligatorios: Excel legacy, database, contabilidad, integraciones, invariantes, production-readiness y decisiones confirmadas por el usuario.
6. Codigo real, schema, migraciones, tests, auditores y datos verificados.
7. Historicos: 26 PRD fuente, PRD maestro, PRD unificado, auditorias historicas y artefactos historicos, solo como trazabilidad o insumo para rescatar ideas validas.

Regla: un documento historico no puede abrir alcance, cerrar etapa, reemplazar evidencia ni contradecir datos reales confirmados.

El anexo `docs/product/ANEXO_MODELO_OPERATIVO_EXCEL_MAYO_2026.md` traduce el funcionamiento practico del Excel legacy a reglas operativas candidatas. Ese anexo no convierte celdas en arquitectura, pero si fija que LeaseManager debe absorber la logica real de cobranza, conciliacion, clasificacion, liquidacion, comision de administracion, participaciones, sucesion y cierre bancario.

El material tributario de `D:/Proyectos/MineralBalance/aula-tributaria-at2026/` puede apoyar el diseno de renta anual, DDJJ, F22, certificados y captura de datos durante el ano. No es fuente normativa final, no abre gates tributarios y no puede convertirse en regla del sistema sin validacion contra SII, normativa vigente, instrucciones AT aplicables o confirmacion experta.

Jerarquia de conflicto entre fuentes:

1. Decision explicita del usuario, contrato, escritura, mandato, documento legal o comprobante oficial confirmado.
2. Banco, cartola, saldo y movimiento oficial para hechos de caja y conciliacion.
3. SII, normativa vigente, instrucciones AT, folios, DTE aceptado/rechazado y documentos tributarios oficiales.
4. Base real o snapshot real/controlado para estado operativo del sistema.
5. Excel legacy para funcionamiento practico y logica historica del negocio.
6. Production-readiness, gates, auditores y runbooks para readiness operativo.
7. Material tributario de apoyo y documentos historicos, solo como insumo secundario.

Si dos fuentes discrepan y la fuente superior no esta disponible o no resuelve el caso, el resultado correcto es bloqueo, verificacion o pregunta concreta; no se inventa conciliacion, dato, regla ni cierre.

## 5. Invariantes no negociables

- No inventar direcciones, RUTs, nombres, montos, contratos, cuentas, participaciones, clasificaciones ni datos legales.
- La UF se usa solo con valor exacto de la fecha requerida. Si falta, el calculo se bloquea.
- Saldo sistema igual a saldo banco para conciliacion y cierres.
- Cada entidad opera sobre su cuenta bancaria definida; no se mezclan fondos por conveniencia.
- Una propiedad activa se cobra por una sola `CuentaRecaudadora` vigente para el mandato aplicable.
- Solo sociedades emiten DTE 34; comunidades y personas naturales no facturan.
- Las renovaciones y cambios de contrato usan periodos_contractuales; no se duplican contratos para representar periodos.
- Los datos maestros viven una vez y los flujos los referencian.
- Las operaciones criticas escriben audit_log o evidencia equivalente.
- WebPay, correo, SII o Banco no reemplazan por separado la evidencia final del flujo completo.
- Toda regla fiscal se valida contra SII, normativa vigente o experto.
- La suma de participaciones activas de una empresa o comunidad propietaria debe ser exactamente 100%.
- Una propiedad no puede pertenecer simultaneamente a empresa, comunidad y persona natural; debe existir un owner operativo unico por vigencia.
- Una empresa propietaria solo admite socios/personas naturales como participantes patrimoniales activos; una comunidad puede admitir socios y empresas segun porcentaje vigente.
- Una comunidad activa debe tener exactamente una representacion activa vigente para documentos, comunicaciones, decisiones operativas y trazabilidad.
- Un cambio de arrendatario termina el contrato anterior y crea uno nuevo; no se reescribe la identidad historica del contrato.
- Una propiedad solo puede tener un contrato vigente y un contrato futuro; una propiedad vinculada no puede tener contrato activo independiente.
- Todo asiento contable debe cuadrar debe = haber y un periodo aprobado no admite edicion destructiva.
- `AvisoTermino` activo bloquea la renovacion automatica mientras este vigente y habilita contrato futuro cuando corresponda.

Policies v1:

- Contratos activos mensuales: inicio dia 1, termino ultimo dia del mes y dia de pago entre 1 y 5.
- Monto minimo operativo: CLP 1.000 o equivalente validado al registrar moneda UF.
- Email es canal base; WhatsApp es complementario y depende de gate, templates, opt-in y ventana permitida.
- Debe existir al menos un canal operativo por contrato.
- La pareja principal + vinculada comparte cobro, garantia, aviso de termino, calendario y codigo efectivo de la propiedad principal.
- El cierre de mes es automatico o asistido por sistema; reapertura solo excepcional, aprobada y auditada.
- El score de pago se expresa como porcentaje y conteo de meses evaluados; excluye meses sin registro operativo.
- El score considera pago a tiempo hasta el dia de vencimiento inclusive. Si existe repactacion, cuenta como cumplido solo si el total exigible del mes, arriendo mas cuota, fue pagado en plazo.
- No existen dias de gracia ocultos, feriados asumidos ni extensiones tacitas de vencimiento; cualquier excepcion debe venir de contrato, regla formal, gate o decision auditada.
- Libros contables, DTE, F29, F22, DDJJ y soportes tributarios se retienen minimo 6 anos calendario completos, ampliables por fiscalizacion, remanentes, litigio o necesidad legal.
- Expedientes contractuales, eventos auditables y respaldos operativos se retienen minimo 6 anos desde termino de contrato o ultimo evento relevante.
- Exports sensibles expiran en maximo 30 dias salvo hold legal o tributario.
- Idioma operativo: espanol de Chile; formato de fecha: `dd/mm/yyyy`; zona horaria: `America/Santiago`; monedas operativas: CLP y UF.
- Las notificaciones tienen base sugerida dias `1/3/5/10/15/20/25`, pero se configuran por contrato y canal habilitado.
- WhatsApp, si su gate esta abierto, opera solo dentro de ventana `08:00-21:00`, con templates, opt-in y manejo de bloqueo.
- `CodigoConciliacionEfectivo` usa rango `001-999` por cuenta/seccion operativa; no es identificador global.
- Email no se suspende por falla de WhatsApp; si WhatsApp falla, el canal base o alerta critica debe seguir operando.
- Un bloqueo definitivo de WhatsApp marca el contacto, registra evento, alerta al administrador y permite rehabilitacion manual; si falla de nuevo, vuelve a bloquearse sin ocultar el evento.
- Procesos criticos calendarizados evitan ventanas de cambio horario; `02:01 America/Santiago` es referencia inicial para jobs sensibles salvo ADR o runbook vigente distinto.

## 5.1 Indicadores no funcionales iniciales

Estos indicadores no reemplazan gates ni evidencia contable. Sirven para medir si el producto terminado realmente mejora la operacion:

- `TiempoAdministrativoMensual`: reducir al menos 90% contra baseline comparable dentro de 6 meses de uso estable.
- `ErrorPostConciliacion`: menos de 1% de pagos conciliados con correccion posterior.
- `PagoPuntual`: mejorar al menos 15% contra baseline historico de la cartera.
- `DashboardP95`: percentil 95 de carga del dashboard principal menor a 2 segundos con cache habilitada.
- `DocumentoContractualP95`: percentil 95 de generacion documental menor a 3 segundos.
- `UptimeMensual`: objetivo inicial 99.5% sobre servicios criticos, excluyendo mantenciones comunicadas.

## 6. Modelo operativo base

Actores principales:

- Administrador/operador: mantiene datos, clasifica excepciones, aprueba cierres y opera el sistema. Alias canonicos: `AdministradorGlobal`, `AdministradorOperativo` y `OperadorDeCartera` segun scope.
- Arrendatario: recibe cobros, paga, recibe confirmaciones y facturas cuando corresponda.
- Socio/persona natural: recibe liquidaciones, distribuciones, contabilidad personal, certificados y reportes.
- Contador/tributario: revisa asientos, cierres, PPM, F22, DDJJ, certificados y conversiones IFRS/GAAP.
- Revisor fiscal externo, si se configura: observa, comenta y exporta solo dentro de su scope, sin acceso a secretos ni capacidad de bloqueo operativo. Alias canonico: `RevisorFiscalExterno`.
- Operador tecnico: gestiona deploy, variables, backups, restore, monitoreo, incidentes y runbook.
- Proveedores externos: Banco de Chile, Transbank/WebPay, correo, SII, UF y
  servicios de despliegue/base de datos definidos por ADR vigente. Las menciones
  heredadas a proveedores especificos solo aplican si el stack vigente las
  ratifica.

Entidades obligatorias:

- Empresas, socios, comunidades, propiedades, participaciones, arrendatarios, contratos, periodos contractuales, garantias, cuentas bancarias, pagos mensuales, movimientos bancarios, facturas electronicas, asientos contables, obligaciones tributarias, liquidaciones, certificados, audit_log, usuarios, roles, configuraciones de integracion y evidencia.

Matriz operacional real inicial:

- Las sociedades base son Inmobiliaria Puig SpA, San Cristobal Ltda, Santa Maria Ltda y Quepe Ltda, sujetas a validacion contra datos reales.
- La operacion contempla socios/personas naturales con contabilidad personal separada y participaciones vigentes.
- Cada sociedad, comunidad operativa y persona natural que recauda debe tener cuenta bancaria propia en datos maestros controlados.
- Los numeros de cuenta, RUTs completos y datos sensibles no se hardcodean en codigo ni documentos publicos; viven en datos maestros, secretos, snapshots controlados o evidencia redactada segun corresponda.
- Inmobiliaria Puig mantiene contabilidad IFRS interna con conversion GAAP tributaria; las otras sociedades operan GAAP salvo decision documentada.
- La contabilidad personal de socios es separada de la contabilidad de sociedades y no emite DTE.

Gobierno de socios, empresas y cuentas:

- Un socio con participaciones activas no se elimina; se transfiere, reemplaza o termina su participacion mediante flujo auditado que mantenga total 100% por empresa, comunidad o propiedad.
- Una empresa o entidad operativa debe tener al menos una cuenta bancaria activa para operar cobros, pagos, cierres y conciliacion.
- Una cuenta bancaria activa requiere titular/recaudador correcto, uso operativo declarado, gate bancario o modo manual controlado y evidencia de que puede reconciliar saldos; no basta con existir en una tabla.
- Si una empresa queda sin cuenta activa, debe bloquear operaciones nuevas hasta asignar cuenta valida o registrar disolucion/termino formal.
- La disolucion de empresa o salida operativa exige transferir activos, contratos, participaciones, obligaciones, cuentas, expedientes, garantias, contratos futuros, avisos y comunicaciones antes de cerrar la entidad.
- La eliminacion directa de empresa, socio, comunidad o cuenta solo aplica si no existen efectos activos, historicos obligatorios, saldos, contratos, obligaciones ni documentos que deban conservarse.

Reglas de acceso:

- Administrador global opera y corrige dentro de gates, con evidencia y auditoria.
- Contador o contadora tiene acceso de revision contable/tributaria y exportacion controlada, pero no acceso a secretos ni acciones bancarias fuera de autorizacion.
- Socio accede solo a informacion filtrada por su participacion, liquidaciones, certificados y documentos propios.
- Arrendatario accede solo a su estado de cuenta, documentos, pagos y comunicaciones.
- Toda lectura, dashboard, reporte y export debe respetar scope de rol, entidad, socio, contrato, mandato y sensibilidad del dato.
- Los permisos de socio se derivan de participaciones activas y grants explicitos; nunca por coincidencia de nombre, email o texto libre.
- Secretos, credenciales bancarias, tokens, logs sensibles y configuraciones criticas quedan fuera de roles de consulta contable/socio/arrendatario y requieren rol autorizado, motivo y auditoria.

## 6.1 Modelo de dominio obligatorio

El dominio minimo no puede limitarse a tablas aisladas. Debe cubrir estos contextos:

- Patrimonio: socios, empresas, comunidades, representacion de comunidades, propiedades, participaciones patrimoniales con vigencia y cuentas asociadas.
- Operacion: mandato operativo, recaudador, propietario, administrador operativo, entidad facturadora, cuenta recaudadora, identidad de envio y asignacion de canales.
- Contratos: arrendatarios, codeudores, contratos, propiedades vinculadas, periodos contractuales, avisos de termino, contrato futuro, garantias, ajustes y tramos.
- Cobranza: pagos mensuales, distribucion economica del cobro, codigo de conciliacion efectivo, ingresos desconocidos, deudas, repactaciones, cobranza residual y estado de cuenta del arrendatario.
- Banco: movimientos por cuenta, saldo, conciliacion, clasificacion, excepciones, transferencias interentidad y evidencia bancaria.
- Clasificacion: `CategoriaMovimiento`, reglas de asignacion, categorias protegidas, reclasificacion, resolucion manual y motivo auditable.
- Documentos: expediente documental, documento emitido, version de plantilla, checksum, storage, politica de firma/notaria y formalizacion.
- Contabilidad: evento contable, regla contable, asiento, movimiento de asiento, plan de cuentas, cierre mensual, reversos y obligaciones tributarias.
- Tributacion: configuracion fiscal por empresa, DTE, F29/PPM, DDJJ, F22, certificados y proceso anual.
- Seguridad y operacion: usuarios, roles, RLS, MFA/2FA, audit_log, resolucion manual, secretos, retencion, backups, restore, monitoreo y runbook.

`MandatoOperacion` es una entidad conceptual obligatoria: declara quien es propietario, quien administra, quien recauda, quien factura, que cuenta recibe, que identidad comunica y que autorizaciones existen. Si esos roles no coinciden, el mandato debe declararlo explicitamente. Debe existir antes de activar un contrato. La `CuentaRecaudadora` debe pertenecer exactamente al recaudador declarado. Si la entidad facturadora existe, debe ser sociedad con `ConfiguracionFiscalEmpresa` activa para la capacidad tributaria aplicable. Si el propietario es comunidad sin participante empresa facturadora habilitada, la entidad facturadora queda nula y no se emite DTE.

`IdentidadDeEnvio` es una entidad conceptual obligatoria: las credenciales de correo o mensajeria pertenecen a una identidad autorizada, no a una cuenta bancaria. Si no hay identidad activa para un canal, el sistema no inventa remitente sustituto. Para documentos contractuales o tributarios, la identidad debe pertenecer a la entidad facturadora o al administrador operativo expresamente autorizado por mandato.

`ExpedienteDocumental` es obligatorio para contratos, anexos, cartas de aviso, garantias, respaldos tributarios, comprobantes notariales y resoluciones manuales relevantes. Un documento critico debe tener version, checksum, origen, estado y storage_ref.

La implementacion puede usar nombres de tablas distintos si el schema real ya esta avanzado, pero la capacidad y las relaciones deben existir.

`ResolucionManual` es obligatoria cuando el sistema no puede decidir de forma segura: debe registrar motivo, responsable, datos afectados, criterio aplicado, evidencia, resultado y fecha. No existe resolucion manual invisible.

## 6.2 Glosario canonico minimo

El schema real puede nombrar tablas distinto si ya existe una decision tecnica valida, pero estas capacidades conceptuales deben estar presentes y trazables:

- `CuentaRecaudadora`: cuenta o instrumento sobre el que se esperan cobros; pertenece al recaudador declarado por `MandatoOperacion`.
- `Recaudador`: actor que recibe operativamente el flujo bancario y debe ser titular/sujeto autorizado de la `CuentaRecaudadora`.
- `EntidadFacturadora`: empresa habilitada para emitir documentos tributarios cuando el gate SII y la configuracion fiscal aplicable estan abiertos.
- `ParticipacionPatrimonial`: porcentaje vigente de socio o empresa sobre empresa, comunidad o propiedad, con suma activa exactamente 100% por owner.
- `RepresentacionComunidad`: representante vigente de una comunidad activa; debe ser unica por vigencia para comunicaciones, documentos y decisiones operativas.
- `ProviderBancario`: adapter conceptual de movimientos, saldos y conectividad. La conciliacion automatica depende de proveedor activo y saludable.
- `FuenteUF`: cadena priorizada Banco Central -> CMF -> MiIndicador -> carga manual auditada, sin default silencioso.
- `CanalMensajeria`: canal con provider, gate, restricciones, identidad y estado independiente.
- `GateExterno`: condicion formal para habilitar, suspender, degradar o cerrar una capacidad dependiente de terceros, con entrada, suspension, salida, fallback y evidencia minima.
- `CapacidadTributariaSII`: gate por empresa y capacidad; no existe bloque generico unico llamado "API SII".
- Capacidades SII separadas: `DTEEmision`, `DTEConsultaEstado`, `F29Preparacion`, `F29Presentacion`, `DDJJPreparacion` y `F22Preparacion`, cada una con gate y evidencia propia.
- `ConfiguracionFiscalEmpresa`: habilita cierre mensual, F29/PPM, DDJJ, F22 y preparacion tributaria solo cuando esta completa; si falta, la capa contractual/cobranza puede operar, pero el cierre tributario automatizado queda bloqueado.
- `ContratoPropiedad`: relacion entre contrato y propiedad, incluyendo rol principal/vinculada y codigo snapshot cuando aplique.
- `ContratoPrincipal`: documento contractual rector de un contrato activo, dentro de expediente documental.
- `PeriodoContractual`: tramo de vigencia, valor, moneda, reajuste y reglas economicas sin duplicar contrato.
- `AjusteContrato`: descuento, recargo o ajuste definido por periodo, con justificacion, vigencia y limite minimo.
- `GarantiaContractual`: garantia pactada/recibida/devuelta/retenida/aplicada por contrato, no por propiedad.
- `PagoMensual`: obligacion mensual por contrato y periodo, con monto calculado, monto pagado, vencimiento, estado, mora y codigo efectivo.
- `DistribucionCobroMensual`: atribucion economica, conciliada y facturable del pago mensual por beneficiario, porcentaje y regla vigente.
- `EstadoCuentaArrendatario`: consolida deuda, repactaciones, cumplimiento, score y observaciones.
- `IngresoDesconocido`: ingreso bancario o manual no asignable automaticamente; permanece bloqueado hasta clasificacion, devolucion, regularizacion o resolucion manual.
- `RepactacionDeuda`: acuerdo trazable sobre deuda total acumulada, cuotas, vencimientos, estado y efectos sobre score/contabilidad.
- `HistorialGarantia`: historial de recepcion, retencion, aplicacion y devolucion de garantias, vinculado a contrato, movimiento y evidencia.
- `EventoContable`: hecho economico canonico listo para contabilizar, con idempotencia y origen.
- `ReglaContable`: transforma un evento contable en asiento segun plan y vigencia.
- `MotorContable`: capacidad que transforma eventos contables en asientos idempotentes y balanceados bajo reglas vigentes.
- `MatrizReglasContables`: version canonica del mapping evento -> cuenta debe, cuenta haber, condicion tributaria y vigencia.
- `CuentaContable`: cuenta del plan activo, con codigo, nombre, naturaleza, nivel, padre y estado.
- `CentroResultado`: dimension de analisis cuando un evento deba atribuirse a propiedad, comunidad, sociedad, socio u otra unidad economica.
- `AsientoContable`: journal balanceado, con debe = haber y `hash_integridad` cuando aplique.
- `MovimientoAsiento`: linea de asiento con cuenta, debe/haber, centro de resultado, entidad y referencia de origen.
- `CierreMensualContable`: cierre auditable del periodo; aprobado bloquea mutaciones estructurales salvo reapertura controlada.
- `CierreMensualContableYTributario`: vista de control que une cierre operativo, contable, banco cuadrado, PPM/F29 cuando aplique y bloqueadores del periodo.
- `ReaperturaDeMes`: proceso excepcional para reabrir periodo aprobado con autorizacion, justificacion, efecto esperado, reversos/ajustes y evidencia.
- `ObligacionTributariaMensual`: obligacion mensual que alimenta PPM/F29 y reportes.
- `EstadoPreparacionTributaria`: NoAplica, PendienteDatos, EnPreparacion, Preparado, AprobadoParaPresentacion, Presentado, Observado o Rectificado.
- `ProcesoRentaAnual`: consolidacion anual para DDJJ, F22, certificados y paquetes de revision.
- `SalidaTributariaMensualFinal` y `SalidaTributariaAnualFinal`: salidas finales solo cuando el gate aplicable, aprobacion y evidencia esten completos; si no, el sistema opera en preparacion/revision.
- `PresentacionAnualFinal`: capacidad final podada salvo reemision/gate formal; no se presume por existir preparacion anual.
- `LibroDiario`, `LibroMayor` y `BalanceComprobacion`: vistas derivadas del ledger, no planillas paralelas.
- `DocumentoEmitido`: documento versionado con storage, checksum, estado, expediente asociado y flujo PDF canonico antes de cualquier carga externa controlada.
- `AsignacionCanalOperacion`: vincula mandato, canal e identidad de envio con prioridad y estado.
- `ConexionBancaria`: estado de conectividad por cuenta/proveedor, con modo activo, pausado, degradado o inactivo segun gate real.
- `PoliticaFirmaYNotaria`: define firma, notaria y formalizacion exigida por tipo documental.
- `PoliticaReversoContable`: define reversos, asientos complementarios y reaperturas posteriores al cierre.
- `PoliticaRetencionDatos`: politica canonica de conservacion, exportacion, hold legal/tributario, borrado logico y purga fisica cuando aplique.
- `EventoAuditable`: registro inmutable o equivalente para accion sensible, con actor, timestamp, entidad, accion, motivo, `payload_hash`, aprobacion, `external_ref` y referencia externa cuando exista.
- `CodigoCobroResidual`: referencia visible de cobranza post-contrato, formato canonico `CCR-XXXXXX`, sin colision con codigos de propiedad.
- `RegimenTributarioEmpresa`: regimen fiscal habilitado por empresa; en v1 solo se automatiza `EmpresaContabilidadCompletaV1`, y cualquier ampliacion requiere gate/ADR y validacion oficial o experta.

Capacidades externas minimas gobernadas por gates:

- `Banca.Movimientos`, `Banca.Saldos` y `Banca.Conectividad`: requieren credenciales oficiales validas, cuenta operativa, conectividad saludable y evidencia de sync/saldo; fallback solo carga o consulta manual auditada.
- `UF.BancoCentral`, `UF.CMF`, `UF.MiIndicador` y `UF.CargaManualExtraordinaria`: la carga manual requiere motivo, usuario, fecha, valor persistido y rectificacion si se detecta error.
- `Email.Salida`: requiere identidad activa, autorizacion del canal, prueba de envio y evidencia.
- `WhatsApp.Salida`: requiere numero habilitado, templates aprobados, opt-in operativo, ventana permitida y manejo de bloqueo; fallback a email o alerta critica.
- `SII.*`: cada capacidad tributaria se abre, suspende o degrada por separado; presentaciones finales no se reactivan sin reemision/gate formal cuando esten podadas.
- `SII.BoletaEmision`, `SII.LibrosYArchivos` y `SII.PresentacionAnualFinal` permanecen podadas del v1 salvo reemision formal.
- `Compliance.DatosPersonalesChile2026`: si aplica por fecha/normativa, requiere politica aprobada, responsables, controles y evidencia archivada.
- Capacidades `Podadas` no reaparecen en roadmap, UI, gates ni acceptance sin reemision formal del set activo.

Restricciones operativas derivadas:

- Una `CuentaRecaudadora` con conciliacion por codigo embebido soporta como maximo 999 propiedades/codigos activos en su namespace.
- Un contrato puede tener override explicito de `IdentidadDeEnvio`; si no existe, se usa la asignacion vigente del `MandatoOperacion`.
- `F29Preparacion`, `DDJJPreparacion` y `F22Preparacion` solo consumen obligaciones y formularios habilitados por `ConfiguracionFiscalEmpresa`.
- `F29Preparacion` se construye desde ledger, obligaciones y configuracion interna validada; no depende de copiar una propuesta automatica externa sin contraste.

Aprobaciones criticas:

- `AsignacionManualPagoAmbiguo` nunca se consolida sin aprobacion final de administrador autorizado y `ResolucionManual`.
- `ReaperturaDeMes` requiere aprobacion de administrador autorizado, justificacion, efecto esperado, reversos/ajustes previstos, evidencia y cierre posterior.
- `CambioDeGateSII` para F29, DDJJ, F22 o presentaciones finales requiere evidencia del gate, checklist de readiness y decision registrada.
- `CambioDeGateComplianceDatos2026` requiere checklist legal-operativo completo y evidencia archivada.
- `ExportacionMasivaDeDatosSensibles` solo puede ejecutarse con rol autorizado, scope, motivo, expiracion, trazabilidad y `EventoAuditable`.

## 7. Casos especiales obligatorios

Bulnes 699: LeaseManager administra solo la participacion real correspondiente a la comunidad. No se factura por comunidad. El sistema debe cobrar, conciliar y distribuir solo la parte administrada, sin inventar el 80% externo ni mezclarlo con el flujo interno.

Parking E49: pertenece a Joaquin como persona natural, no a Inmobiliaria Puig SpA. Se cobra y registra en contabilidad personal. No emite factura.

Edificio Q / propiedades con participacion de Inmobiliaria Puig: debe distinguirse devengo, facturacion, conciliacion bancaria y transferencia real. Inmobiliaria Puig solo queda conciliada en su contabilidad bancaria cuando el dinero llega a su cuenta o existe movimiento intercuenta trazado.

Edificio Q Dpto 1014 codigo 46 Familia: es una sola propiedad/contrato de comunidad, no una propiedad duplicada. Inmobiliaria Puig factura solo su porcentaje activo desde participaciones sobre el valor vigente del contrato. Los socios personas naturales no facturan.

## 8. Arquitectura funcional end-to-end

El producto completo se entiende como este flujo:

1. Confirmar datos reales y fuentes de verdad.
2. Normalizar empresas, socios, comunidades, cuentas, propiedades, participaciones, arrendatarios y contratos.
3. Modelar periodos contractuales, garantias, codigos por seccion y casos especiales.
4. Generar cobranza mensual con moneda efectiva y UF exacta.
5. Enviar cobros y recordatorios por canales habilitados.
6. Confirmar pago por WebPay o transferencia, sin matching por monto cuando existe token/transaction id.
7. Importar movimientos bancarios por cuenta y conciliar contra pagos, contratos y clasificaciones.
8. Emitir DTE 34 solo si corresponde, despues de cumplir reglas y gate SII aplicable.
9. Generar contabilidad mensual, asientos balanceados, liquidaciones y distribuciones.
10. Calcular PPM y obligaciones mensuales, con aprobacion y safety gates para pagos.
11. Preparar renta anual, DDJJ, F22 y certificados desde datos acumulados durante el ano.
12. Operar con seguridad, observabilidad, backups, restore, runbook y evidencias.

Un modulo existente no se considera listo solo porque compile. Debe estar conectado al flujo, probado con datos reales o controlados, documentado y auditado.

## 8.0 Reglas funcionales que no deben perderse

Renta mensual:

1. Obtener monto base desde periodo contractual vigente.
2. Convertir UF a CLP solo con UF exacta de la fecha definida por la regla aplicable.
3. Aplicar ajustes vigentes antes del codigo.
4. Truncar decimales; no redondear salvo politica futura emitida formalmente.
5. Validar minimo operativo.
6. Aplicar codigo de conciliacion efectivo solo a contratos activos y solo dentro de la seccion/cuenta correcta.
7. Persistir monto calculado, moneda, UF usada, fecha efectiva y fuente.
8. La diferencia generada por insertar/reemplazar el codigo efectivo se conserva como efecto operativo auditable, no como mora, descuento, interes ni error silencioso.
9. El codigo de conciliacion se aplica al total exigible del periodo, incluyendo arriendo, cuota de repactacion, ajustes y otros conceptos habilitados, despues de validar reglas y evidencia.

Contratos:

- Un contrato conserva identidad y se extiende por periodos contractuales.
- Un contrato cubre una propiedad o una pareja principal + vinculada.
- Una propiedad vinculada no puede tener contrato activo independiente.
- Un contrato futuro requiere aviso de termino vigente o terminacion anticipada ejecutada.
- Un aviso de termino fuera de plazo se registra y alerta; no se oculta ni se corrige inventando fechas.
- Un aviso de termino es oportuno solo si su timestamp real de registro cae dentro del plazo contractual hasta `23:59:59` del ultimo dia permitido; no se ajusta retroactivamente.
- Si existe conflicto entre aviso, renovacion automatica ya ejecutada y contrato futuro, el sistema debe exigir resolucion guiada con chequeo de integridad; no cancela ni reescribe automaticamente efectos ya producidos.
- Contratos retroactivos no reconstruyen pagos ficticios de meses cerrados ni envian cobros automaticos por meses pasados.
- Si un contrato retroactivo se registra despues del dia 5 del mes operativo, debe alertar posible notificacion manual y no inventar cobranza pasada.
- Los descuentos, tramos y ajustes no pueden reducir el monto operativo bajo CLP 1.000 o equivalente validado.
- Los ajustes ordinarios se aplican por mes completo; no se prorratean por dias salvo termino, inicio excepcional o decision auditada.
- Si un contrato con tramos se renueva, la base por defecto es el ultimo tramo vigente, salvo politica documentada distinta.
- La terminacion anticipada permite tratamiento parcial del ultimo mes solo con regla o decision auditada.
- `CodeudorSolidario` opera con snapshot inmutable y maximo 3 por contrato, salvo nueva emision formal del PRD.

Garantias, deuda y cobranza residual:

- La garantia pertenece al contrato, no a la propiedad individual.
- Recepcion, retencion, aplicacion y devolucion de garantia generan eventos auditables y contables cuando corresponda.
- La garantia no genera intereses ni reajustes por defecto; se devuelve el monto recibido, salvo retencion/aplicacion formalmente documentada.
- Una garantia parcial puede operar, pero debe quedar visible como incompleta hasta regularizarse o aceptarse formalmente.
- El flujo normal es crear contrato, recibir garantia exigida o registrar excepcion, y solo entonces entregar llaves o registrar entrega bajo autorizacion auditada.
- Al cambiar arrendatario mediante termino y contrato nuevo, la garantia saliente y la garantia entrante se tratan como eventos separados.
- El sistema no crea gastos de devolucion de garantia automaticamente sin movimiento bancario, evidencia o resolucion manual.
- Si se recibe mas garantia que la pactada, el exceso no es utilidad ni ingreso libre: se clasifica, devuelve, regulariza o bloquea con evidencia y resolucion manual.
- Una repactacion no reescribe la deuda historica; por defecto cubre la deuda total acumulada y crea plan y cuotas trazables. Una repactacion parcial requiere excepcion formal y motivo auditable.
- La cobranza residual post-contrato usa referencia propia y no reutiliza el namespace de codigos de propiedad.
- `CodigoCobroResidual` usa referencia visible propia, formato `CCR-XXXXXX` con caracteres mayusculos no ambiguos, no rango `001-999` ni esquema historico `900-999`.
- Si el proveedor bancario entrega referencia o descripcion confiable para cobranza residual, el sistema puede hacer match exacto contra `CodigoCobroResidual`; si no, queda como resolucion manual auditada.
- Mientras una deuda este en repactacion activa, el pago original puede pasar a `EnRepactacion`; solo pasa a `PagadoViaRepactacion` cuando el plan completo se cumple, conservando dias de atraso para auditoria.

Documentos:

- El contrato principal, anexos, cartas, liquidaciones de garantia, respaldos tributarios y comprobantes formales viven en expediente documental.
- La notaria o firma avanzada no son regla universal; aplican segun politica documental configurada.
- La generacion documental usa plantilla versionada y vista previa antes de formalizar o enviar documentos sensibles.
- Si existe `CodeudorSolidario`, la politica documental define si su firma es obligatoria; el sistema no formaliza el documento si falta una firma requerida.
- Un documento no queda formalizado si faltan firmas, notaria o evidencia exigida por su politica.

Contabilidad:

- Todo hecho economico confirmado genera evento contable o queda pendiente de revision contable.
- Un mismo hecho economico no puede generar doble contabilizacion efectiva para la misma empresa, cuenta y periodo.
- Un asiento cerrado no se edita destructivamente; se corrige con reverso, asiento complementario o reapertura controlada.
- Un cierre mensual no se aprueba con eventos pendientes, asientos descuadrados o banco sin cuadrar.
- Todo mes operativo debe cerrar tambien como periodo contable antes de habilitar presentacion tributaria mensual.
- Movimientos bancarios detectados despues de un cierre aprobado no modifican el mes cerrado automaticamente; se tratan como periodo posterior, reclasificacion auditada o reapertura autorizada.
- La reapertura de mes requiere administrador autorizado, justificacion, efecto esperado, evidencia y `EventoAuditable`.

Clasificacion, pagos parciales y resolucion manual:

- Una conciliacion automatica solo puede cerrar un movimiento si la cuenta, contrato, periodo, arrendatario, referencia y regla de matching son consistentes.
- Un pago parcial no cierra conciliacion automatica. Si un pago llega parcial, duplicado, complementario o en varios abonos, el sistema puede sumarlo solo con regla segura, suma exacta y resolucion manual auditada.
- La clasificacion manual no es libre texto sin control: debe usar `CategoriaMovimiento`, entidad afectada, periodo economico, criterio de reparto, evidencia y motivo.
- Categorias criticas como garantia, PPM, transferencia interna, liquidacion a socio, reintegro, gasto pagado por entidad equivocada, cobranza residual y regularizacion requieren evidencia o bloqueo documentado.
- Toda reclasificacion conserva el movimiento original, clasificacion previa, usuario/proceso, motivo y efecto contable.

Reportes, dashboard y alertas:

- El dashboard operativo debe mostrar pagos pendientes, movimientos sin clasificar, diferencias banco/sistema, contratos por vencer, avisos de termino, garantias incompletas, fallas de integracion y cierres bloqueados.
- Los reportes de socio, contabilidad, tributacion, contrato y arrendatario deben derivar de datos fuente trazables, no de calculos pegados manualmente.
- Un reporte exportado debe registrar scope, usuario, fecha, motivo y expiracion cuando contenga datos sensibles.

Onboarding y datos de arrendatarios:

- Un arrendatario persona natural debe tener identidad, RUT, contacto, domicilio de notificacion, estado de contacto y, cuando el documento lo requiera, nacionalidad, estado civil y profesion.
- Un arrendatario empresa debe tener razon social, RUT, domicilio, contacto, representante legal y snapshot de datos del representante al momento de contratar.
- Los telefonos operativos deben validarse en formato internacional cuando se usen para mensajeria.
- Representantes legales, codeudores solidarios, contactos de pago y canales deben modelarse como informacion estructurada, no como notas informales.
- Si faltan datos obligatorios para operar, el contrato queda bloqueado o en preparacion; no se completan campos con supuestos.

Datos minimos de propiedad y contrato:

- Una propiedad debe conservar rol de avaluo cuando exista, direccion, comuna, region, tipo de inmueble, owner, codigo operativo y estado.
- Servicios, numero de cliente, gastos comunes y datos de administracion de comunidad se registran solo si aplican; no son texto libre perdido.
- Si una propiedad pertenece a comunidad, debe existir representacion vigente unica para comunicaciones, documentos y decisiones operativas.
- Empresas, comunidades y mandatos que firman o comunican documentos deben tener representante/autoridad operativa vigente y trazable.
- Un contrato debe registrar fecha de inicio, fecha fin vigente, fecha de entrega si difiere, dia de pago, plazo de notificacion, prealerta, estado, moneda, monto, tramos, gastos comunes y politica documental.
- Las plantillas de contrato pueden existir para acelerar captura, pero no reemplazan validaciones, datos reales ni expediente documental.

Estados y transiciones minimas:

- `Contrato`: PendienteActivacion -> Vigente; Vigente -> TerminadoAnticipadamente; Vigente -> Finalizado; Vigente -> Cancelado solo si no produjo efectos irreversibles.
- `PagoMensual`: Pendiente -> Pagado; Pendiente -> Atrasado; Atrasado -> EnRepactacion; EnRepactacion -> PagadoViaRepactacion; Pendiente/Atrasado -> PagadoPorAcuerdoDeTermino o Condonado solo con justificacion.
- `AvisoTermino`: Borrador -> Registrado; Registrado -> Cancelado solo si no existe contrato futuro activo sin revertir.
- `EventoContable`: PendienteContabilizacion -> Contabilizado; PendienteContabilizacion -> PendienteRevisionContable; PendienteRevisionContable -> Contabilizado.
- `CierreMensualContable`: Borrador -> Preparado; Preparado -> Aprobado; Aprobado -> Reabierto solo por administrador autorizado.
- `ConexionBancaria`: Verificando -> Activa; Verificando -> Pausada; Activa -> Pausada; Pausada -> Activa; Pausada/Activa -> Inactiva, con evidencia de gate.
- Toda transicion critica genera `EventoAuditable` o evidencia equivalente.

## 8.1 Modelo practico heredado del Excel legacy

El Excel legacy aporta la logica operativa diaria que LeaseManager debe reemplazar, no solo documentar. Sus reglas practicas se integran asi:

- Los abonos de arriendo se identifican usualmente por los ultimos tres digitos del monto, pero el match debe considerar tambien cuenta bancaria, seccion operativa, contrato activo, periodo, arrendatario y excepciones.
- El monto completo recibido se registra como pago real; si difiere del canon esperado, se conserva la diferencia como hecho auditable y no como error silencioso.
- Ingresos extraordinarios, reintegros, PPM pagados por error, garantias, transferencias internas y regularizaciones no se mezclan con arriendos normales.
- Todo gasto requiere entidad afectada, cuenta que pago, fecha, periodo economico, criterio de reparto y evidencia cuando exista.
- Las participaciones se modelan con vigencia temporal, no como formulas fijas de una hoja.
- La sucesion o redistribucion de participaciones debe quedar explicitamente modelada, incluyendo el caso operativo en que Catalina y Trinidad reciben por separado la participacion que correspondia a Cristian.
- La comision u honorario de administracion a Joaquin debe ser linea explicita de liquidacion, no una resta oculta.
- Los saldos finales por entidad deben cuadrar contra banco antes de cerrar el mes.
- Si una entidad tiene participacion economica en una propiedad cuyo dinero entro a otra cuenta, el sistema debe generar distribucion/transferencia trazada antes de considerarlo ingreso bancariamente conciliado de esa entidad.

Estas reglas hacen que el Excel sea fuente practica de negocio, pero no fuente tecnica de implementacion: no se copian celdas, se normaliza el funcionamiento.

Transicion Excel -> LeaseManager:

- `referencia`: el Excel explica reglas, casos historicos y criterios, pero LeaseManager aun no reemplaza operacion.
- `paralelo_controlado`: LeaseManager calcula y concilia en paralelo contra Excel/banco, sin ser fuente unica.
- `corte_operativo`: LeaseManager pasa a operar el mes corriente solo cuando la matriz de datos, banco, cobranza, facturacion aplicable, cierre y evidencia estan listos para ese alcance.
- `archivo_historico`: el Excel queda como respaldo y trazabilidad, no como fuente diaria de operacion.
- No se hace cutover desde Excel sin un mes controlado con saldo sistema igual a saldo banco por entidad, liquidaciones explicadas y bloqueadores registrados.
- Una liquidacion mensual por sociedad, comunidad o persona natural debe dejar la cuenta sin saldo operativo pendiente o con saldo final explicado, conciliado y trazable.
- El backfill historico no es default. Solo se ejecuta con alcance, preflight, snapshot, rollback, evidencia y confirmacion.

## 9. Etapas de cierre productivo

Etapa 1: datos reales, schema, contratos, propiedades, cuentas,
participaciones, facturacion esperada y matriz
contrato-propiedad-cuenta-facturacion contra base real o snapshot
real/controlado.

Etapa 2: cobranza, WebPay/Transbank, correos, recordatorios, mora y evidencia de ciclo controlado.

Etapa 3: Banco de Chile, movimientos por cuenta, conciliacion, clasificacion de excepciones y saldos cuadrados.

Etapa 4: SII/DTE 34, folios, firma, envio, estado aceptado/rechazado, reintentos y evidencia tributaria.

Etapa 5: cierre mensual, contabilidad, IFRS/GAAP, liquidaciones, PPM, pagos programados y reportes.

Etapa 6: renta anual, DDJJ, F22, certificados, reglas oficiales y validacion experta/oficial.

Etapa 7: operacion productiva, seguridad, dominio, deploy, crons, webhooks, observabilidad, backups, restore, runbook, aceptacion y corrida end-to-end.

No se avanza de etapa si el gate anterior esta bloqueado, salvo trabajo documental o preparatorio que no declare avance productivo.

## 10. Arquitectura tecnica de referencia

El root limpio verificado en mayo 2026 implementa el producto como monolito
modular con backend Django 5/DRF, PostgreSQL, Celery/Redis, frontend
React/TypeScript/Vite, integraciones controladas y jobs programados. Las
menciones heredadas a Next.js, Supabase o Vercel describen historia del root
anterior, no una obligacion tecnica vigente salvo ADR aceptado.

El PRD no debe congelar librerias como verdad de producto. La arquitectura tecnica puede evolucionar mediante ADR, siempre que conserve dominio, integridad financiera, seguridad, evidencia, gates y Definition of Done.

Reglas tecnicas minimas:

- Mutaciones sensibles en servidor, con validacion server-side.
- Auth, RBAC/scopes y permisos server-side para superficies internas.
- Credenciales privilegiadas solo en servidor y solo despues de
  autenticacion/autorizacion cuando aplique.
- Webhooks y crons fallan cerrado ante secreto, firma, timestamp, permisos o config faltante.
- Transacciones multi-tabla para operaciones financieras o contables.
- Idempotencia por periodo, cuenta, contrato, pago, movimiento, factura y job.
- Secretos fuera del repo y evidencia sin tokens, RUTs completos, cuentas completas, XMLs crudos ni payloads sensibles.
- Migraciones/backfills reales solo con preflight, backup, rollback y confirmacion.

Fallbacks y modo degradado:

- UF: Banco Central, CMF, MiIndicador o carga manual auditada; nunca default silencioso.
- Conciliacion bancaria: match exacto, asistido o manual auditado; nunca autoasignacion ambigua.
- Contabilidad: automatica, cola de revision o resolucion manual auditada; nunca asiento invisible.
- Mensajeria: WhatsApp gated, email base y alerta critica si no hay canal operativo.
- SII: capacidad abierta, borrador con revision humana u operacion manual controlada; nunca presentacion tributaria final sin gate y autorizacion.
- Banco: si falla proveedor, se opera con carga controlada y resolucion manual, manteniendo saldo sistema igual a saldo banco antes de cierre.
- Cache, colas o jobs pueden degradarse, pero no pueden ocultar bloqueos financieros, tributarios, contractuales o de seguridad.

## 11. Datos, evidencia y estados

Cada componente se clasifica como:

- resuelto_confirmado
- implementado_sin_evidencia
- parcial
- bloqueado_dato_real
- bloqueado_externo
- requiere_decision_usuario
- defectuoso
- duplicado
- desactualizado
- faltante

Lo correcto se conserva. Lo incompleto, incorrecto, debil, duplicado, desordenado, desactualizado, mal integrado o pendiente se corrige acotadamente.

Evidencia aceptable:

- Auditor reproducible.
- Resultado de build/type-check/test relevante.
- Snapshot real/controlado fuera del repo.
- Prueba de integracion controlada.
- Evidencia externa redactada.
- Registro de decision del usuario.
- Runbook o handoff actualizado.

Fechas auditables obligatorias:

- Fecha de movimiento bancario, fecha de deteccion/importacion, fecha de pago WebPay, fecha de devengo contable, fecha de emision DTE, fecha de aceptacion o rechazo SII, fecha UF usada, periodo contractual, periodo economico y periodo tributario son datos distintos.
- Si una fecha obligatoria falta o contradice otra fuente superior, el sistema bloquea calculo, conciliacion, factura, cierre o reporte afectado hasta resolver la diferencia.

La evidencia real/controlada que contenga datos, filas, payloads, XML, RUTs, cuentas, correos, tokens, secretos, dumps o respuestas crudas debe quedar fuera del repo/workspace. En el repo solo pueden quedar referencias redactadas, fingerprints, schemas, comandos, handoffs y resultados seguros.

No cuenta como cierre:

- Texto declarativo sin prueba.
- Codigo sin corrida.
- Mock no identificado.
- Screenshot sin origen.
- Self-test, evidencia sintetica o fixture que no este marcado como tal.
- Datos sensibles pegados en docs.
- Tarea historica marcada como completa.
- Dependencia externa asumida.
- Tipos generados, migraciones o schema local sin contraste contra base real, snapshot controlado o auditor reproducible.

## 12. Seguridad, privacidad y operacion

LeaseManager debe operar con minimo privilegio, RLS, 2FA/MFA administrativo o riesgo formal aceptado, rate limit, validacion de entrada, errores publicos seguros, logs internos controlados, audit_log, rotacion de secretos, backups, restore probado, monitoreo y runbook.

Las superficies publicas solo exponen DTOs publicos. Nunca deben exponer RUTs internos, cuentas bancarias, participaciones privadas, tasaciones, FKs sensibles, mensajes internos de excepcion ni estado detallado de configuracion.

Los reportes y evidencias deben ser trazables a su fuente y redactados si contienen datos reales.

Portal publico y superficies anonimas:

- El portal publico, mapa, buscador y fichas solo usan datos publicos aprobados; no filtran FKs, RUTs, cuentas, participaciones, tasaciones ni estados internos.
- El mapa publico no inventa coordenadas ni ubicaciones. Si no existe geocodificacion confiable, debe mostrar direccion/comuna publica, enlace de busqueda externo o estado seguro de ubicacion no disponible.
- Un error de carga de backend, base de datos o permisos no puede convertirse
  silenciosamente en lista vacia; debe mostrarse estado seguro al usuario y
  registrarse detalle interno.
- Un error publico no debe exponer `error.message` interno, stack trace, payloads, nombres de tablas, claves, policies ni configuracion.
- Endpoints financieros, estadisticas internas, reportes y APIs con service role requieren autenticacion, autorizacion por rol y scope antes de crear clientes privilegiados.
- Los placeholders visuales solo son aceptables como estado grafico generico; no pueden reemplazar funciones reales, datos obligatorios, mapas ni evidencia.

Data protection y continuidad:

- Los datos deben clasificarse al menos como operativo, financiero, tributario, documental sensible o secreto.
- Los exports sensibles quedan cifrados o protegidos, con motivo, scope, usuario, expiracion y evidencia.
- Si la plataforma opera despues del 1 de diciembre de 2026 y la normativa vigente exige nuevas condiciones de datos personales, debe existir gate `Compliance.DatosPersonalesChile2026` abierto o bloqueo formal aceptado.
- Objetivo operacional inicial: `RPO 24h` y `RTO 4h`, sujeto a infraestructura real validada.
- Backups incrementales diarios y completos semanales para base de datos y storage documental, con prueba de restore.
- Observabilidad minima: salud de integraciones y gates, latencia de calculo mensual, fallos documentales, colas/tareas, movimientos sin match, bloqueos de mensajeria, reaperturas de mes, webhooks fallidos y crons fallidos.
- Un error aislado de propiedad, contrato o integracion no debe ocultar el problema ni bloquear procesamiento masivo completo si puede aislarse con evidencia.

## 13. Reglas de aceptacion global

LeaseManager Produccion 1.0 se considera listo solo si:

- Todos los modulos obligatorios estan implementados o confirmados.
- Todas las integraciones requeridas estan conectadas o formalmente bloqueadas/aceptadas sin saltar gates.
- La matriz contrato-propiedad-cuenta-facturacion esta validada con datos reales o snapshot controlado.
- La cobranza, banco, SII, cierre mensual, ciclo anual y operacion productiva tienen evidencia.
- No hay datos inventados ni placeholders en flujos reales.
- No quedan duplicaciones innecesarias de maestros, propiedades, contratos o reglas.
- No hay contradicciones entre PRD, arquitectura, gates, ADR, codigo y datos verificados.
- Build, type-check, auditores de etapa y auditor global pasan o registran bloqueadores exactos.
- Backup/restore, runbook, dominio, crons, webhooks, seguridad y aceptacion estan probados.

Si algo obligatorio no cumple, el estado final debe ser bloqueo exacto, riesgo y proxima accion, no declaracion de termino.

Escenarios transversales obligatorios:

1. Contrato estandar de una propiedad con UF/CLP, codigo efectivo, cobro, conciliacion y asiento.
2. Contrato con propiedad principal + vinculada, un solo cobro, una garantia y trazabilidad por propiedad.
3. Renovacion por periodo contractual sin duplicar contrato.
4. Cambio de arrendatario mediante termino y contrato nuevo, conservando deuda historica.
5. Contrato retroactivo sin reconstruir pagos ficticios de meses cerrados.
6. Falla de proveedor bancario con modo degradado, carga controlada y `ResolucionManual`.
7. Garantia recibida, incompleta, devuelta parcialmente, retenida y cerrada con evidencia.
8. `AvisoTermino` con contrato futuro y bloqueo de renovacion automatica.
9. Deuda residual con referencia propia sin colisionar con codigos de propiedad.
10. Email operativo con WhatsApp suspendido o bloqueado, sin perder notificacion critica.
11. Cierre mensual contable aprobado con banco cuadrado, asientos balanceados y PPM/F29 preparado solo si aplica.
12. DDJJ y F22 preparados desde doce cierres mensuales aprobados.
13. SII con DTE 34 abierto y presentaciones finales cerradas por gate.
14. Reverso o asiento complementario posterior a cierre aplicado segun politica.
15. Exportacion sensible fuera de scope rechazada por permisos.
16. Empresa fuera de regimen soportado bloqueada para automatizacion tributaria oficial.
17. Bulnes 699, Parking E49 y Edificio Q/1014 ejecutados sin duplicar propiedades ni hardcodear montos.

## 14. Puntos que requieren verificacion antes de convertir este candidato en vigente

- Confirmar si este PRD candidato reemplazara formalmente al PRD Canonico de marzo 2026 o si convivira como PRD de production-readiness.
- Migrar el set vigente fuera del repo anidado a rutas limpias del root profesional.
- Resolver la tension documental entre PRD de producto y Arquitectura Maestra: el PRD define producto; la arquitectura define camino integral, capas, gates y Definition of Done.
- Confirmar con datos reales o snapshot controlado la Etapa 1 antes de permitir avance productivo.
- Validar reglas tributarias anuales contra SII/normativa vigente o experto.
- Confirmar si las capacidades podadas siguen fuera del boundary activo.
- Reconciliar las menciones heredadas del root Next.js/Supabase/Vercel con
  `ADR_STACK_FINAL.md` y el root limpio Django/React antes de convertir este
  candidato en vigente.
- Aceptar o corregir este documento por el usuario antes de marcarlo como vigente.

## 15. Como continuar sin arrastrar desorden

Antes de continuar desarrollo funcional, LeaseManager debe pasar por una fase de ordenamiento profesional. Esta fase no es avance productivo; es preparacion necesaria para que el avance posterior sea confiable.

El plan rector de esa transicion vive en `docs/product/PLAN_ORDENAMIENTO_PROFESIONAL_MAYO_2026.md` y exige:

- proteger el estado actual mediante savegame;
- separar fuente vigente, candidatos, anexos e historicos;
- mover el set rector a rutas limpias;
- aislar herencia operativa y repos anidados;
- definir estructura profesional de carpetas;
- clasificar cambios pendientes antes de migrarlos;
- versionar en Git con commits pequenos;
- validar build, type-check y auditores despues de cada paquete;
- reanudar avance solo por etapas y gates.

Regla de continuidad:

```text
Primero ordenar la base del proyecto; luego cerrar Etapa 1 con datos reales/controlados; despues continuar las etapas restantes. No se debe mezclar limpieza de herencia, migracion documental, features nuevas y declaracion de avance productivo en el mismo paquete.
```

Si este PRD se acepta como rector, el proyecto debe continuar desde una base limpia o controlada, no desde una masa anonima de cambios pendientes.
