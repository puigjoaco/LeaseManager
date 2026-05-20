# Auditoria de Fuentes - PRD Canonico Mayo 2026 Candidato

Estado: auditoria documental inicial.
Fecha: 2026-05-20.
Documento auditado: `docs/product/PRD_CANONICO_MAYO_2026_CANDIDATO.md`.

## 1. Objetivo

Registrar por que se propone un nuevo PRD Canonico Mayo 2026 y que fuentes se usaron para elevar el PRD vigente a una version mas limpia, actual y alineada con el proyecto real.

## 2. Fuentes consideradas

- `D:/Proyectos/LeaseManager/Produccion 1.0/06_Fuentes_PRD_1_26/prd1.txt` a `prd26.txt`: corpus historico bruto.
- `D:/Proyectos/LeaseManager/Produccion 1.0/05_Contexto_Historico/AUDITORIA_PRDS_1_26.md`: trazabilidad de consolidacion de los 26 PRD.
- `D:/Proyectos/LeaseManager/Produccion 1.0/05_Contexto_Historico/PRD_MAESTRO_DEFINITIVO.md`: maestro historico auditado.
- `D:/Proyectos/LeaseManager/Produccion 1.0/01_Set_Vigente/PRD_CANONICO.md`: PRD canonico vigente de marzo 2026.
- `D:/Proyectos/LeaseManager/Produccion 1.0/01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md`: gates externos vigentes.
- `D:/Proyectos/LeaseManager/Produccion 1.0/02_ADR_Activos/*.md`: ADR activos.
- `D:/Proyectos/LeaseManager/Produccion 1.0/04_Auditoria_y_Cierre/AUDITORIA_MAXIMA_PRD_MAESTRO.md`: hallazgos sobre mezcla de dominio, ADR, gates y roadmap.
- `D:/Proyectos/LeaseManager/docs/production-readiness/ARQUITECTURA_MAESTRA_LEASEMANAGER.md`: arquitectura integral de inicio a fin.
- `D:/Proyectos/LeaseManager/docs/production-readiness/PLAN_ETAPAS_PRODUCCION.md`: etapas, gates y bloqueos reales.
- `D:/Proyectos/LeaseManager/docs/production-readiness/*`: evidencia, handoffs, runbook, integraciones, datos reales, contabilidad y bloqueadores.
- `D:/Proyectos/LeaseManager/.Codex/context/*`: invariantes, Excel legacy, database, contabilidad, integraciones y proyecto maestro.
- `D:/Proyectos/LeaseManager/AGENTS.md`: reglas de negocio, cuentas, casos especiales, stop rules y nuevo orden documental.
- `D:/Proyectos/LeaseManager/package.json`: stack y auditores reales actuales.
- `D:/Proyectos/LeaseManager/docs/product/ANEXO_MODELO_OPERATIVO_EXCEL_MAYO_2026.md`: anexo candidato creado para traducir el Excel legacy a reglas operativas normalizadas.
- `D:/Proyectos/LeaseManager/docs/product/PLAN_ORDENAMIENTO_PROFESIONAL_MAYO_2026.md`: plan candidato para ordenar el proyecto antes de continuar desarrollo funcional.
- `D:/Proyectos/LeaseManager/docs/product/AUDITORIA_PRD_ORDENAMIENTO_MAYO_2026.md`: auditoria documental del PRD, anexo y plan de ordenamiento.

## 3. Hallazgos principales

1. Los 26 PRD historicos ya fueron consolidados, pero el contexto de mayo 2026 permite una reemision mas precisa porque ahora existe Arquitectura Maestra, gates por etapa, auditorias reproducibles, contexto de Excel Mayo 2026 y codigo real mucho mas avanzado.
2. El PRD canonico de marzo 2026 es util como base de producto, pero todavia debe convivir con documentos historicos y rutas del repo anidado `Produccion 1.0`.
3. La auditoria maxima antigua detecto un problema real: el PRD no debe mezclar dominio con stack, gates, roadmap o mecanismos de trabajo.
4. Tras migrar el candidato al root limpio se detecto una contradiccion
   relevante: el root historico contenia una app Next.js/Supabase, pero
   `origin/main` y `ADR_STACK_FINAL.md` gobiernan un greenfield Django/DRF,
   PostgreSQL, Celery/Redis y React/Vite. El PRD candidato no puede declarar
   Next.js/Supabase como stack vigente; cualquier decision tecnica debe quedar
   reconciliada por ADR aceptado.
5. TaskMaster y Claude son herencia operativa. Pueden conservarse en savegames o como contexto historico, pero no deben dirigir cierre productivo, etapas, prioridades ni evidencia.
6. La Arquitectura Maestra ya esta limpia como documento de producto/arquitectura y no debe incluir mecanismos de ejecucion. El PRD candidato conserva esa frontera.
7. La Etapa 1 sigue bloqueada hasta contar con base real o snapshot
   real/controlado del flujo que se esta migrando/validando. El PRD candidato
   no declara avance productivo.
