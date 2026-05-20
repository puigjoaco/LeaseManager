# Plan de Ordenamiento Profesional Mayo 2026

Estado: antecedente de plan. El reemplazo del root ya fue ejecutado y mergeado
a `main` en mayo 2026. Para el resultado real usar
`docs/RESULTADO_REEMPLAZO_ROOT_MAYO_2026.md`; este documento conserva el plan y
criterios que guiaron el proceso.
Fecha: 2026-05-20.
Relacion: complementa el PRD Canonico Mayo 2026 candidato y la Arquitectura Maestra.

## 1. Proposito

Este plan define como pasar desde el estado actual del proyecto, con avances
reales pero tambien herencia, carpetas historicas, documentos dispersos y muchos
cambios pendientes, hacia una base profesional limpia desde la cual se pueda
continuar hasta LeaseManager v1 sin arrastrar desorden.

El objetivo no es borrar historia ni rehacer lo que sirve. El objetivo es separar:

- fuente vigente;
- evidencia;
- codigo aceptado;
- trabajo pendiente;
- herencia util;
- herencia descartada;
- bloqueadores externos;
- datos reales;
- artefactos locales o riesgosos.

Solo despues de esa separacion corresponde continuar desarrollo de producto.

## 2. Principio rector

No se avanza producto sobre una base confusa.

Antes de nuevas features mayores, el proyecto debe tener:

- PRD candidato aceptado o lista concreta de correcciones.
- Arquitectura Maestra vigente y alineada.
- Anexo Excel absorbido como modelo operativo practico.
- Jerarquia documental limpia.
- Repo base o carpeta limpia verificable.
- Git funcionando con commits pequenos y revisables.
- Herencia aislada en savegames o historicos, no mezclada en el flujo diario.
- Gates y auditores reproducibles.
- Bloqueadores externos registrados.

## 3. Estado de partida reconocido

El estado actual no se asume como cero. Hay trabajo valioso:

- Codigo real implementado.
- Auditores de production-readiness.
- Arquitectura Maestra.
- PRD candidato Mayo 2026.
- Anexo operativo del Excel.
- Contextos obligatorios.
- Gates por etapa.
- Evidencia local.
- Savegame ya creado.

Tambien hay riesgo:

- Root con muchos cambios pendientes.
- Repo anidado historico `Produccion 1.0`.
- Fuentes historicas mezcladas con fuentes vivas.
- Documentos operativos antiguos.
- Capturas, artefactos y archivos locales que no deben entrar al producto.
- Cambios utiles aun no clasificados ni committeados.

## 4. Estrategia recomendada

La estrategia profesional recomendada es:

1. Conservar el root actual como fuente de rescate y savegame.
2. Crear una carpeta limpia de trabajo profesional.
3. Migrar selectivamente solo lo que pase auditoria.
4. Versionar en Git por paquetes pequenos.
5. Revalidar build, type-check y auditores.
6. Continuar el cierre productivo por etapas.

No se debe copiar el proyecto completo encima de la carpeta limpia. Eso trasladaria el problema.

Decision recomendada:

- Usar `D:/Proyectos/LeaseManager` como fuente de rescate temporal, no como base diaria.
- Crear `D:/Proyectos/LeaseManager-clean` desde el remoto o una rama limpia verificable.
- Migrar primero documentacion rectora y luego paquetes de codigo.
- Mantener el root actual intacto hasta que todo lo util este clasificado.
- Solo limpiar el root en sitio si el usuario rechaza expresamente la carpeta limpia.

Razon:

- El root actual tiene demasiados cambios pendientes para distinguir con seguridad, a simple vista, que es producto, que es experimento, que es evidencia local y que es herencia. Una base limpia reduce el riesgo de llevar basura historica al producto final.

## 5. Fase 0 - Congelar y proteger

Objetivo: asegurar que nada valioso se pierda antes de ordenar.

Acciones:

- Confirmar que existe savegame completo del root actual.
- No borrar ni resetear el root sucio.
- No ejecutar produccion, deploy, migraciones reales ni backfills.
- No iniciar nuevas features hasta terminar el primer baseline limpio.
- Registrar que archivos nuevos son candidatos y cuales siguen sin versionar.

Criterio de salida:

- Savegame identificado.
- Root actual tratado como fuente historica/rescate.
- Plan de migracion selectiva aprobado.

## 6. Fase 1 - Cerrar fuente rectora

Objetivo: decidir que documentos mandan antes de ordenar codigo.

Acciones:

