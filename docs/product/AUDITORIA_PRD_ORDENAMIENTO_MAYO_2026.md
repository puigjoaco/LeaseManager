# Auditoria PRD y Ordenamiento Mayo 2026

Estado: auditoria documental aceptada y promovida.
Fecha: 2026-05-20.

## 1. Alcance

Esta auditoria revisa el set documental que permitio promover el PRD Canonico Mayo 2026 y guiar el ordenamiento profesional de LeaseManager antes de continuar desarrollo funcional.

Documentos revisados:

- `docs/product/PRD_CANONICO_MAYO_2026_CANDIDATO.md`
- `docs/product/ANEXO_MODELO_OPERATIVO_EXCEL_MAYO_2026.md`
- `docs/product/PLAN_ORDENAMIENTO_PROFESIONAL_MAYO_2026.md`
- `docs/product/PRD_CANONICO_MAYO_2026_AUDITORIA_FUENTES.md`
- `AGENTS.md`

## 2. Pregunta auditada

El set debe responder claramente:

- que producto se quiere terminar;
- que funcionamiento practico debe absorberse desde el Excel;
- que arquitectura y gates gobiernan el avance;
- que se conserva, que se descarta y que queda historico;
- como se ordena el repo antes de seguir;
- cuando se puede volver a construir producto;
- como se evita arrastrar herencia, duplicaciones o decisiones antiguas.

## 3. Resultado

Resultado: `aceptado_y_promovido_como_prd_vigente`.

El set documental ya fue aceptado por el usuario y el PRD Mayo 2026 fue
promovido a `01_Set_Vigente/PRD_CANONICO.md`. Esto cierra la ambiguedad de
fuente rectora, pero no cierra ninguna etapa productiva.

## 4. Hallazgos cerrados en esta pasada

### H-001 - Faltaba decision recomendada sobre base limpia

Estado anterior: el plan decia crear o usar carpeta limpia, pero dejaba la decision demasiado abierta.

Correccion: se establecio como recomendacion crear `D:/Proyectos/LeaseManager-clean` desde una base Git limpia y mantener el root actual como fuente de rescate/savegame.

### H-002 - Faltaban gates minimos del baseline

Estado anterior: el plan pedia validar, pero no enumeraba comandos minimos.

Correccion: se agregaron gates minimos: `type-check`, `build`, `audit:production-docs-index`, `audit:stage1:local-self-tests` y `audit:session-status:markdown`.

### H-003 - Faltaba Definition of Ready para retomar desarrollo

Estado anterior: el plan definia Definition of Done del ordenamiento, pero no el punto exacto donde se permite volver a construir features.

Correccion: se agrego Definition of Ready para retomar desarrollo funcional mayor.

### H-004 - Faltaba registro requerido por cambio migrado

Estado anterior: la clasificacion de cambios existia, pero podia quedar informal.

Correccion: se agrego registro minimo por archivo/grupo: origen, destino, razon, estado, prueba, riesgo residual y commit.

### H-005 - Faltaba primera ejecucion concreta

Estado anterior: el plan decia los pasos generales, pero no el entregable de la primera corrida.

Correccion: se agrego una primera ejecucion concreta con salida esperada y acciones prohibidas.

### H-006 - PRD candidato demasiado resumido frente al canónico vigente

Estado anterior: el PRD candidato cubria el producto, pero omitía detalles estructurales importantes del PRD canonico vigente y de los 26 PRD fuente: mandato operativo, identidad de envio, expediente documental, codeudores, contrato futuro, deuda, repactacion, cobranza residual, politicas v1, retencion documental y reglas de estados criticos.

Correccion: se agregaron secciones de invariantes/policies v1, modelo de dominio obligatorio y reglas funcionales que no deben perderse.

### H-007 - Anexo Excel no cubria pruebas de garantias, UF y periodo economico

Estado anterior: el anexo Excel cubria matching, gastos, repartos y cierre, pero faltaban pruebas explicitas para UF aplicada, garantias y liquidaciones pagadas en mes siguiente.