8. El Excel legacy no debe quedar como "contexto auxiliar": contiene el modelo practico de cobranza, conciliacion, gastos, repartos, comision de administracion, sucesion y cierre mensual que el sistema debe absorber.
9. El PRD candidato explicaba producto, pero necesitaba un puente operacional para ordenar el repo/proyecto antes de seguir construyendo. Ese puente queda separado como plan de ordenamiento para no contaminar el PRD con instrucciones de ejecucion diaria.

## 4. Decisiones incorporadas al candidato

- Mantener el objetivo central: sistema integral para operar arriendos, cobranza, banco, SII, contabilidad, liquidaciones, renta anual y operacion productiva.
- Subir el Excel legacy a fuente practica de negocio, no como planilla a copiar celda por celda.
- Separar fuentes rectoras, arquitectura, gates, ADR, codigo real y documentos historicos.
- Explicitar que el candidato no reemplaza al vigente sin aprobacion.
- Mantener invariantes absolutos: no inventar datos, UF exacta, saldo banco, cuentas separadas, solo empresas facturan, periodos contractuales, datos maestros unicos y audit_log.
- Incluir casos especiales Bulnes 699, Parking E49, Edificio Q y Dpto 1014 codigo 46 Familia.
- Adoptar etapas 1 a 7 como camino de cierre productivo.
- Dejar las reglas tributarias como validadas solo por SII/normativa vigente o experto.
- Eliminar TaskMaster/Claude como fuente operativa.
- Reflejar el stack real actual como arquitectura tecnica de referencia, sin convertirlo en regla inmutable de producto.
- Crear un anexo operativo del Excel para no saturar el PRD, pero dejar vinculada su logica como fuente practica obligatoria.
- Crear un plan de ordenamiento profesional para guiar la transicion desde el estado actual hacia una base limpia.
- Auditar el set documental completo y cerrar brechas de baseline limpio, Definition of Ready y primera ejecucion concreta.

## 5. Mejoras frente al PRD canonico de marzo 2026

- Se alinea con el estado real de mayo 2026 y con production-readiness.
- Evita que el set vigente dependa de rutas dentro de un repo anidado.
- Integra el bloqueo real de Etapa 1 como condicion de avance.
- Separa con mas claridad producto, arquitectura, gates, ADR y mecanismos de trabajo.
- Refuerza evidencia y estados por componente.
- Refuerza seguridad de superficies publicas, service role, webhooks, crons, secretos y evidencia redactada.
- Reafirma que codigo compilable no equivale a produccion lista.
- Refuerza la traduccion del Excel a entidades normalizadas y pruebas obligatorias.

## 6. Riesgos o puntos abiertos

- Este candidato todavia no fue aceptado formalmente por el usuario.
- No se contrasto contra servicios externos en vivo; la auditoria es documental/local.
- Las reglas tributarias no fueron revalidadas en esta emision contra SII; quedan como gate.
- Los ADR activos deben reemitirse o revisarse para eliminar decisiones tecnicas historicas que no reflejen el stack actual.
- La migracion del set vigente a rutas limpias del root profesional sigue pendiente.
- La Etapa 1 sigue bloqueada hasta contar con base real o snapshot
  real/controlado.
- El anexo Excel debe revisarse nuevamente cuando existan mas meses o datos reales confirmados para evitar sobreajustarlo a Mayo 2026.
- El plan de ordenamiento requiere decision del usuario sobre si la base limpia se arma en nueva carpeta o dentro del root actual protegido por savegame.

## 7. Criterio de aceptacion de este candidato

Para convertir este candidato en PRD vigente:

1. El usuario debe aprobarlo o corregirlo expresamente.
2. Debe quedar en una ruta limpia del repo profesional, no escondido en historicos ni repo anidado.
3. Debe actualizarse la jerarquia documental en `AGENTS.md` y production-readiness.
4. Deben revisarse enlaces a ADR, gates y Arquitectura Maestra.
5. Debe ejecutarse una auditoria documental que bloquee referencias operativas a TaskMaster/Claude como fuentes activas.
6. Debe confirmarse que no contradice la Arquitectura Maestra ni los gates vivos.
7. Debe aceptarse o ajustarse el plan de ordenamiento antes de retomar features mayores.

## 8. Veredicto

El PRD Canonico Mayo 2026 candidato es una mejora razonable y profesional frente al set vigente historico, pero no debe marcarse como vigente hasta pasar aceptacion del usuario, limpieza de rutas, revision de ADR y auditoria documental final.