- Revisar `PRD_CANONICO_MAYO_2026_CANDIDATO.md`.
- Revisar `ANEXO_MODELO_OPERATIVO_EXCEL_MAYO_2026.md`.
- Revisar Arquitectura Maestra.
- Revisar Matriz de Gates y ADR activos.
- Registrar correcciones del usuario.
- Marcar el PRD como aceptado o dejar lista de cambios.

Criterio de salida:

- Existe una fuente rectora clara.
- Se sabe que documentos son vigentes, candidatos, anexos o historicos.
- Ningun sistema historico dirige el producto.

Promocion del PRD candidato:

- Si el usuario acepta el PRD candidato, crear `docs/product/PRD_CANONICO_MAYO_2026.md` como documento vigente.
- Conservar `PRD_CANONICO_MAYO_2026_CANDIDATO.md` solo como trazabilidad o reemplazarlo por enlace al vigente, segun decision de versionado.
- Mover el PRD canonico previo del repo anidado a historico limpio, sin dejar dos PRD vigentes compitiendo.
- Actualizar `AGENTS.md`, indices y enlaces para apuntar al PRD vigente nuevo.
- Registrar la decision de aceptacion, fecha, alcance, auditoria aplicada y riesgos pendientes.
- No promover el candidato si existen correcciones abiertas del usuario, contradicciones con arquitectura/gates o faltantes de fuentes.

## 7. Fase 2 - Definir estructura profesional

Objetivo: ordenar carpetas y responsabilidades del repo.

Estructura objetivo:

```text
docs/product/
  PRD_CANONICO_MAYO_2026.md
  ANEXO_MODELO_OPERATIVO_EXCEL_MAYO_2026.md
  MATRIZ_GATES_EXTERNOS.md

docs/architecture/
  ARQUITECTURA_MAESTRA_LEASEMANAGER.md
  adr/

docs/production-readiness/
  etapas, gates, evidencia, handoffs, bloqueadores y runbook

docs/context/
  contextos vigentes migrados a ruta neutral o historicos claramente aislados

app/ components/ lib/ supabase/ scripts/ tests/
  codigo productivo, auditores y pruebas

archive/ o savegames externos
  historia no operativa, fuera del flujo diario
```

Reglas:

- `Produccion 1.0` no debe seguir como repo anidado operativo.
- `.taskmaster`, comandos antiguos, capturas, artefactos locales, `node_modules`, `.next`, snapshots reales y secretos no se migran a la base limpia.
- Los 26 PRD crudos quedan como historia, salvo que una auditoria demuestre una brecha concreta.
- Scripts legacy con service role amplio, `select('*')`, IDs/cuentas/ACTECO hardcodeados, tokens productivos, salida de errores internos o escritura directa en datos reales quedan en cuarentena hasta auditoria puntual.
- Codigo runtime con `as any` estructural, consultas excesivas, errores publicos inseguros, clientes privilegiados antes de auth/rol/scope o dependencias externas sin gate no puede clasificarse como `migrar_ahora` sin prueba y correccion.

Criterio de salida:

- Hay mapa de carpetas definitivo.
- Hay lista de migracion: conservar, mover, archivar, ignorar o eliminar en limpio.

## 8. Fase 3 - Crear baseline limpio

Objetivo: tener una carpeta/repo de trabajo que compile y sea revisable.

Acciones:

- Partir desde el remoto Git o desde una rama limpia verificable.
- Incorporar primero solo documentacion rectora.
- Incorporar despues codigo por paquetes funcionales.
- Evitar `git add .`.
- Commits pequenos, atomicos y con mensaje claro.
- Ejecutar build, type-check y auditores relevantes tras cada paquete.

Gates minimos del baseline:

- `npm run type-check`
- `npm run build`
- `npm run audit:production-docs-index`
- `npm run audit:stage1:local-self-tests`
- `npm run audit:session-status:markdown`

Si alguno falla, el baseline no esta listo para continuar features. La falla se registra como bloqueo o tarea de reparacion acotada.

Paquetes sugeridos:

- Documentacion rectora.
- Production-readiness y auditores.
- Seguridad/auth/RLS.
- Datos y schema Etapa 1.
- Cobranza/WebPay/correos.
- Banco/conciliacion.
- SII/facturacion.
- Contabilidad/cierre mensual.
- Renta anual.
- Operacion productiva.

Criterio de salida:

- `git status` limpio o con cambios candidatos controlados.
- Build y type-check pasan.
- Auditores documentales pasan.
- No hay herencia operativa mezclada.

## 9. Fase 4 - Clasificar cambios del root actual

Objetivo: rescatar lo util sin copiar desorden.

