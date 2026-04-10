# Auditoría Exhaustiva de PRD 1-26

## 1. Propósito

Este documento registra la auditoría exhaustiva realizada sobre los `26` PRD crudos de [analizar](D:/Proyectos/PRDLeaseManager/analizar), más los documentos de apoyo del repositorio. Su objetivo es dejar trazabilidad explícita de:

- qué aportó cada versión;
- qué mejoró respecto de las anteriores;
- qué contradicciones o riesgos introdujo;
- qué se adoptó, refinó, fusionó o rechazó;
- en qué parte del maestro final quedó absorbido.

El documento canónico del producto sigue siendo [PRD_MAESTRO_DEFINITIVO.md](D:/Proyectos/PRDLeaseManager/PRD_MAESTRO_DEFINITIVO.md). Esta auditoría existe para demostrar cobertura y criterio de consolidación.

## 2. Fuentes auditadas

Se auditó el contenido completo de:

- [analizar/prd1.txt](D:/Proyectos/PRDLeaseManager/analizar/prd1.txt)
- [analizar/prd2.txt](D:/Proyectos/PRDLeaseManager/analizar/prd2.txt)
- [analizar/prd3.txt](D:/Proyectos/PRDLeaseManager/analizar/prd3.txt)
- [analizar/prd4.txt](D:/Proyectos/PRDLeaseManager/analizar/prd4.txt)
- [analizar/prd5.txt](D:/Proyectos/PRDLeaseManager/analizar/prd5.txt)
- [analizar/prd6.txt](D:/Proyectos/PRDLeaseManager/analizar/prd6.txt)
- [analizar/prd7.txt](D:/Proyectos/PRDLeaseManager/analizar/prd7.txt)
- [analizar/prd8.txt](D:/Proyectos/PRDLeaseManager/analizar/prd8.txt)
- [analizar/prd9.txt](D:/Proyectos/PRDLeaseManager/analizar/prd9.txt)
- [analizar/prd10.txt](D:/Proyectos/PRDLeaseManager/analizar/prd10.txt)
- [analizar/prd11.txt](D:/Proyectos/PRDLeaseManager/analizar/prd11.txt)
- [analizar/prd12.txt](D:/Proyectos/PRDLeaseManager/analizar/prd12.txt)
- [analizar/prd13.txt](D:/Proyectos/PRDLeaseManager/analizar/prd13.txt)
- [analizar/prd14.txt](D:/Proyectos/PRDLeaseManager/analizar/prd14.txt)
- [analizar/prd15.txt](D:/Proyectos/PRDLeaseManager/analizar/prd15.txt)
- [analizar/prd16.txt](D:/Proyectos/PRDLeaseManager/analizar/prd16.txt)
- [analizar/prd17.txt](D:/Proyectos/PRDLeaseManager/analizar/prd17.txt)
- [analizar/prd18.txt](D:/Proyectos/PRDLeaseManager/analizar/prd18.txt)
- [analizar/prd19.txt](D:/Proyectos/PRDLeaseManager/analizar/prd19.txt)
- [analizar/prd20.txt](D:/Proyectos/PRDLeaseManager/analizar/prd20.txt)
- [analizar/prd21.txt](D:/Proyectos/PRDLeaseManager/analizar/prd21.txt)
- [analizar/prd22.txt](D:/Proyectos/PRDLeaseManager/analizar/prd22.txt)
- [analizar/prd23.txt](D:/Proyectos/PRDLeaseManager/analizar/prd23.txt)
- [analizar/prd24.txt](D:/Proyectos/PRDLeaseManager/analizar/prd24.txt)
- [analizar/prd25.txt](D:/Proyectos/PRDLeaseManager/analizar/prd25.txt)
- [analizar/prd26.txt](D:/Proyectos/PRDLeaseManager/analizar/prd26.txt)
- [prd.txt](D:/Proyectos/PRDLeaseManager/prd.txt)
- [PRD_UNIFICADO.md](D:/Proyectos/PRDLeaseManager/PRD_UNIFICADO.md)
- [CLAUDE.md](D:/Proyectos/PRDLeaseManager/CLAUDE.md)

## 3. Metodología de auditoría

Para cada PRD se registró:

- enfoque dominante de la versión;
- aportes únicos o mejoras relevantes;
- contradicciones con otras versiones;
- debilidades, riesgos o sobrepromesas;
- decisión de consolidación:
  - `Adoptar`
  - `Adoptar refinado`
  - `Fusionar`
  - `Rechazar`
- huella visible en el maestro final.

## 4. Contradicciones globales cerradas

| Tema | Tensiones históricas detectadas | Decisión canónica final |
|---|---|---|
| Estrategia bancaria | scraping puro -> API + scraping -> solo API | Banco de Chile API oficial + contingencia manual; scraping fuera de la estrategia oficial |
| Credenciales bancarias | usuario/clave de portal y 2FA vs conexión oficial | se normaliza `Conexión bancaria oficial`; se abandona el modelo canónico de portal |
| Cambio de arrendatario | cambio de titular dentro del contrato vs término + contrato nuevo | siempre término del contrato vigente + contrato nuevo |
| Renovación | crear contrato nuevo vs extender el mismo contrato | renovación por extensión del mismo contrato |
| Contrato futuro | múltiples futuros o conflicto manual vs uno solo condicionado | máximo un contrato futuro y solo si existe aviso/terminación válida |
| Código de propiedad | no siempre acotado por cuenta, incluso 001-899 en unificado previo | `001-999` por cuenta bancaria |
| Usuarios y socios | límite de ~15 vs usuarios ilimitados | RBAC flexible sin límite arbitrario como regla dura |
| Propiedades vinculadas | inexistente vs 1:N abierto | caso oficial acotado: `1 principal + 1 vinculada` |
| Integraciones de marketing | automatización prometida sin certeza de APIs | solo si existen APIs reales y viables |
| Automatización regulatoria | promesas muy agresivas de IA/SII | automatización por fases con aprobación humana donde la criticidad lo exige |

## 5. Fichas por versión

### PRD 1

- **Enfoque**: documento fundacional de Rent Control, centrado en el dominio base, los CRUD y el cálculo mensual.
- **Aportes únicos o fuertes**:
  - primera formulación robusta del problema de negocio;
  - base de entidades maestras;
  - cálculo de renta con UF y código embebido;
  - integración de garantías con ingresos y gastos manuales;
  - primeras secciones de riesgos y mitigaciones.
- **Debilidades o contradicciones**:
  - scraping bancario como estrategia principal;
  - ambición alta sobre automatización 2FA;
  - estructura aún muy extensa y poco jerarquizada.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - visión del producto;
  - modelo de dominio base;
  - reglas de cálculo;
  - riesgos y trazabilidad.

### PRD 2

- **Enfoque**: refinamiento del original con mayor precisión contractual y financiera.
- **Aportes únicos o fuertes**:
  - mayor definición de inmutabilidad contractual;
  - `CategoriaMovimiento` y tratamiento más claro de garantías;
  - cadena de fallback para valor UF;
  - mayor precisión sobre excepciones administrativas.
- **Debilidades o contradicciones**:
  - sigue anclado a credenciales y scraping de portal;
  - mezcla buena especificación con medios de integración hoy descartados.
- **Decisión**: `Adoptar refinado`.
- **Huella en el maestro**:
  - reglas contractuales;
  - garantías e historial;
  - política de fuentes UF.

### PRD 3

- **Enfoque**: consolidación de garantías y mayor granularidad operativa.
- **Aportes únicos o fuertes**:
  - mejor separación entre devolución y retención;
  - estados más finos de garantía;
  - mejor vínculo entre movimientos manuales y ciclo contractual.
- **Debilidades o contradicciones**:
  - persiste scraping;
  - sigue heredando ambigüedad estructural del bloque fundacional.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - garantía contractual;
  - `HistorialGarantia`;
  - estados y justificaciones.

### PRD 4

- **Enfoque**: primera transición seria desde scraping puro a API prioritaria.
- **Aportes únicos o fuertes**:
  - priorización explícita de API Banco de Chile;
  - `HistorialGarantia` con trazabilidad;
  - más robustez en avisos y cierres;
  - mayor estructura operativa del roadmap.
- **Debilidades o contradicciones**:
  - mantiene scraping como fallback natural;
  - no resuelve aún el problema de seguridad/compliance de fondo.
- **Decisión**: `Adoptar refinado`.
- **Huella en el maestro**:
  - priorización de integración oficial;
  - garantías trazables;
  - fortalecimiento de flujos de término.

### PRD 5