Correccion: se agregaron pruebas obligatorias para UF/fecha efectiva, garantias y periodo economico de liquidaciones.

### H-008 - Faltaban roles, clasificacion protegida, resolucion manual y modo degradado

Estado anterior: el PRD candidato mencionaba seguridad, roles y clasificacion, pero no dejaba suficientemente explicitos los scopes por rol, las categorias criticas de movimiento, la trazabilidad de reclasificaciones, los pagos parciales, las alertas de dashboard ni los fallbacks canonicos.

Correccion: se agregaron reglas de acceso, `CategoriaMovimiento`, `ResolucionManual`, pagos parciales, dashboard/alertas, onboarding de arrendatarios, categorias protegidas en el anexo Excel y modo degradado controlado.

### H-009 - Faltaban requisitos no funcionales medibles

Estado anterior: el PRD candidato mencionaba seguridad, backups y operacion, pero perdia detalle del set canonico sobre localizacion, indicadores iniciales, ventana de mensajeria, data protection, RPO/RTO, cadencia de backups y observabilidad minima.

Correccion: se agregaron localizacion operativa, indicadores no funcionales, reglas de mensajeria, clasificacion de datos, gate de datos personales cuando aplique, RPO/RTO, backups diarios/semanales y observabilidad minima.

### H-010 - Faltaba baseline real de entidades sin datos sensibles

Estado anterior: el PRD candidato describia empresas, socios y cuentas como categorias, pero no amarraba suficiente el documento al negocio real de LeaseManager.

Correccion: se agrego una matriz operacional real inicial con sociedades base, socios/personas naturales, cuentas por entidad, proteccion de RUTs/cuentas, IFRS/GAAP y separacion de contabilidad personal.

### H-011 - AGENTS podia presentar una revision UI historica como estado vigente

Estado anterior: `AGENTS.md` conservaba una seccion de enero 2026 con frase de estado cerrado que podia confundirse con validacion actual.

Correccion: se marco como nota historica y se aclaro que no reemplaza gates actuales, build, type-check, auditorias ni validacion visual vigente.

### H-012 - Faltaba acceptance ejecutable transversal

Estado anterior: el PRD candidato tenia aceptacion global, pero no listaba escenarios transversales suficientes para probar que el producto esta realmente listo de punta a punta.

Correccion: se agregaron escenarios obligatorios de contrato, propiedad vinculada, renovacion, cambio de arrendatario, retroactivo, banco degradado, garantias, aviso de termino, deuda residual, canales, cierre mensual, renta anual, SII, reversos, permisos y casos especiales.

### H-013 - Faltaba glosario canonico operacional

Estado anterior: el PRD candidato cubria contextos, pero no nombraba suficientes conceptos canónicos del PRD vigente: `CuentaRecaudadora`, `ProviderBancario`, `FuenteUF`, `CanalMensajeria`, `CapacidadTributariaSII`, `ConfiguracionFiscalEmpresa`, `EventoContable`, `ReglaContable`, `CierreMensualContable`, `ProcesoRentaAnual`, libros derivados, politicas documentales/contables, `EventoAuditable` y `CodigoCobroResidual`.

Correccion: se agrego un glosario canonico minimo con capacidades conceptuales obligatorias, sin congelar nombres fisicos de tablas si el schema real ya decidio otra nomenclatura equivalente.

### H-014 - Faltaban reglas finas de contratos, garantias y datos minimos

Estado anterior: el PRD candidato mencionaba contratos, garantias, codeudores y onboarding, pero no recogia suficientemente reglas repetidas en los 26 PRD fuente: no redondear, no cobros automaticos pasados en retroactivos, alerta posterior al dia 5, ajustes sin bajar de CLP 1.000, tramos, garantia parcial, entrega de llaves, datos estructurados de arrendatario/representante/codeudor, servicios/gastos comunes y transiciones minimas.

