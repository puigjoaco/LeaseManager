# ADR 007 - Activacion de IA semantica y pgvector

Estado: historico, fuera del boundary activo  
Fecha: 15/03/2026  
PRD relacionado: [PRD_CANONICO.md](./PRD_CANONICO.md)

> Nota: esta ADR queda fuera del set activo vigente. Las capacidades de IA semantica y asistente conversacional fueron podadas del boundary activo del v1 y solo podrian reingresar mediante nueva emision del set documental.

## Contexto

El maestro anterior incluia `pgvector` en el stack base pese a que las capacidades semanticas fuertes vivian en fases posteriores. Eso inflaba complejidad tecnica antes de tener caso de uso suficientemente cerrado.

## Decision

LeaseManager no exige IA semantica ni `pgvector` en el MVP obligatorio.

Decisiones aprobadas:

1. La plataforma parte con busqueda transaccional y reglas deterministicas.
2. `pgvector` solo se activa cuando el gate de `IA.Semantica` esta abierto.
3. El primer caso de uso valido para abrir ese gate debe ser alguno de estos:
   - exploracion semantica de expediente documental;
   - asistente conversacional con retrieval controlado;
   - clasificacion documental con evidencia de mejora operacional.
4. Cuando el gate se abra, `pgvector` sera el primer almacenamiento vectorial aprobado por convivencia con PostgreSQL.
5. Ninguna accion critica dependera exclusivamente de retrieval semantico.

## Forma de implementacion

Precondiciones para abrir `IA.Semantica`:

- caso de uso documentado;
- data set apto y autorizado;
- politica de masking y retencion definida;
- criterios de precision y rollback;
- aprobacion de arquitectura y seguridad.

## Consecuencias

- el MVP mantiene menor complejidad;
- se conserva una ruta clara para IA aplicada mas adelante;
- `pgvector` deja de ser una dependencia prematura, pero no se descarta como opcion aprobada.

## Alternativas descartadas

- incluir `pgvector` desde el dia cero sin caso de uso: descartado.
- usar un vector store externo como default inicial: descartado para v1.

