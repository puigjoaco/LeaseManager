# Arquitectura Maestra LeaseManager

Estado: sintesis rectora derivada del set vigente de mayo 2026.

Esta arquitectura describe el producto, sus dominios, dependencias, reglas,
gates, evidencia y condiciones de cierre. No contiene ejecutores ni
herramientas operativas. Si existe conflicto, manda la fuente de verdad definida
en `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md`.

## Mision del producto

LeaseManager debe operar la administracion inmobiliaria, contractual,
recaudatoria, contable, documental y tributaria de patrimonios, empresas,
comunidades y propietarios, manteniendo trazabilidad completa desde el dato
maestro hasta el cierre mensual, renta anual y reporting.

## Stack v1

- Monolito modular.
- Backend: Django 5.
- API: Django REST Framework.
- Base de datos: PostgreSQL.
- Jobs: Celery + Redis.
- Frontend: React + TypeScript + Vite.
- Documentos: PDF canonico.

## Capas de arquitectura

1. Gobierno y fuente de verdad: PRD vigente, gates externos, ADR activos,
   arquitectura y plan trazable.
2. Plataforma base: auth, RBAC, auditoria, permisos, healthcheck, configuracion,
   jobs y observabilidad minima.
3. Dominio patrimonial: socios, empresas, participaciones, propiedades,
   comunidades, cuentas recaudadoras y mandatos.
4. Dominio contractual: arrendatarios, codeudores, contratos, propiedades por
   contrato, periodos contractuales, reajustes, garantias y avisos.
5. Dominio de cobranza y canales: pagos mensuales, codigos de cobro, correo,
   WebPay, notificaciones y estados de cuenta.
6. Dominio bancario: movimientos, conciliacion, ingresos desconocidos,
   atribucion y saldo sistema igual a saldo banco.
7. Dominio contable: eventos contables, reglas, asientos, movimientos, cierres,
   liquidaciones, PPM, F29/F21 y estados/reportes.
8. Dominio tributario: empresas emisoras, DTE 34 cuando corresponda, SII,
   renta anual, DDJJ, F22 y certificados.
9. Dominio documental: PDFs, contratos, respaldos, politicas de firma y
   notaria, origen de reportes y evidencia.
10. Operacion productiva: backups, restore, runbook, monitoreo, soporte,
    aceptacion y continuidad.

## Invariantes de negocio

- No inventar direcciones, RUTs, nombres, montos, contratos, cuentas,
  participaciones ni clasificaciones.
- UF exacta por fecha cuando una operacion dependa de UF.
- Saldo sistema igual a saldo banco antes de cierre.
- Cuentas separadas por entidad.
- Solo empresas emiten DTE 34 cuando corresponda.
- Comunidades y personas naturales no facturan si la regla tributaria no lo
  permite.
- Contratos usan `PeriodoContractual`.
- Datos maestros viven una vez y se referencian desde otros modulos.
- Operaciones criticas dejan auditoria.
- WebPay, banco, SII y correo no reemplazan evidencia final.

## Orden de construccion

1. PlataformaBase.
2. Patrimonio.
3. Operacion.
4. Contratos.
5. CobranzaActiva.
6. Conciliacion.
7. Contabilidad.
8. Documentos.
9. Canales.
10. SII.
11. Reporting.

Dependencias criticas:

- Contabilidad no cierra antes de que Conciliacion genere hechos confiables.
- SII no cierra antes de configuracion fiscal, ledger y cierre mensual.
- Documentos no cierra sin politica de firma, notaria y origen verificable.
- Reporting no cierra si sus cifras no trazan a datos, asientos o documentos.

## Gates externos

Toda integracion externa parte cerrada o condicionada por
`01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md`. Email, WhatsApp, banco, UF, SII,
WebPay, storage, dominios y despliegue requieren permisos, entorno, prueba
aislada, evidencia y rollback.

## Bloqueos y evidencia

Los registros de evidencia y bloqueos son controles operativos de cierre, no
capas de arquitectura ni componentes del producto. Un bloqueo puede impedir
declarar cierre, abrir una integracion, usar datos reales o marcar evidencia
final, pero no redefine dominios, entidades, dependencias ni el orden de
construccion.

Cuando una etapa queda bloqueada por dato real, decision o servicio externo, el
avance permitido es preparacion verificable que no declare cierre ni use datos
no autorizados. El bloqueo debe registrarse una vez con proxima accion concreta;
no debe convertirse en una repeticion indefinida de la misma solicitud.

## Definition of Done del producto

LeaseManager esta listo para uso cuando todo componente obligatorio esta:

- implementado o confirmado;
- conectado con sus dependencias reales o controladas;
- probado con gates reproducibles;
- documentado;
- auditado;
- sin datos sensibles en evidencia;
- sin duplicaciones activas;
- sin contradicciones entre PRD, ADR, arquitectura y codigo;
- sin bloqueos criticos abiertos que impidan el cierre declarado;
- aceptado por el usuario o responsable designado.
