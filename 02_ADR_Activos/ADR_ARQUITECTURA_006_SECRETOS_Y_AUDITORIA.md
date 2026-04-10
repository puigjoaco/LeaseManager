# ADR 006 - Secretos, certificados y auditoria inmutable

Estado: aprobado  
Fecha: 15/03/2026  
PRD relacionado: [PRD_CANONICO.md](./PRD_CANONICO.md)

## Contexto

El maestro anterior exigia cifrado y trazabilidad, pero no definia el mecanismo operativo para secretos, certificados, refresh tokens ni eventos auditablemente sensibles.

## Decision

LeaseManager adopta separacion fuerte entre secretos y datos operativos.

Decisiones aprobadas:

1. Los secretos de integracion y certificados no se almacenan como texto plano en la base transaccional.
2. La plataforma usa un secret manager o KMS como origen canonico de secretos.
3. La base de datos solo guarda referencias, metadatos operativos, expiracion y estado.
4. Si una integracion exige cache local de token de corta vida, este debe almacenarse cifrado y con expiracion explicita.
5. La auditoria sensible opera en modo append-only a nivel aplicativo: no se reescriben eventos historicos.
6. Toda resolucion manual, reapertura de mes, cambio de gate, evento tributario sensible o decision sobre pagos ambiguos genera bundle auditable.
7. Toda exportacion masiva de datos financieros, tributarios o documentales sensibles genera bundle auditable.

## Forma de implementacion

Bundle minimo de auditoria:

- actor;
- timestamp;
- entidad afectada;
- accion;
- motivo;
- payload hash o before/after cuando aplique;
- referencias externas;
- aprobacion humana asociada si corresponde.
- scope de datos exportados cuando el evento sea una exportacion.

## Consecuencias

- baja el riesgo sistemico por exposicion de secretos;
- mejora la trazabilidad forense;
- obliga a explicitar ownership, expiracion y rotacion.

## Alternativas descartadas

- guardar client secrets y certificados solo en la base de datos: descartado.
- auditoria editable o resumida sin evidencia: descartada.