Correccion: se agregaron reglas funcionales mas precisas de renta mensual, contratos retroactivos, ajustes/tramos, garantias, datos minimos de propiedad/contrato/arrendatario y estados/transiciones criticas.

### H-015 - Faltaban estados y capacidades canónicas de cierre

Estado anterior: el glosario agregado aun no explicitaba estados de pago, estados tributarios, capacidades SII separadas, formato `CCR-XXXXXX`, distribucion de cobro, conexion bancaria ni documentos emitidos.

Correccion: se agregaron capacidades SII por gate, conceptos `PagoMensual`, `DistribucionCobroMensual`, `EstadoCuentaArrendatario`, `DocumentoEmitido`, `AsignacionCanalOperacion`, `ConexionBancaria`, `EstadoPreparacionTributaria`, formato de `CodigoCobroResidual` y transiciones de pago/conexion bancaria.

### H-016 - Anexo Excel necesitaba regla para gasto masivo

Estado anterior: el anexo cubria gastos y clasificacion, pero no impedia que una carga masiva aplicara formulas o porcentajes globales sin validar cada gasto.

Correccion: se agrego regla de ingreso masivo de gastos: puede acelerar captura, pero cada gasto conserva monto, propiedad/entidad, detalle, categoria, periodo y evidencia.

### H-017 - Faltaban reglas explicitas para portal publico y mapa

Estado anterior: el PRD candidato hablaba de superficies publicas y DTOs, pero no recogia con suficiente precision aprendizajes recientes del proyecto: no inventar coordenadas, no mostrar placeholders tecnicos como funcion real, no convertir errores de carga en lista vacia y no exponer mensajes internos.

Correccion: se agregaron reglas de portal publico, mapa, errores seguros, endpoints financieros/estadisticas con auth/rol/scope y uso permitido de placeholders visuales.

### H-018 - Plan no definia promocion del candidato a vigente

Estado anterior: el plan pedia aceptar o corregir el PRD candidato, pero no fijaba el procedimiento para convertirlo en PRD vigente sin dejar dos fuentes compitiendo.

Correccion: se agrego procedimiento de promocion: crear documento vigente, conservar candidato como trazabilidad o enlace, mover PRD previo a historico limpio, actualizar indices/AGENTS y registrar decision.

### H-019 - Faltaba frontera explicita de MineralBalance

Estado anterior: el PRD candidato exigia validacion contra SII/normativa/experto, pero no nombraba expresamente el material tributario vecino que el proyecto usa como apoyo.

Correccion: se agrego que `MineralBalance/aula-tributaria-at2026` puede apoyar diseno tributario, pero no es fuente normativa final, no abre gates y no se convierte en regla sin validacion oficial/experta.

### H-020 - Faltaba formalizar GateExterno y capacidades de matriz vigente

Estado anterior: el PRD candidato hablaba de gates, pero no explicitaba `GateExterno` ni la lista minima de capacidades externas de la matriz vigente.

Correccion: se agregaron `GateExterno`, gates bancarios, UF, Email, WhatsApp, SII por capacidad, compliance de datos personales y regla de capacidades podadas.

### H-021 - Faltaban reglas de evidencia fuera del repo

Estado anterior: el PRD candidato prohibia datos sensibles en docs, pero no decia con suficiente fuerza que la evidencia real/controlada debe quedar fuera del repo/workspace.

Correccion: se agrego regla de evidencia externa redactada/fingerprints y se aclaro que self-tests, evidencia sintetica, fixtures y schema local no cierran etapas sin contraste real/controlado.

### H-022 - Faltaban conceptos contables/documentales y aprobaciones criticas

Estado anterior: el PRD candidato ya cubria contabilidad y documentos, pero no nombraba de forma expresa `MatrizReglasContables`, `CuentaContable`, `CentroResultado`, `hash_integridad`, flujo PDF canonico, capacidades SII podadas ni aprobaciones criticas como pago ambiguo, cambio de gate y exportacion masiva sensible.

