# Pendientes y Proximos Pasos

## 1. Pendiente principal

El pendiente principal ya no es “abrir el siguiente módulo”, “cerrar migración” ni “sembrar roles”.

La etapa actual deja como pendiente principal:

- **probar manualmente el sistema como `demo-operador`, `demo-revisor` y `demo-socio`, y cerrar cualquier hueco restante de visibilidad o mutación que aparezca en esa prueba**

## 2. Que ya no falta verificar

Ya no falta verificar, para este tramo:

- naming del greenfield;
- separación del repo legacy;
- baseline local y staging de migración comunitaria;
- backoffice base por módulos principales;
- navegación contextual;
- edición de registros core;
- permisos visibles en UI;
- permisos efectivos de backend por rol;
- seed reproducible de usuarios/roles/scopes demo;
- primer hardening de scope por lectura y escritura.

## 3. Trabajo que sigue abierto

### 3.1 Validación manual por perfil

- recorrer el backoffice local con:
  - `demo-operador`
  - `demo-revisor`
  - `demo-socio`
- anotar qué vistas, acciones o formularios todavía exponen más de lo debido;
- ajustar esos puntos sobre backend y, si corresponde, sobre UI.

### 3.2 Scope residual

- revisar si, además del hardening ya hecho, quedan endpoints o acciones sin scope efectivo;
- detectar módulos secundarios donde un rol con lectura válida todavía vea un subconjunto incorrecto.

### 3.3 Higiene/documentación

- revisar si se quiere actualizar [README.md](/D:/Proyectos/LeaseManager/Produccion%201.0/README.md), que hoy subestima el estado real del frontend.

### 3.4 Módulos no expuestos todavía en frontend

El backend ya tiene superficie en:

- `Documentos`
- `Canales`
- `Audit`
- `Compliance`

Todavía no están trabajados con el mismo nivel de UX/backoffice que los módulos principales ya cubiertos.

## 4. Proximo paso recomendado

Secuencia recomendada para continuar correctamente:

1. mantener [puigjoaco/LeaseManager](https://github.com/puigjoaco/LeaseManager) como repo oficial;
2. mantener `leasemanager_migration_run_20260409_v7` como baseline local;
3. probar el sistema con cada perfil demo;
4. corregir permisos finos o alcance por scope donde la experiencia real falle;
5. recién después decidir si conviene:
   - abrir `Documentos/Canales/Audit/Compliance` en frontend;
   - o mejorar filtros persistentes y búsquedas.

## 5. Que no hacer a continuación

- no reabrir el diseño comunitario;
- no volver a discutir el naming `LeaseManager`;
- no asumir que los datos `TEST LOCAL` están versionados;
- no tratar la UI role-aware como sustituto del permiso backend;
- no mezclar el refresh documental pendiente con cambios de producto sin revisar el alcance.

## 6. Trabajo reservado para la siguiente etapa

### Etapa inmediata

- pruebas de experiencia real como perfiles no-admin;
- cierre de huecos residuales de scope.

### Etapa posterior

- apertura de módulos secundarios en frontend si sigue haciendo sentido;
- o modularización adicional del frontend si el costo de cambio en `App.tsx` sigue creciendo.