Cada archivo/cambio del root actual debe clasificarse:

- `migrar_ahora`
- `migrar_despues`
- `requiere_revision`
- `descartar`
- `historico_savegame`
- `bloqueado_por_dato_real`
- `bloqueado_por_dependencia_externa`

Reglas:

- Un cambio de seguridad probado tiene prioridad alta.
- Un documento rector validado tiene prioridad alta.
- Una captura o artefacto local no se migra.
- Un script riesgoso no se migra sin dry-run, rollback y confirmacion.
- Una migracion real no se aplica sin preflight, backup y rollback.
- Una mejora local sin evidencia externa puede migrarse como implementacion preparatoria, pero no puede cerrar etapa ni declararse `resuelto_confirmado`.

Registro requerido por cambio migrado:

- archivo o grupo de archivos;
- origen;
- destino;
- razon de migracion;
- estado;
- prueba/gate usado;
- riesgo residual;
- commit donde queda incorporado.

Criterio de salida:

- No quedan 455 cambios como masa anonima.
- Cada cambio importante tiene destino y razon.

## 10. Fase 5 - Reanudar cierre productivo por etapas

Objetivo: continuar el producto completo sin volver al desorden.

Orden:

1. Etapa 1: datos reales y matriz contrato-propiedad-cuenta-facturacion.
2. Etapa 2: cobranza, WebPay y correos.
3. Etapa 3: Banco y conciliacion.
4. Etapa 4: SII y DTE 34.
5. Etapa 5: cierre mensual, contabilidad, liquidaciones, PPM.
6. Etapa 6: renta anual, DDJJ, F22, certificados.
7. Etapa 7: operacion productiva, seguridad, dominio, backups, restore, runbook.

Regla:

- No se declara etapa lista sin gate reproducible y evidencia real/controlada.
- Codigo futuro queda `implementado_sin_evidencia` hasta probar dependencias reales/controladas.

## 11. Definition of Done del ordenamiento

El ordenamiento se considera completo solo si:

- El PRD rector y anexos estan aceptados o con cambios pendientes explicitos.
- La arquitectura y el PRD no se contradicen.
- La estructura de carpetas es clara.
- El repo base esta limpio o controlado.
- La herencia esta separada.
- Git tiene commits atomicos y rastreables.
- Los auditores documentales pasan.
- El siguiente bloqueo real esta identificado.
- Nadie necesita adivinar que archivo manda.

## 12. Definition of Ready para retomar desarrollo

Solo se retoma desarrollo funcional mayor cuando:

- Existe base limpia o root controlado.
- El PRD rector esta aceptado o sus correcciones estan listadas.
- El anexo Excel esta aceptado como modelo operativo practico.
- El plan de ordenamiento esta aceptado.
- La Arquitectura Maestra sigue alineada.
- `AGENTS.md` apunta a fuentes correctas.
- Los documentos historicos estan fuera del flujo operativo.
- Los cambios pendientes fueron clasificados.
- Hay una rama o secuencia de commits clara.
- Los gates minimos del baseline pasan.
- El proximo trabajo es una etapa concreta, no una mezcla de limpieza, feature, evidencia y deploy.

Si falta cualquiera de estos puntos, el trabajo siguiente sigue siendo ordenamiento, no avance de producto.

## 13. Proxima accion recomendada

La siguiente accion correcta es no seguir agregando features. Primero se debe:

1. Auditar y aceptar/corregir el PRD candidato, el anexo Excel y este plan.
2. Crear `D:/Proyectos/LeaseManager-clean` desde una base Git limpia, salvo decision contraria del usuario.
3. Migrar documentacion rectora a la base limpia.
4. Ejecutar gates minimos del baseline.
5. Clasificar los cambios pendientes por paquete.
6. Migrar primero cambios documentales, despues auditores, despues codigo funcional.
7. Recien entonces reanudar avance por Etapa 1.

## 14. Primera ejecucion concreta

La primera corrida de ordenamiento debe producir:

- carpeta limpia creada o root controlado declarado;
- commit inicial con `AGENTS.md`, PRD, anexo Excel, plan de ordenamiento, Arquitectura Maestra y Matriz de Gates;
- auditoria documental que confirme ausencia de herencia operativa como fuente activa;
- resultado de gates minimos;
- inventario de cambios del root actual agrupado por paquete;
- siguiente paquete a migrar con criterio de aceptacion.

No debe producir:

- deploy;
- migraciones reales;
- backfills;
- cambios de datos reales;
- cierre de etapa;
- declaracion de producto listo.