Correccion: se agregaron esos conceptos al glosario operativo, se reforzo `DocumentoEmitido` y se definieron aprobaciones criticas para `AsignacionManualPagoAmbiguo`, `CambioDeGateSII`, `CambioDeGateComplianceDatos2026` y `ExportacionMasivaDeDatosSensibles`.

### H-023 - Faltaba resolver conflictos entre fuentes, fechas y corte desde Excel

Estado anterior: el PRD candidato listaba fuentes, pero no definia con suficiente precision que fuente gana cuando hay discrepancias ni separaba todas las fechas criticas del flujo financiero/tributario. Tambien describia reemplazo del Excel, pero faltaba un estado de transicion controlada.

Correccion: se agrego jerarquia de conflicto entre fuentes, fechas auditables obligatorias y transicion `referencia -> paralelo_controlado -> corte_operativo -> archivo_historico`, incluyendo regla de no cutover sin mes cuadrado contra banco.

### H-024 - Faltaban reglas operativas finas de socios, empresas, pagos y garantias

Estado anterior: el PRD candidato cubria entidades, pagos parciales, repactacion y garantias, pero no cerraba casos repetidos en los PRD fuente: socio con participaciones activas, empresa sin cuenta bancaria, disolucion, codigo aplicado al total exigible, repactacion por deuda total, garantia excedente y ajustes por mes completo.

Correccion: se agrego gobierno de socios/empresas/cuentas, regla de cuenta activa para operar, disolucion controlada, pagos parciales sin cierre automatico, codigo sobre total exigible, repactacion por defecto sobre deuda total, garantia excedente como caso a clasificar/devolver/regularizar y ajustes ordinarios por mes completo.

### H-025 - Plan no aislaba suficientemente scripts legacy riesgosos

Estado anterior: el plan decia que scripts riesgosos no migran sin dry-run, pero no nombraba patrones concretos que ya aparecen en la historia del repo.

Correccion: se agrego cuarentena para scripts legacy con service role amplio, `select('*')`, hardcodes, tokens, errores internos o escrituras directas, y regla para no clasificar runtime inseguro como `migrar_ahora` sin prueba y correccion.

### H-026 - Faltaban reglas finas de score, WhatsApp, permisos y meses cerrados

Estado anterior: el PRD candidato mencionaba score, WhatsApp, roles y cierre mensual, pero no recogia suficientes detalles repetidos en los PRD fuente: pago a tiempo hasta vencimiento inclusive, score con repactacion, bloqueo/rehabilitacion de WhatsApp, permisos de socio por participacion/grant, exclusion de secretos para roles no autorizados y regla de no mutar meses cerrados automaticamente.

Correccion: se agregaron esas reglas como policies y reglas de acceso/contabilidad, manteniendo email como respaldo y reapertura de mes solo con administrador autorizado, justificacion, evidencia y evento auditable.

### H-027 - Faltaba precision final en cobranza residual y vencimientos

Estado anterior: el PRD candidato ya definia `CodigoCobroResidual`, deuda y estados de pago, pero no recogia completamente la precision del PRD vigente sobre formato canonico, match por referencia bancaria confiable, estado `EnRepactacion`/`PagadoViaRepactacion` y ausencia de dias de gracia ocultos.

Correccion: se agrego formato `CCR-XXXXXX` con caracteres mayusculos no ambiguos, match exacto si el proveedor bancario entrega referencia confiable, conservacion de dias de atraso en repactaciones, paso a `PagadoViaRepactacion` solo con plan completo y regla de no inventar feriados, dias de gracia ni extensiones tacitas.

### H-028 - Plan conservaba una ruta operativa no neutral para contextos

Estado anterior: el mapa de estructura objetivo mantenia una ruta interna historica para contextos, lo que podia perpetuar dependencia de carpeta operativa en la base limpia.

Correccion: se reemplazo por `docs/context/` como destino neutral para contextos vigentes, dejando historicos aislados.

### H-029 - Faltaban restricciones exactas de mandato, comunidad y tributacion