- **Enfoque**: evolución hacia operación más completa, con deuda y repactación.
- **Aportes únicos o fuertes**:
  - primera aparición clara de repactación;
  - mejor secuenciación por fases;
  - mayor foco en uso operativo real.
- **Debilidades o contradicciones**:
  - sigue atado a API + scraping;
  - la deuda todavía no está totalmente separada del contrato histórico.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - repactaciones;
  - roadmap por fases;
  - lógica de deuda más madura.

### PRD 6

- **Enfoque**: reforzamiento técnico-operativo.
- **Aportes únicos o fuertes**:
  - modo degradado;
  - fallbacks más explícitos;
  - mayor foco en robustez de procesamiento.
- **Debilidades o contradicciones**:
  - sigue aceptando scraping como pieza normal de arquitectura;
  - la degradación aún no separa claramente lo permitido de lo prohibido.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - resiliencia;
  - modo degradado;
  - aislamiento de fallos.

### PRD 7

- **Enfoque**: maduración incremental del flujo contractual y financiero.
- **Aportes únicos o fuertes**:
  - más definición sobre contrato futuro;
  - mejoras en coherencia mensual;
  - mejor separación de responsabilidades operativas.
- **Debilidades o contradicciones**:
  - todavía tolera alternativas demasiado abiertas en conflictos;
  - no cierra completamente la gobernanza del contrato futuro.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - reglas de contrato futuro;
  - consistencia de flujos mensuales.

### PRD 8

- **Enfoque**: fase intermedia con mayor flexibilidad, pero también más contradicciones.
- **Aportes únicos o fuertes**:
  - conflicto explícito entre renovación automática y contrato futuro;
  - sistema de plantillas y más detalle de UX operativa;
  - validaciones más visibles de dominio.
- **Debilidades o contradicciones**:
  - permite múltiples contratos futuros, luego descartado;
  - abre la puerta a mantener contrato con nuevo titular;
  - mantiene scraping como respaldo normal.
- **Decisión**: `Fusionar` con varios descartes.
- **Huella en el maestro**:
  - tratamiento de conflicto renovación/contrato futuro, pero endurecido;
  - varias decisiones de esta versión quedaron expresamente rechazadas.

### PRD 9

- **Enfoque**: consolidación operativa con más automatización y más agresividad bancaria.
- **Aportes únicos o fuertes**:
  - refuerzo de automatización integral;
  - más detalle en asignaciones retroactivas y conciliación;
  - continuidad del modelo de períodos.
- **Debilidades o contradicciones**:
  - vuelve más fuerte la apuesta por scraping automático con 2FA;
  - conserva la idea de cambio flexible de arrendatario.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - consolidación de operación mensual;
  - trazabilidad de asignaciones y cierres.

### PRD 10

- **Enfoque**: endurecimiento serio del modelo contractual y de notificaciones.
- **Aportes únicos o fuertes**:
  - validación absoluta del monto mínimo `CLP 1.000`;
  - contratos retroactivos sin límite temporal;
  - formulación explícita de la regla del “valor UF más alto histórico” para retroactivos;
  - notificaciones extremadamente configurables;
  - auditoría y métricas más visibles.
- **Debilidades o contradicciones**:
  - convive la regla de cambio de arrendatario con flujo de titular intacto;
  - define scraping como “autorizado definitivo”;
  - la regla del UF máximo histórico para retroactivos se consideró demasiado agresiva e inconsistente con la regla general mensual;
  - mantiene tensión entre flexibilidad extrema y consistencia contractual.
- **Decisión**: `Adoptar refinado`.
- **Huella en el maestro**:
  - monto mínimo absoluto;
  - contratos retroactivos;
  - flexibilidad de notificaciones por contrato y por día.

### PRD 11

- **Enfoque**: reorganización por capacidades y primera estructura más ejecutiva.
- **Aportes únicos o fuertes**:
  - cambio de forma hacia bloques funcionales;
  - primera cadena lógica/dependencias más utilizable;
  - lectura más rápida para implementación.
- **Debilidades o contradicciones**:
  - menos profundidad que versiones largas;
  - aún arrastra decisiones bancarias ya débiles.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - estructura por dominios;
  - orden de lectura y priorización.

### PRD 12

- **Enfoque**: versión resumida y más táctica.
- **Aportes únicos o fuertes**:
  - síntesis de dependencias;
  - detección de bloqueos WhatsApp;
  - mayor claridad de MVP versus siguientes fases.
