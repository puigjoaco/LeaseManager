# Matriz de Consolidación Temática

## 1. Propósito

Esta matriz conecta las fuentes históricas con las decisiones canónicas del producto. No reemplaza al maestro ni a la auditoría por versión:

- [PRD_MAESTRO_DEFINITIVO.md](D:/Proyectos/PRDLeaseManager/PRD_MAESTRO_DEFINITIVO.md) define la norma vigente.
- [AUDITORIA_PRDS_1_26.md](D:/Proyectos/PRDLeaseManager/AUDITORIA_PRDS_1_26.md) explica la evolución por versión.
- Esta matriz explica la consolidación **por tema**.

## 2. Lectura de la matriz

Columnas:

- `Tema`: dominio o área funcional.
- `Subtema`: problema específico consolidado.
- `Versiones fuente`: PRD donde aparece el tema o la tensión.
- `Tensión detectada`: conflicto, ambigüedad o evolución relevante.
- `Decisión canónica`: resolución final adoptada.
- `Razón de decisión`: por qué ganó esa opción.
- `Sección final del maestro`: dónde quedó plasmada.
- `Gaps cerrados por criterio experto`: mejoras añadidas al consolidar.

## 3. Matriz

| Tema | Subtema | Versiones fuente | Tensión detectada | Decisión canónica | Razón de decisión | Sección final del maestro | Gaps cerrados por criterio experto |
|---|---|---|---|---|---|---|---|
| Dominio | Socios y participaciones | `prd1`, `prd2`, `prd13-16`, `prd24-25` | Validaciones presentes, pero dispersas y con distinta dureza | participaciones siempre suman `100%`; socio con participación activa no se elimina | evita corrupción patrimonial y mantiene trazabilidad | `7.1`, `8.1`, `8.15` | wizard de transferencia como vía correcta de salida |
| Dominio | Empresas y representante legal | `prd2`, `prd13-16`, `prd21`, `prd24-25`, `prd26` | presencia desigual de representante legal, cuentas activas y operatividad | empresa requiere representante legal y cuenta operativa | coherencia jurídica y operativa | `7.2`, `7.4`, `8.15` | separación clara entre propiedad, sociedad y operatividad bancaria |
| Dominio | Cuenta bancaria y códigos | `prd4`, `prd13-15`, `prd23-25`, `PRD_UNIFICADO` | `001-999` vs `001-899`; unicidad local vs global | códigos `001-999` únicos por cuenta bancaria | es la regla más consistente y útil para conciliación | `7.3`, `7.5`, `16.2`, `20` | eliminación del rango arbitrario `001-899` |
| Integración bancaria | Modelo de conexión | `prd1-25`, `prd26`, `CLAUDE.md` | usuario/clave de portal y 2FA vs integración oficial | `Conexión bancaria oficial` reemplaza credenciales de portal | mejora seguridad, defendibilidad y coherencia con reglas actuales | `7.4`, `10.1`, `20` | estados de conexión y gate estricto |
| Contratos | Identidad y renovación | `prd2`, `prd10`, `prd13-26`, `prd25` | renovar creando contrato nuevo vs extender el mismo | renovación por `PeriodoContractual` sobre el mismo contrato | preserva historia legal y financiera | `2.4`, `7.9`, `8.2`, `20` | precedencia documental para que roadmap no contradiga esta regla |
| Contratos | Contrato futuro | `prd7-10`, `prd13-25` | múltiples futuros o conflicto manual vs uno condicionado | máximo `1` contrato futuro por propiedad o pareja vinculada | reduce conflicto operacional y simplifica consistencia | `7.5`, `8.2`, `8.13`, `8.17`, `16.2` | bloqueo de cancelación de aviso si hay contrato futuro activo |
| Contratos | Cambio de arrendatario | `prd8-25` | mantener contrato con nuevo titular vs terminar y crear nuevo | término + contrato nuevo | más limpio jurídica y contablemente | `2.4`, `7.9`, `8.11`, `20` | liquidación de garantía y persistencia de deuda histórica |
| Contratos | Retroactividad | `prd10`, `prd13-25` | contratos retroactivos con distinto nivel de detalle | permitidos sin límite, sin reconstrucción ficticia del pasado | cubre la necesidad del negocio sin inventar historia operativa | `8.12`, `9.2`, `15.2` | advertencia obligatoria si se crea después del día 5 |
| Contratos | UF más alto histórico en retroactivos | `prd10`, `prd22` | usar el UF máximo histórico del rango vs mantener regla mensual general | se rechaza como regla canónica; cada cobro futuro usa la regla general del mes correspondiente | la regla del máximo histórico rompe consistencia de cálculo y dificulta auditabilidad | `8.12` | rechazo explícito de una regla histórica reiterada pero no defendible |
| Propiedades vinculadas | Alcance funcional | `prd25`, trazas previas indirectas | ausencia total vs `1 contrato -> N propiedades` abierto | solo `1 principal + 1 vinculada` | toma el valor del caso real sin abrir complejidad excesiva | `7.6`, `7.10`, `8.6`, `20` | distribución interna y división contractual explícita |
| Propiedades vinculadas | Código efectivo | `prd25`, `PRD_UNIFICADO` | código propio por inmueble vs código heredado para cobro | vinculada hereda código efectivo de principal | maximiza conciliación y mantiene identidad de activo | `7.6`, `8.5`, `8.15` | separación entre código estructural y código efectivo |
| Cálculo | Fórmula mensual | `prd1-4`, `prd10`, `prd24-26` | distintos niveles de detalle en UF, truncamiento y código | monto base -> UF -> ajustes -> truncar -> mínimo -> insertar código | es la cadena estable a lo largo de la evolución | `8.3`, `16.1` | doble fecha de pago y consistencia por contrato |
| Cálculo | Fuente UF | `prd2`, `prd4`, `prd26`, `CLAUDE.md` | fuentes variables y fallback poco estandarizado | Banco Central -> CMF -> MiIndicador -> carga manual auditada | disponibilidad + trazabilidad | `8.4`, `10.2`, `8.16` | gate de proveedor y carga manual formal |
| Notificaciones | Configuración por contrato | `prd10`, `prd21-25`, `prd26` | rigidez inicial vs flexibilidad extrema | configuración por contrato/día/canal, con base sugerida | equilibra flexibilidad y control | `8.7`, `15.3` | canal mínimo operativo y fallback permitido |
| Notificaciones | WhatsApp bloqueado | `prd12`, `prd20-24` | detección simple vs rehabilitación y control | bloqueo visible, alerta, rehabilitación documentada y email fallback | protege el canal y evita silencio operacional | `8.7`, `10.4`, `15.2` | gate de canal y salida de rehabilitación |
| Conciliación | Modo exacto/asistido/manual | `prd5-25`, `prd26` | distintos umbrales y automatizaciones agresivas | exacto -> asistido por IA -> manual | separa certeza, sugerencia y decisión humana | `8.8`, `9.7`, `15.3` | prohibición de autoasignación ambigua |
| Fechas | Pago real vs detección | `PRD_UNIFICADO`, evolución tardía | fecha banco vs fecha sistema | guardar ambas; usar cada una según contexto | elimina ambigüedad operacional y auditiva | `8.9` | separación entre mora y trazabilidad del sistema |
| Garantías | Naturaleza jurídica | `prd1-4`, `prd21-25` | garantía ligada a propiedad vs a contrato | garantía contractual con historial independiente | coherencia legal y contable | `7.14`, `8.10`, `8.15` | resolución especial si una pareja vinculada se separa |
| Deuda | Repactación | `prd5-25`, `prd26` | deuda absorbida por contrato vs obligación con historia propia | repactación no reescribe la historia del contrato | preserva trazabilidad de mora y cumplimiento | `7.16`, `15.2`, `15.3` | score condicionado a cuota efectivamente cumplida |
| Deuda | Código post-contrato | `PRD_UNIFICADO`, versiones tardías | deuda residual sin mecanismo estable vs código dedicado | rango `900-999` para deuda post-contrato | separa deuda residual de arriendo activo | `7.17` | persistencia aunque el arrendatario tenga contratos nuevos |
| Documentos | Generación contractual | `prd17-26`, `prd24-25` | desde almacenamiento simple hasta flujo formal completo | generación desde plantilla, PDF, control de archivos y checksum | integra negocio, legalidad y trazabilidad | `7.18`, `9.3`, `15.3` | archivo operativo unificado |
| Documentos | Firma y notaría | `prd17`, `prd24`, `prd26` | firma documental simple vs flujo mixto completo | revisión -> firma arrendador -> notaría -> recepción final | refleja el proceso real del negocio | `9.3` | pasos y precondiciones del flujo formal |
| Email | Gmail dual | `prd26`, `CLAUDE.md`, `PRD_UNIFICADO` | correo único vs identidad por empresa/cuenta | Gmail por empresa o por cuenta bancaria con regla de selección | equilibrio entre identidad y operación centralizada | `10.3` | gate de conexión y prueba de envío |
| SII | Facturación y tributación | `prd10`, `prd20-26`, `CLAUDE.md` | automatización ambiciosa vs readiness insuficiente | integración directa; automatización por fases; aprobación humana por defecto en lo sensible | reduce sobrepromesa y aumenta defendibilidad | `10.5`, `13.5`, `20` | gate de readiness formal para automatización extendida |
| Marketing | Publicación automática | `prd24-26`, `CLAUDE.md` | promesa automática sin prueba de API | solo con API viable, TOS compatibles y prueba end-to-end | evita vender una capacidad incierta como cerrada | `10.6`, `14`, `20` | checklist/manual asistido como fallback permitido |
| IA | Límites de IA | `prd20-26`, `PRD_UNIFICADO` | IA como sugerencia vs IA como ejecutor | IA sugiere, clasifica y resume; no ejecuta acciones críticas por defecto | seguridad, auditabilidad y gobernanza | `4.4`, `10.7`, `20` | gate de criticidad y logging obligatorio |
| Documento fuente | Contaminación de texto generado | `prd16`, `prd18`, `prd19`, `prd22`, `prd23`, `prd25` | contenido de PRD mezclado con wrappers, truncados o mensajes de asistente | se rechaza todo texto de scaffolding, truncado o metacomentario como fuente normativa | protege la señal documental y evita adoptar ruido de generación | `2.5`, `18`, auditoría | lectura lineal permitió distinguir contenido de producto vs contaminación de canal |
| Arquitectura | Stack base backend/async | `prd20`, `prd21`, `prd26`, `CLAUDE.md` | `DRF + Background Tasks` vs `Django Ninja + Celery` | stack canónico: `Django 5 + Django Ninja + Redis + Celery` | se alinea con la fuente más consistente y con el resumen operativo actual del proyecto | `12.1`, `12.4` | se aclara que `Web Workers` son opcionales y no norma |
| Seguridad | Secretos y privilegios | `prd10`, `prd20-26`, `CLAUDE.md` | mezcla de acceso operativo y secretos | separación de secretos, mínimo privilegio y restricción por rol | reduce riesgo sistémico | `11.1`, `11.2`, `15.3` | bloqueo de acceso no autorizado a trazas y decisiones de cierre |
| Resiliencia | Degradación y fallback | `prd6`, `prd12`, `prd20-25` | fallbacks dispersos y sin jerarquía | fallbacks permitidos y prohibidos formalizados | evita “atajos” encubiertos | `8.16`, `11.3`, `9.7` | jerarquía explícita entre fallback válido y no válido |
| Gobernanza | Precedencia del PRD | `prd24`, `prd25`, auditoría actual | ejemplos, roadmap y reglas mezclados | normativa > operativo > ilustrativo > evolutivo | elimina lecturas conflictivas al implementar | `4.6`, `4.7` | clasificación formal del contenido del PRD |
| Aceptación | Pruebas por subsistema | `prd24`, maestro actual, segunda vuelta | aceptación global demasiado general | aceptación por módulo + escenarios transversales | vuelve el PRD más implementable y testeable | `15.2`, `15.3` | tabla por subsistema y escenarios mínimos |

## 4. Decisiones reabiertas

En esta segunda vuelta no se reabrió ninguna decisión maestra. Se reforzaron y formalizaron:

- gates;
- precedencia;
- transiciones de estado;
- excepciones manuales;
- aceptación por subsistema.

## 5. Uso recomendado

Orden de uso para implementación:

1. leer esta matriz para entender tensiones y decisiones;
2. ir al maestro para la definición normativa;
3. usar la auditoría por versión cuando se necesite contexto histórico o racional detallado.
