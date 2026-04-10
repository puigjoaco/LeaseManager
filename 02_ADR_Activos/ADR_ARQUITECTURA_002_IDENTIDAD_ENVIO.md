# ADR 002 - Identidad de envio y ownership de canales

Estado: aprobado  
Fecha: 15/03/2026  
PRD relacionado: [PRD_CANONICO.md](./PRD_CANONICO.md)

## Contexto

El maestro anterior permitia `Gmail por empresa o por cuenta bancaria`. Esa formulacion mezclaba un canal de comunicacion con un instrumento de recaudacion y dejaba ambigua la propiedad de credenciales, la experiencia del arrendatario y la auditoria del remitente.

## Decision

LeaseManager adopta `IdentidadDeEnvio` como abstraccion obligatoria para canales salientes.

Decisiones aprobadas:

1. Toda salida automatizada o asistida usa una `IdentidadDeEnvio`.
2. Una `IdentidadDeEnvio` pertenece a un owner autorizado:
   - `Empresa`
   - `AdministradorOperativo`
3. Una cuenta bancaria nunca es owner de credenciales de canal.
4. Los canales inicialmente soportados son:
   - `Email`
   - `WhatsApp`
5. La seleccion de identidad opera en este orden:
   - override explicito del contrato para ese canal;
   - identidad activa asignada en el `MandatoOperacion`;
   - si no existe identidad valida, el canal se bloquea y el sistema alerta al administrador.
6. No existe sustitucion silenciosa de remitente.

## Forma de implementacion

Campos minimos de `IdentidadDeEnvio`:

- `id`
- `canal`
- `owner_tipo`
- `owner_id`
- `remitente_visible`
- `direccion_o_numero`
- `credencial_ref`
- `estado`

Reglas de canal:

- `Email`: requiere identidad con credencial activa y permiso de envio.
- `WhatsApp`: requiere identidad habilitada, template aprobado y opt-in operacional valido.

## Consecuencias

- Se aclara quien comunica y con que credenciales.
- Se evita atar canales a cuentas recaudadoras.
- La experiencia del arrendatario y la trazabilidad del remitente mejoran.
- Los gates de email y WhatsApp se controlan por identidad y canal, no por banco.

## Alternativas descartadas

- `Gmail por cuenta bancaria`: descartado por confundir ownership y contexto operacional.
- Remitente global unico para toda la plataforma: descartado por falta de aislamiento operativo.