- **Debilidades o contradicciones**:
  - menos detalle jurídico y de modelo;
  - persiste fallback bancario no canónico.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - cadena de evolución por fases;
  - alertas y fallos de mensajería.

### PRD 13

- **Enfoque**: primera gran versión madura de reglas definitivas.
- **Aportes únicos o fuertes**:
  - códigos `001-999` por cuenta bancaria;
  - representante legal obligatorio en comunidades;
  - snapshot del representante más sólido;
  - reglas duras de monto mínimo y retroactivos;
  - mejor definición de un solo contrato futuro.
- **Debilidades o contradicciones**:
  - todavía permite cambio de titular manteniendo contrato futuro;
  - sigue con scraping autorizado.
- **Decisión**: `Adoptar refinado`.
- **Huella en el maestro**:
  - propiedad, cuenta y códigos;
  - snapshot legal;
  - contrato futuro único;
  - reglas de retroactividad.

### PRD 14

- **Enfoque**: expansión de roles y usuarios, con gran consolidación del bloque maduro.
- **Aportes únicos o fuertes**:
  - elimina el límite operativo estricto de usuarios;
  - enfatiza permisos configurables;
  - conserva la estructura madura de `prd13`.
- **Debilidades o contradicciones**:
  - mezcla usuarios ilimitados con afirmaciones poco gobernadas de permisos;
  - todavía arrastra cambio de arrendatario en dos direcciones.
- **Decisión**: `Adoptar refinado`.
- **Huella en el maestro**:
  - RBAC flexible;
  - abandono del límite duro de usuarios/socios como regla de dominio.

### PRD 15

- **Enfoque**: profundización de anexos, decisiones de diseño y límites.
- **Aportes únicos o fuertes**:
  - mayor explicitud en apéndices;
  - más madurez en límites y reglas anexas;
  - continuidad del modelo contractual fuerte.
- **Debilidades o contradicciones**:
  - todavía no cierra del todo la contradicción de arrendatario;
  - mantiene la estrategia bancaria no canónica.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - límites operativos;
  - apéndices y endurecimiento de decisiones auxiliares.

### PRD 16

- **Enfoque**: estabilización extensa del bloque maduro.
- **Aportes únicos o fuertes**:
  - consolidación de fórmulas, NFR y reglas;
  - más madurez en estructura técnica y operativa.
- **Debilidades o contradicciones**:
  - contiene contaminación de canal con texto de asistente antes del contenido real;
  - sigue mezclando decisiones excelentes con fallback bancario débil;
  - aún no termina de limpiar ambigüedades históricas.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - soporte estructural del endurecimiento documental;
  - continuidad de fórmulas y reglas.

### PRD 17

- **Enfoque**: salto fuerte en formalización documental.
- **Aportes únicos o fuertes**:
  - estructura clara de generación de contratos;
  - mejor articulación de documentos y anexos;
  - vínculo más fuerte entre contrato y representación legal.
- **Debilidades o contradicciones**:
  - sigue coexistiendo con banca por scraping;
  - el resto del dominio todavía hereda tensiones previas.
- **Decisión**: `Adoptar`.
- **Huella en el maestro**:
  - generación documental;
  - firma y formalización;
  - estructura de archivo contractual.

### PRD 18

- **Enfoque**: refinamiento del salto documental de `prd17`.
- **Aportes únicos o fuertes**:
  - mejora del flujo documental;
  - continuidad del modelo maduro;
  - consolidación de detalle operativo.
- **Debilidades o contradicciones**:
  - arrastra encabezado de canal conversacional antes del contenido real;
  - no corrige aún la contradicción bancaria;
  - sigue en continuidad más que en ruptura.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - apoyo al flujo documental y contractual.

### PRD 19

- **Enfoque**: estabilización y coherencia incremental.
- **Aportes únicos o fuertes**:
  - mayor consistencia del bloque documental/operacional;
  - refuerzo de reglas maduras ya valiosas.
- **Debilidades o contradicciones**:
  - incluye fragmentos truncados por límite de generación, impropios de una fuente normativa limpia;
  - no agrega un cambio disruptivo nuevo;
  - mantiene herencias débiles anteriores.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - consistencia transversal del bloque contractual.

### PRD 20