Estado anterior: el PRD candidato ya mencionaba mandato, comunidad, cuenta recaudadora y configuracion fiscal, pero no recogia con suficiente exactitud reglas del PRD vigente: propiedad con owner unico, comunidad con una representacion activa, participantes permitidos por tipo de owner, cuenta recaudadora perteneciente al recaudador, mandato previo a activar contrato y bloqueo tributario si falta configuracion fiscal.

Correccion: se agregaron esas restricciones al bloque de invariantes, gobierno de entidades, `MandatoOperacion`, `IdentidadDeEnvio` y `ConfiguracionFiscalEmpresa`.

### H-030 - Faltaban controles finos de renovacion, documentos y contabilidad

Estado anterior: el PRD candidato cubria avisos, documentos y cierre mensual, pero faltaban precisiones de fuente: timestamp real hasta `23:59:59` para aviso oportuno, resolucion guiada ante conflicto aviso/renovacion/contrato futuro, plantilla documental versionada con vista previa, firma de codeudor segun politica, no doble contabilizacion y cierre contable antes de presentacion tributaria mensual.

Correccion: se agregaron esas reglas al PRD candidato y se reforzo el anexo Excel con referencias internas unicas para ingresos/gastos manuales.

### H-031 - Faltaban nombres canonicos y limites de recaudacion

Estado anterior: algunas capacidades estaban cubiertas por regla, pero no con los nombres canonicos del PRD vigente: `Recaudador`, `EntidadFacturadora`, `ParticipacionPatrimonial`, `RepresentacionComunidad` y `EmpresaContabilidadCompletaV1`. Tambien faltaba explicitar que una propiedad activa cobra por una sola `CuentaRecaudadora`, que el namespace de codigo embebido soporta maximo 999 codigos activos y que F29/DDJJ/F22 consumen solo obligaciones habilitadas por `ConfiguracionFiscalEmpresa`.

Correccion: se agregaron esos conceptos, limites y restricciones operativas al PRD candidato.

### H-032 - Faltaban capacidades canónicas de cierre y retencion

Estado anterior: el PRD candidato cubria deuda, garantias, reapertura, retencion y F29 por reglas dispersas, pero no nombraba algunas capacidades del PRD vigente que ayudan a cerrar implementacion y auditoria: `IngresoDesconocido`, `RepactacionDeuda`, `HistorialGarantia`, `CierreMensualContableYTributario`, `ReaperturaDeMes` y `PoliticaRetencionDatos`. Tambien faltaba explicitar que `F29Preparacion` nace del ledger interno y no de copiar una propuesta externa sin contraste.

Correccion: se agregaron esas capacidades al glosario, se reforzo `ReaperturaDeMes` como aprobacion critica y se declaro que F29 se prepara desde ledger, obligaciones y configuracion interna validada.

### H-033 - Faltaban alias canonicos para roles, contratos, ledger y salidas tributarias

Estado anterior: el PRD candidato describia roles, contratos, garantias, asientos y salidas tributarias, pero no preservaba varios nombres canonicos utiles del PRD vigente: `AdministradorGlobal`, `AdministradorOperativo`, `OperadorDeCartera`, `RevisorFiscalExterno`, `ContratoPrincipal`, `PeriodoContractual`, `AjusteContrato`, `GarantiaContractual`, `MotorContable`, `MovimientoAsiento`, `SalidaTributariaMensualFinal`, `SalidaTributariaAnualFinal` y `PresentacionAnualFinal`.

Correccion: se agregaron como alias/capacidades conceptuales sin abrir alcance nuevo ni importar stack historico.

## 5. Cobertura actual

