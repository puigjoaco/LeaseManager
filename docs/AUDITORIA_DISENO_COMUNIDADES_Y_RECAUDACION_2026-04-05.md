# Auditoria de Diseno - Comunidades, Recaudacion y Mandato Operativo

Fecha: 05/04/2026  
Estado: recomendado para implementar por etapas  
Scope: modelo de `Patrimonio`, `Operacion`, `Conciliacion`, `Contabilidad`, `Reporting` y pipeline de migracion

## 1. Objetivo de la auditoria

Confirmar, con el mayor nivel de certeza posible, cual es la forma correcta de modelar:

- propiedades de `ComunidadPatrimonial`;
- administracion real por `Joaquin`;
- recaudacion bancaria via cuenta contenedora de comunidades (`Santa Maria II`);
- casos mixtos como `Edificio Q`, donde participa una `Empresa` dentro de la comunidad.

La auditoria busca evitar dos errores:

1. reflejar algo falso solo para satisfacer una validacion tecnica;
2. sobredisenar un modelo que no agrega valor real al dominio.

## 2. Hechos de negocio confirmados

### 2.1 Comunidades estandar

- cada propiedad comunitaria crea una comunidad independiente;
- las comunidades estandar tienen como participantes a `Cecilia`, `Geraldine`, `Cristobal` y `Joaquin`;
- los porcentajes cambian por propiedad;
- `Joaquin` administra operativamente todas las comunidades;
- los arriendos de comunidades se depositan en la cuenta contenedora `Santa Maria II`;
- esa cuenta existe como cuenta operativa compartida, no como verdad economica de ownership.

### 2.2 Casos especiales relevantes

- `Edificio Q` rompe la composicion estandar;
- en `Edificio Q` no participa `Joaquin` como duenio patrimonial;
- entra `Inmobiliaria Puig SpA` dentro de la comunidad;
- por lo tanto, la comunidad no siempre es solo un conjunto de personas naturales.

## 3. Reglas canonicas que gobiernan la decision

### 3.1 PRD activo

Del set vigente:

- `MandatoOperacion` une activo, responsable operacional, recaudacion, facturacion y canales.
- LeaseManager no deduce automaticamente que quien recauda es quien factura o quien comunica.
- una propiedad activa se cobra en una sola `CuentaRecaudadora`.
- una `CuentaRecaudadora` puede soportar muchas propiedades activas.
- el subsistema `Operacion` debe probarse con recaudador, facturador e identidad de envio distintos.

Referencias:

- [PRD_CANONICO.md:130](D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md#L130)
- [PRD_CANONICO.md:134](D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md#L134)
- [PRD_CANONICO.md:169](D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md#L169)
- [PRD_CANONICO.md:170](D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md#L170)
- [PRD_CANONICO.md:176](D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md#L176)
- [PRD_CANONICO.md:662](D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md#L662)

### 3.2 Implementacion actual

Hoy el backend impone:

- `CuentaRecaudadora` pertenece a `Empresa` o `Socio`, no a `Comunidad`;
- `MandatoOperacion` solo distingue `Propietario`, `AdministradorOperativo`, `EntidadFacturadora` y `CuentaRecaudadora`;
- la cuenta debe pertenecer al `AdministradorOperativo` o a la `EntidadFacturadora`;
- `ComunidadPatrimonial` solo puede componerse mediante participaciones de `Socio`;
- el representante de comunidad debe pertenecer a las participaciones activas.

Referencias:

- [operacion/models.py](D:/Proyectos/LeaseManager/Produccion%201.0/backend/operacion/models.py)
- [patrimonio/models.py](D:/Proyectos/LeaseManager/Produccion%201.0/backend/patrimonio/models.py)

## 4. Diagnostico del problema actual

### 4.1 Lo que el modelo actual representa mal

Para comunidades estandar, la realidad es:

- propietario economico: `ComunidadPatrimonial`;
- administrador real: `Joaquin`;
- recaudador bancario: `Santa Maria Ltda` mediante `Santa Maria II`;
- facturadora: ninguna.

El modelo actual no puede expresar eso sin forzar una mentira, porque si la cuenta pertenece a `Santa Maria`, entonces el mandato empuja a que `Santa Maria` sea el administrador operativo o la facturadora.

### 4.2 Lo que el modelo actual no puede representar

El caso `Edificio Q` no cabe fielmente porque:

- la comunidad incluye personas naturales;
- la comunidad incluye una empresa;
- la estructura actual de `ParticipacionPatrimonial` solo admite `Socio` como participante.

### 4.3 Riesgo de futuro si solo se corrige una parte

Si solo se agrega un nuevo actor `Recaudador` pero no se corrige el modelo patrimonial:

- se resuelven comunidades estandar;
- pero `Edificio Q` sigue siendo un caso torcido;
- el sistema queda con una mejora parcial y un segundo problema estructural pendiente.

Si solo se permite una excepcion para cuentas de terceros:

- se resuelve un caso puntual;
- pero no se vuelve explicita la responsabilidad de recaudacion;
- y se abren excepciones no auditables para otros flujos parecidos.

## 5. Evaluacion de alternativas

### 5.1 Opcion A - Dejar `Santa Maria` como administrador operativo

Resultado:

- implementacion simple;
- representacion de negocio falsa.

Problema:

- el sistema diria que `Santa Maria` administra comunidades cuando la administracion real la ejerce `Joaquin`.

Veredicto:

- descartada.

### 5.2 Opcion B - Mantener `Joaquin` como administrador y permitir que la cuenta pertenezca a un tercero

Resultado:

- resuelve el caso puntual;
- no hace explicito quien recauda realmente.

Problema:

- se convierte en excepcion especial;
- no modela el rol de recaudacion;
- se vuelve fragil para nuevos casos.

Veredicto:

- descartada.

### 5.3 Opcion C - Agregar `Recaudador` a `MandatoOperacion`

Resultado:

- separa administracion de recaudacion;
- alinea el modelo con el PRD.

Problema:

- no resuelve por si sola comunidades mixtas con `Empresa` participante;
- deja abierto el caso `Edificio Q`.

Veredicto:

- correcta como base, pero insuficiente como solucion final.

### 5.4 Opcion D - Solucion integrada

Componentes:

1. `MandatoOperacion` separa:
   - `Propietario`
   - `AdministradorOperativo`
   - `Recaudador`
   - `EntidadFacturadora`
2. `CuentaRecaudadora` debe pertenecer al `Recaudador` o a la `EntidadFacturadora`.
3. `ComunidadPatrimonial` admite participantes `Socio` o `Empresa`.
4. `AdministradorOperativo` sigue governando comunicacion.
5. `EntidadFacturadora` sigue governando SII.
6. `Recaudador` gobierna la cuenta recaudadora y conciliacion bancaria.

Veredicto:

- recomendada.

## 6. Solucion recomendada

### 6.1 Cambio 1 - Introducir `Recaudador` explicito en `MandatoOperacion`

Campos conceptuales nuevos:

- `recaudador_empresa_owner`
- `recaudador_socio_owner`

Reglas:

- exactamente un `Recaudador` cuando el mandato este activo;
- `CuentaRecaudadora` debe pertenecer al `Recaudador` o a la `EntidadFacturadora`;
- `AdministradorOperativo` ya no queda obligado a ser dueno de la cuenta;
- si `Recaudador != Propietario`, debe existir `autoriza_recaudacion`.

### 6.2 Cambio 2 - Permitir comunidades con participantes `Socio` o `Empresa`

Recomendacion de modelado:

- conservar el concepto canonico `ParticipacionPatrimonial`;
- ampliar la participacion para soportar `participante_socio` o `participante_empresa`;
- mantener integridad relacional con FKs explicitas, no `GenericForeignKey`.

Reglas:

- para `Empresa` como owner, los participantes pueden seguir siendo solo `Socio`;
- para `ComunidadPatrimonial` como owner, los participantes pueden ser `Socio` o `Empresa`;
- la suma activa debe seguir siendo exactamente `100%`.

### 6.3 Cambio 3 - Mantener `Representante` separado de `AdministradorOperativo`

Decicion recomendada:

- no mezclar `representante` patrimonial con `administrador operativo`;
- `representante` sigue en `Patrimonio`;
- `administrador operativo` vive en `MandatoOperacion`.

Esto permite:

- que una comunidad tenga un representante patrimonial definido;
- y que `Joaquin` administre operativamente aunque la cuenta bancaria pertenezca a otro actor.

Nota:

- si mas adelante se confirma que el representante puede no ser participante patrimonial, ese seria un refinamiento adicional;
- no es prerequisito para corregir el problema principal de recaudacion.

## 7. Impacto por subsistema

### 7.1 Operacion

Cambios obligatorios:

- `MandatoOperacion` agrega `Recaudador`;
- serializer y validaciones deben distinguir:
  - cuenta del recaudador;
  - identidad del administrador o facturadora.

### 7.2 Conciliacion

Sin ruptura conceptual:

- la conciliacion ya trabaja sobre `CuentaRecaudadora`;
- con `Recaudador` explicito, el ownership bancario queda correctamente modelado.

### 7.3 Canales

Regla recomendada:

- `IdentidadDeEnvio` debe pertenecer al `AdministradorOperativo` o a la `EntidadFacturadora`;
- no necesita pertenecer al `Recaudador`.

### 7.4 SII

Se mantiene igual:

- `EntidadFacturadora` sigue siendo quien emite;
- comunidades no facturan;
- la separacion de `Recaudador` no complica SII.

### 7.5 Contabilidad

Aqui hay un impacto critico.

Hoy el sistema resuelve empresa contable asi:

1. `EntidadFacturadora`
2. `AdministradorOperativo`
3. `CuentaRecaudadora.empresa_owner`

Eso es incorrecto para comunidades, porque podria reconocer como ingreso de empresa algo que en realidad es recaudacion en custodia para terceros.

Recomendacion:

- no usar `Recaudador` como sustituto automatico del beneficiario economico;
- para flujos de comunidad sin `EntidadFacturadora` ni propietario empresa, el sistema debe:
  - bloquear contabilidad automatica de empresa; o
  - enrutar a un flujo de custodia/distribucion no empresarial.

Mientras ese subdominio no exista, la implementacion segura es:

- `resolve_empresa_for_payment` no debe inferir empresa desde el `Recaudador` para propiedades de comunidad.

### 7.6 Reporting

Recomendacion:

- los reportes por empresa no deben contar pagos comunitarios solo porque entraron por una cuenta de empresa;
- deben usar beneficiario economico o facturadora, no recaudador bancario.

## 8. Como quedarian los casos reales

### 8.1 Comunidad estandar - Basilio Urrutia 633

- `Propietario`: `Comunidad Basilio Urrutia 633`
- participantes:
  - Cecilia `38.89%`
  - Geraldine `16.67%`
  - Cristobal `22.22%`
  - Joaquin `22.22%`
- `AdministradorOperativo`: `Joaquin`
- `Recaudador`: `Sociedad Inmobiliaria Santa Maria Ltda`
- `CuentaRecaudadora`: `8240452907`
- `EntidadFacturadora`: `null`

### 8.2 Comunidad mixta - Edificio Q

- `Propietario`: comunidad especifica de la propiedad
- participantes:
  - socios segun porcentaje;
  - `Inmobiliaria Puig SpA` como participante empresa
- `AdministradorOperativo`: segun operacion real
- `Recaudador`: actor que usa la cuenta bancaria real del flujo
- `EntidadFacturadora`: `Inmobiliaria Puig SpA` solo para la fraccion que factura cuando aplique

## 9. Riesgos reales si no se implementa asi

1. modelar como administrador a un actor que en realidad solo presta la cuenta bancaria;
2. registrar ingresos comunitarios como ingresos de empresa por simple propiedad de cuenta;
3. mantener a `Edificio Q` como excepcion permanente imposible de modelar bien;
4. acumular excepciones ad hoc en vez de roles de negocio explicitos.

## 10. Recomendacion final

La solucion final recomendada es:

1. separar `Recaudador` de `AdministradorOperativo` en `MandatoOperacion`;
2. ampliar la participacion de comunidad para soportar `Socio` o `Empresa`;
3. ajustar `Contabilidad` y `Reporting` para no confundir recaudacion bancaria con beneficio economico.

Esto resuelve:

- la verdad de negocio de comunidades;
- la cuenta contenedora `Santa Maria II`;
- las comunidades mixtas como `Edificio Q`;
- y evita que el backend actual mienta o contabilice mal.

## 11. Secuencia correcta para implementar

1. actualizar el modelo de `Operacion` con `Recaudador`;
2. actualizar el modelo patrimonial de participaciones comunitarias mixtas;
3. corregir reglas de `Contabilidad` y `Reporting` para no atribuir ingresos comunitarios al recaudador;
4. migrar y adaptar el pipeline de resolucion manual;
5. recien despues retomar resoluciones puntuales como `Basilio Urrutia 633`.