- **Enfoque**: robustecimiento operacional con más foco en riesgos.
- **Aportes únicos o fuertes**:
  - bloqueos WhatsApp y rehabilitación;
  - timestamps finos;
  - riesgos y mitigaciones más realistas;
  - mejoras del tratamiento de repactación y estados.
- **Debilidades o contradicciones**:
  - introduce una variante técnica (`Django Background Tasks`) luego revertida en versiones posteriores;
  - aún conserva scraping como fallback natural;
  - mantiene algunas tensiones del cambio de arrendatario.
- **Decisión**: `Adoptar refinado`.
- **Huella en el maestro**:
  - comunicaciones y fallos;
  - estados de pago;
  - riesgos operativos y controles.

### PRD 21

- **Enfoque**: versión muy madura orientada a operación real.
- **Aportes únicos o fuertes**:
  - flujo de onboarding por email y formulario;
  - validación asíncrona inteligente de conexión bancaria;
  - regla fuerte de “no existe cambio de arrendatario”;
  - score de pago con contexto;
  - mejor definición de rehabilitación WhatsApp.
- **Debilidades o contradicciones**:
  - cambia la base async hacia `Celery`, corrigiendo la deriva técnica de `prd20`;
  - sigue describiendo credenciales de portal y scraping;
  - convive con residuos de versiones previas en otras áreas.
- **Decisión**: `Adoptar refinado`.
- **Huella en el maestro**:
  - onboarding de arrendatarios;
  - score de pago;
  - validación asíncrona;
  - criterio definitivo de contrato nuevo por cambio de arrendatario.

### PRD 22

- **Enfoque**: estabilización casi final del bloque operativo previo.
- **Aportes únicos o fuertes**:
  - continuidad del modelo maduro con menos ruido estructural;
  - refuerzo de reglas operativas, repactación y notificaciones.
- **Debilidades o contradicciones**:
  - incluye wrapper conversacional antes del PRD real;
  - reitera la regla del “valor UF más alto histórico” para retroactivos, luego descartada del canónico;
  - menos novedades reales que `prd21`;
  - sigue arrastrando medio de conexión bancaria hoy descartado.
- **Decisión**: `Fusionar`.
- **Huella en el maestro**:
  - consistencia transversal del bloque maduro.

### PRD 23

- **Enfoque**: consolidación fuerte de conflictos contractuales y snapshots legales.
- **Aportes únicos o fuertes**:
  - mejor snapshot inmutable de representante legal;
  - mejor control de conflictos entre aviso, renovación y contrato futuro;
  - regla fuerte de término + contrato nuevo;
  - mejor cierre jurídico/operativo de retroactivos.
- **Debilidades o contradicciones**:
  - el archivo viene contaminado con marcador `<context>` al inicio;
  - mantiene todavía el marco bancario antiguo;
  - el documento mezcla repeticiones estructurales.
- **Decisión**: `Adoptar`.
- **Huella en el maestro**:
  - contratos, snapshots, aviso de término y contrato futuro;
  - criterio jurídico-operativo reforzado.

### PRD 24

- **Enfoque**: gran salto de calidad de producto, no solo de dominio.
- **Aportes únicos o fuertes**:
  - personas e historias de usuario;
  - KPIs;
  - fuera de alcance;
  - UX/UI;
  - requerimientos no funcionales más completos;
  - plan de migración;
  - estructura más profesional de PRD.
- **Debilidades o contradicciones**:
  - sigue dependiendo de banca con scraping;
  - conserva ciertas promesas amplias que requerían moderación.
- **Decisión**: `Adoptar`.
- **Huella en el maestro**:
  - estructura de producto;
  - KPIs;
  - UX;
  - fuera de alcance;
  - parte del marco de calidad.

### PRD 25

- **Enfoque**: clarificación radical del concepto de contrato y aparición formal de propiedades vinculadas.
- **Aportes únicos o fuertes**:
  - defensa fuerte del contrato como entidad permanente;
  - claridad conceptual de renovación por extensión;
  - introducción explícita del sistema de propiedades vinculadas;
  - principios de desarrollo más duros.
- **Debilidades o contradicciones**:
  - el archivo viene contaminado con marcador `<context>` al inicio;
  - abre el modelo a `1 contrato -> N propiedades`, demasiado amplio;
  - mezcla requerimiento con lenguaje de “implementado y funcional”;
  - incluye comandos y detalles de implementación ya ejecutada, impropios del PRD;
  - mantiene scraping bancario.
