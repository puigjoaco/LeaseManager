# Pendientes y Proximos Pasos

## 1. Pendiente principal

El pendiente principal ya no es “abrir el siguiente modulo”, “cerrar migracion”, “sembrar roles” ni “conectar backend y frontend”.

La etapa actual deja como pendiente principal:

- **aprovechar correctamente el stack publico ya online, empezando por mejorar la representatividad de la data remota y luego elegir el siguiente frente funcional real sin romper la topologia publica ya cerrada**

## 2. Que ya no falta verificar

Ya no falta verificar, para este tramo:

- naming del greenfield;
- separacion del repo legacy;
- baseline local y staging de migracion comunitaria;
- backoffice base por modulos principales;
- seed reproducible de usuarios/roles/scopes demo;
- hardening inicial de scope por lectura y escritura;
- apertura de `Audit`, `Documentos` y `Canales` en frontend;
- modularizacion fuerte del frontend;
- frontend publico en Vercel;
- backend publico en Railway;
- `VITE_API_BASE_URL` conectada;
- login publico para `demo-admin`, `demo-operador`, `demo-revisor` y `demo-socio`;
- smoke publico basico por perfil en navegador real.

## 3. Trabajo que sigue abierto

### 3.1 Data remota / representatividad

- hoy el entorno publico funciona, pero muestra muy poca data operativa;
- conviene decidir si:
  - se carga un seed remoto mas representativo;
  - se migra un subconjunto seguro de data util;
  - o se deja el entorno publico como smoke-only y se sigue trabajando principalmente contra local.

### 3.2 Validacion publica residual

- aunque ya hubo smoke checks reales por los cuatro perfiles demo, todavia conviene seguir probando:
  - navegacion contextual con data real;
  - acciones operativas con registros no vacios;
  - lectura de reporting con payloads mas ricos;
  - consistencia entre frontend publico y backend publico en escenarios menos triviales.

### 3.3 Scope residual

- revisar si quedan endpoints o acciones sin scope efectivo en modulos menos transitados;
- en particular, conviene seguir mirando modulos secundarios sobre data no vacia, donde las fugas son mas faciles de detectar.

### 3.4 Siguiente frente funcional

`Compliance` ya quedo abierto en frontend para admin, ya tiene bootstrap demo remoto y ya paso smoke admin-only dedicada.

El proyecto podria seguir por una de estas dos lineas:

- profundizar la utilidad de `Contabilidad` / `SII` / `Reporting` ahora que el entorno remoto ya tiene mas datos derivados;
- o priorizar el siguiente frente funcional con mejor retorno, sin volver a abrir infraestructura ni el modulo `Compliance` como si siguiera sin validar.

## 4. Proximo paso recomendado

Secuencia recomendada para continuar correctamente:

1. mantener [puigjoaco/LeaseManager](https://github.com/puigjoaco/LeaseManager) como repo oficial;
2. mantener [https://leasemanager-backoffice.vercel.app](https://leasemanager-backoffice.vercel.app) como frontend publico vigente;
3. mantener [https://surprising-balance-production.up.railway.app](https://surprising-balance-production.up.railway.app) como backend publico vigente;
4. no mover `Root Directory=frontend` ni desconectar Git en Vercel;
5. no tocar Railway web/worker/Redis sin revalidacion completa;
6. usar los commands versionados de bootstrap demo remoto cuando haga falta;
7. tratar `Compliance` como modulo ya cerrado en smoke admin-only;
8. enriquecer la data remota donde aun siga vacia;
9. recien despues elegir el siguiente frente funcional del producto.

## 5. Que no hacer a continuacion

- no reabrir el diseno comunitario;
- no volver a discutir el naming `LeaseManager`;
- no asumir que los datos `TEST LOCAL` estan versionados;
- no volver a tratar `Vercel + Railway` como bootstrap pendiente;
- no romper `VITE_API_BASE_URL`, el root `frontend` o el wiring Git;
- no versionar secretos o valores sensibles del runtime remoto;
- no inferir que una vista “vacia” implica bug si el dataset remoto sigue siendo escaso.

## 6. Trabajo reservado para la siguiente etapa

### Etapa inmediata

- refresh documental del handoff con estado real actual;
- seguir enriqueciendo la data remota solo a traves de commands versionados o decisiones explicitas.

### Etapa posterior

- elegir el siguiente frente funcional real:
  - profundizacion de workflows operativos,
  - mas vida en `Contabilidad` / `SII`,
  - o nuevo hardening puntual sobre endpoints/acciones residuales.
