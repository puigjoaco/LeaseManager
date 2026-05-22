# Etapa 6 - Renta anual

## Objetivo

Preparar proceso anual de renta, DDJJ, F22, certificados y trazabilidad desde
cierres mensuales.

## Alcance

- Proceso de renta anual.
- Certificados.
- Declaraciones juradas.
- F22 y respaldos.
- Validaciones tributarias.

## Gate

- Cierres mensuales completos.
- Reglas tributarias validadas.
- Documentos generados desde datos trazables.
- Evidencia sin datos sensibles expuestos.
- Capacidades DDJJ/F22, ProcesoRentaAnual, DDJJ y F22 pertenecen a empresas
  con `ConfiguracionFiscalEmpresa` activa propia.
- `audit_stage6_renta_anual_readiness` consolida configuracion fiscal,
  capacidades DDJJ/F22, doce cierres, obligaciones mensuales, proceso anual,
  respaldos tributarios PDF y referencias finales no sensibles sin conectar SII
  ni leer certificados reales.

## Salida

La renta anual no cierra si existen meses sin cierre validado o reglas fiscales
sin respaldo.