- **Decisión**: `Adoptar refinado`.
- **Huella en el maestro**:
  - continuidad contractual;
  - propiedades vinculadas, pero cerradas a `principal + vinculada`;
  - eliminación del lenguaje de implementación real.

### PRD 26

- **Enfoque**: visión final de LeaseManager como ERP con IA, contabilidad y marketing.
- **Aportes únicos o fuertes**:
  - renombre a LeaseManager;
  - cadena UF Banco Central -> CMF -> MiIndicador;
  - sistema de correos dual Gmail;
  - firma mixta con notaría;
  - banco solo API como declaración más fuerte;
  - marketing inmobiliario automatizado condicionado a APIs;
  - visión de contabilidad inteligente, F29/F22 y agente conversacional.
- **Debilidades o contradicciones**:
  - convive con menciones residuales a scraping en algunas partes;
  - varias promesas de automatización regulatoria total requerían moderación y gobierno;
  - mezcla español con inglés y tono de manifiesto.
- **Decisión**: `Adoptar refinado`.
- **Huella en el maestro**:
  - identidad final del producto;
  - política UF;
  - Gmail dual;
  - firma mixta;
  - integraciones de marketing condicionadas;
  - límites de IA y evolución contable.

### Tabla de absorción y referencia al maestro

| PRD | Tipo de absorción | Secciones principales del maestro | Contradicción o descarte principal |
|---|---|---|---|
| `prd1` | `Fusionar` | `3`, `7`, `8`, `11` | scraping bancario como vía principal |
| `prd2` | `Adoptar refinado` | `7.13`, `7.14`, `8.4` | credenciales de portal como modelo canónico |
| `prd3` | `Fusionar` | `7.14`, `8.10` | ambigüedad estructural heredada |
| `prd4` | `Adoptar refinado` | `7.4`, `8.8`, `9.5` | scraping como fallback natural |
| `prd5` | `Fusionar` | `7.16`, `13` | deuda aún demasiado ligada al contrato |
| `prd6` | `Fusionar` | `8.16`, `11.3`, `9.7` | fallback no jerarquizado |
| `prd7` | `Fusionar` | `8.13`, `8.17` | conflicto contractual poco gobernado |
| `prd8` | `Fusionar` | `8.13`, `9.2` | múltiples contratos futuros y cambio flexible de titular |
| `prd9` | `Fusionar` | `8.14`, `9.4` | automatización bancaria agresiva |
| `prd10` | `Adoptar refinado` | `8.3`, `8.7`, `8.12` | scraping “definitivo” y tensión sobre arrendatario |
| `prd11` | `Fusionar` | `6`, `13` | menos profundidad funcional |
| `prd12` | `Fusionar` | `8.7`, `13` | resumen útil, pero menos robusto jurídicamente |
| `prd13` | `Adoptar refinado` | `7.5`, `7.9`, `8.2`, `16.2` | cambio de titular todavía coexistente |
| `prd14` | `Adoptar refinado` | `5.2`, `11.1` | usuarios ilimitados sin suficiente gobierno |
| `prd15` | `Fusionar` | `16`, `18` | continuidad sin cerrar contradicciones base |
| `prd16` | `Fusionar` | `8`, `11`, `16` | persistencia del modelo bancario débil |
| `prd17` | `Adoptar` | `7.18`, `9.3` | limitaciones fuera del bloque documental |
| `prd18` | `Fusionar` | `9.3`, `15.3` | continuidad más que novedad |
| `prd19` | `Fusionar` | `8`, `9` | pocas decisiones nuevas, pero buen refuerzo |
| `prd20` | `Adoptar refinado` | `8.7`, `7.12`, `11` | scraping y mezcla de tensiones previas |
| `prd21` | `Adoptar refinado` | `7.8`, `7.15`, `8.11` | credenciales de portal y scraping residual |
| `prd22` | `Fusionar` | `8`, `15` | estabilización sin salto estructural propio |
| `prd23` | `Adoptar` | `7.9`, `8.13`, `8.17` | repeticiones estructurales y banca antigua |
| `prd24` | `Adoptar` | `5`, `12`, `14`, `15` | automatización aún más prometida que gated |
| `prd25` | `Adoptar refinado` | `7.6`, `7.10`, `20` | 1:N abierto y lenguaje de implementación real |
| `prd26` | `Adoptar refinado` | `3`, `10`, `13`, `20` | automatización regulatoria y marketing demasiado ambiciosos sin gate fuerte |

