# ADR - Stack final recomendado para el v1

Estado: aprobado  
Fecha: 15/03/2026  
Relacionado con: [AUDITORIA_STACK_V1.md](./AUDITORIA_STACK_V1.md), [PRD_CANONICO.md](./PRD_CANONICO.md)

## Contexto

El set activo ya contaba con un stack base recomendado, pero faltaba una auditoria especifica y competitiva para validar si realmente era la mejor opcion para un ERP transaccional, auditable, contable y tributario como este.

## Decision

Se confirma como stack final recomendado del v1:

- arquitectura: monolito modular
- backend core: `Django 5`
- API: `Django REST Framework`
- base de datos: `PostgreSQL`
- jobs y tareas: `Celery + Redis`
- frontend: `React + TypeScript + Vite`
- documentos: `PDF` canonico con estrategia definida en ADR documental
- secretos: secret manager o KMS externo
- observabilidad: logging estructurado, healthchecks y metricas operativas

## Razones

1. Es el mejor fit global para un backoffice ERP con dominio rico, fuerte auditabilidad y reglas transaccionales.
2. Reduce el costo de arranque frente a candidatos mas ceremoniosos.
3. Mantiene una superficie interna muy util para operacion y soporte.
4. Evita sobre-ingenieria temprana.
5. Es razonable de operar y contratar para el contexto probable del proyecto.

## Lo que explicitamente no entra al stack activo

- `Django Ninja` como capa API base
- `pgvector` dentro del core del v1
- arquitecturas distribuidas como base del v1
- IA avanzada, portales o capacidades podadas reintroducidas por razones de moda

## Consecuencias

- no se requiere reemision del set activo por cambio de stack, porque el stack vigente fue confirmado;
- si conviene mantener la disciplina de no meter nuevas librerias core sin ADR;
- si en el futuro cambian el equipo, el dominio o la escala, una nueva auditoria podria reabrir esta decision.