| Area | Estado |
|---|---|
| Producto objetivo | Cubierto por PRD candidato |
| Funcionamiento practico del negocio | Cubierto por anexo Excel |
| Arquitectura end-to-end | Cubierta por Arquitectura Maestra referenciada |
| Ordenamiento profesional | Cubierto por plan de ordenamiento |
| Jerarquia documental | Cubierta por PRD y AGENTS |
| Separacion de herencia | Cubierta por AGENTS y plan |
| Git y baseline limpio | Cubierto por plan |
| Gates minimos | Cubierto por plan |
| Retomar desarrollo | Cubierto por Definition of Ready |
| Bloqueo Etapa 1 | Reconocido por PRD y plan |
| Dominio contractual avanzado | Cubierto por PRD candidato |
| Deuda, repactacion y residual | Cubierto por PRD candidato |
| Expediente documental | Cubierto por PRD candidato |
| Retencion y exports sensibles | Cubierto por PRD candidato |
| Roles, scopes y exports | Cubierto por PRD candidato |
| Clasificacion protegida | Cubierto por PRD candidato y anexo Excel |
| Resolucion manual auditada | Cubierto por PRD candidato |
| Dashboard y alertas operativas | Cubierto por PRD candidato |
| Modo degradado/fallbacks | Cubierto por PRD candidato |
| Requisitos no funcionales | Cubierto por PRD candidato |
| Continuidad, backups y restore | Cubierto por PRD candidato |
| Data protection y exports | Cubierto por PRD candidato |
| Baseline real de entidades | Cubierto por PRD candidato sin exponer cuentas/RUTs completos |
| AGENTS alineado al ordenamiento | Cubierto por AGENTS y esta auditoria |
| Acceptance ejecutable transversal | Cubierto por PRD candidato |
| Glosario canonico operacional | Cubierto por PRD candidato |
| Datos minimos y transiciones | Cubierto por PRD candidato |
| Estados/capacidades canónicas | Cubierto por PRD candidato |
| Gasto masivo controlado | Cubierto por anexo Excel |
| Portal publico y mapa | Cubierto por PRD candidato |
| Promocion candidato a vigente | Cubierto por plan de ordenamiento |
| MineralBalance como apoyo no normativo | Cubierto por PRD candidato |
| GateExterno y matriz de capacidades | Cubierto por PRD candidato |
| Evidencia real/controlada fuera del repo | Cubierto por PRD candidato |
| Contabilidad/documentos/aprobaciones criticas | Cubierto por PRD candidato |
| Jerarquia de conflicto entre fuentes | Cubierto por PRD candidato |
| Transicion Excel a LeaseManager | Cubierto por PRD candidato |
| Fechas auditables separadas | Cubierto por PRD candidato |
| Gobierno de socios/empresas/cuentas | Cubierto por PRD candidato |
| Pagos parciales, repactacion y garantia excedente | Cubierto por PRD candidato |
| Cuarentena de scripts legacy riesgosos | Cubierto por plan de ordenamiento |
| Score, WhatsApp, permisos y meses cerrados | Cubierto por PRD candidato |
| Cobranza residual y vencimientos | Cubierto por PRD candidato |
| Contextos en ruta neutral | Cubierto por plan de ordenamiento |
| Mandato, comunidad y tributacion | Cubierto por PRD candidato |
| Renovacion, documentos y contabilidad fina | Cubierto por PRD candidato y anexo Excel |
| Nombres canonicos y limites de recaudacion | Cubierto por PRD candidato |
| Cierre, retencion, garantias y F29 interno | Cubierto por PRD candidato |
| Alias canonicos de roles, contratos, ledger y salidas tributarias | Cubierto por PRD candidato |

## 6. Riesgos pendientes

- Etapa 1 sigue bloqueada hasta base real valida o snapshot real/controlado.
- Los ADR activos pueden contener decisiones tecnicas historicas que deben reemitirse para el stack real.
- Las reglas tributarias deben validarse contra SII, normativa vigente o experto.
- Las integraciones externas siguen cerradas o condicionadas por gates.

## 7. Veredicto

El set documental ya puede usarse como base rectora del proyecto, pero no para
declarar producto listo. La siguiente accion correcta es avanzar Etapa 1 con
datos reales o snapshot controlado, ejecutar gates minimos y mantener cada
avance en worktrees por frente.