## 6. Documentos de apoyo no crudos

### prd.txt

- **Rol**: guía metodológica de unificación.
- **Aporte absorbido**:
  - enfoque de auditoría individual;
  - lógica de clasificación y consolidación;
  - disciplina de extraer “lo mejor” y no mezclar por simple acumulación.
- **Decisión**: `Adoptar`.

### PRD_UNIFICADO.md

- **Rol**: intento previo de documento maestro.
- **Aporte absorbido**:
  - amplitud funcional útil;
  - varias decisiones ya bien orientadas;
  - primera consolidación visible del stack y roadmap.
- **Debilidades detectadas**:
  - contradicciones internas aún activas;
  - códigos `001-899`;
  - límite `~15` como regla dura;
  - banca con fallback a scraping;
  - frases telegráficas y sobrepromesas.
- **Decisión**: `Adoptar refinado` y limpiar fuertemente.

### CLAUDE.md

- **Rol**: resumen operativo del proyecto y sus reglas de entorno.
- **Aporte absorbido**:
  - stack oficial;
  - reglas maestras del negocio;
  - integraciones núcleo;
  - criterio “no temporary solutions”.
- **Decisión**: `Fusionar`.

## 7. Mejoras deliberadas introducidas por la auditoría

Estas mejoras no dependieron de una sola versión previa, sino del cruce de todas:

- normalización de `Conexión bancaria oficial` en vez de credenciales de portal;
- fijación de fallback bancario manual y rechazo del scraping como estrategia oficial;
- cierre de `propiedades vinculadas` al caso `1 principal + 1 vinculada`;
- creación conceptual de `ContratoPropiedad` para resolver trazabilidad sin abrir 1:N ambiguo;
- reglas de precedencia documental dentro del maestro;
- invariantes explícitos del dominio;
- política de fallbacks permitidos y prohibidos;
- controles anti-inconsistencia sobre contratos, garantías, pagos y avisos;
- moderación de promesas de automatización tributaria e IA a un marco defendible.

Hallazgos adicionales de la tercera vuelta lineal:

- identificación explícita de contaminación textual en varios PRD crudos por wrappers, marcadores de contexto o truncados de generación;
- detección reiterada de la regla del “valor UF más alto histórico” para contratos retroactivos y decisión consciente de no elevarla al canónico;
- cierre explícito de la tensión técnica `Django REST Framework / Django Background Tasks` versus `Django Ninja / Celery`.

## 8. Resultado final de la auditoría

Resultado de consolidación:

- el maestro final **sí** absorbió todos los PRD;
- no se adoptó a ciegas la versión más nueva;
- varias ideas potentes de versiones tardías solo entraron después de ser endurecidas;
- las mayores mejoras del documento final nacieron del cruce entre versiones, no de una sola fuente.

Principales líneas rechazadas del histórico:

- scraping bancario como capacidad oficial;
- cambio de arrendatario dentro del mismo contrato;
- múltiples contratos futuros por propiedad;
- límites arbitrarios de usuarios como regla de dominio;
- contrato multi-propiedad abierto sin restricción;
- lenguaje de “ya implementado” o “funcional” dentro del PRD;
- automatización regulatoria total sin gobierno ni política de aprobación.

Tabla de descartes estructurales:

| Línea descartada | Motivo de descarte |
|---|---|
| scraping bancario como capacidad oficial | inconsistente con seguridad, compliance y regla canónica del proyecto |
| credenciales de portal como modelo oficial | se reemplazó por integración bancaria oficial |
| cambio de arrendatario dentro del mismo contrato | mezcla historia jurídica y financiera |
| múltiples contratos futuros por propiedad | complica integridad y genera conflictos operativos |
| `1 contrato -> N propiedades` abierto | excede el caso real validado y eleva demasiado la complejidad |
| `001-899` como rango operativo | contradice la regla final `001-999` por cuenta |
| límite `~15` como regla dura de usuarios/socios | era un supuesto operativo, no una restricción de dominio |
| automatización total de IA/SII sin readiness | sobrepromesa no defendible para un PRD maestro |

