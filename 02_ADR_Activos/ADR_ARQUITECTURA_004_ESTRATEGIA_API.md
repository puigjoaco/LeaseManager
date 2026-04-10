# ADR 004 - Estrategia de API y backend transaccional

Estado: aprobado  
Fecha: 15/03/2026  
PRD relacionado: [PRD_CANONICO.md](./PRD_CANONICO.md)

## Contexto

El maestro anterior congelaba `Django Ninja` como capa API y `Redis + Celery` como base async. La auditoria concluyo que el PRD no debe fijar librerias, pero la implementacion si necesita una decision clara para arrancar sin ambiguedad.

## Decision

LeaseManager adopta esta base tecnica para el v1:

1. `Django 5` como backend transaccional principal.
2. `Django REST Framework` como framework canonico de API para superficies de negocio y backoffice autenticado.
3. `React + TypeScript + Vite` como frontend web.
4. `Celery + Redis` como motor de jobs operativos y sincronizaciones async.
5. `Django Admin` queda permitido solo para operaciones internas de backoffice y soporte operacional; no reemplaza la superficie canonica del producto.
6. `Django Ninja` queda fuera del set activo del v1 y solo reingresa mediante reemision formal del set.

## Forma de implementacion

Uso de cada capa:

- `DRF`: CRUD transaccional, permisos, serializacion y APIs de negocio.
- `Celery`: notificaciones, sincronizaciones bancarias, tareas documentales y procesos recurrentes.
- `Redis`: broker y cache operativa no canonica del dominio.
- `React`: consola operacional y vistas por rol.

Reglas:

- ninguna regla de negocio vive solo en el frontend;
- un fallo de jobs no debe corromper el estado transaccional base;
- el sistema debe operar en modo degradado si cache o colas fallan.

## Consecuencias

- Se privilegia madurez de ecosistema y permisos sobre minimalismo de framework.
- Se mantiene una base robusta para ERP y backoffice.
- El PRD queda limpio de librerias, pero la implementacion arranca con una decision concreta.

## Alternativas descartadas

- Congelar `Django Ninja` en el PRD: descartado por mezcla de producto e implementacion.
- Usar dos frameworks API como default: descartado por complejidad innecesaria de v1.
- Postergar la decision de API framework: descartado por bloquear el arranque tecnico.

