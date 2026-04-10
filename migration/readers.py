from __future__ import annotations

from psycopg import connect
from psycopg.rows import dict_row


TABLE_QUERIES = {
    'empresas': """
        SELECT id, rut, nombre, razon_social, direccion, comuna, ciudad, giro, activa, standard_contable
        FROM empresas
        ORDER BY created_at
    """,
    'socios': """
        SELECT id, rut, nombre, apellido_paterno, apellido_materno, nombre_completo, email, telefono, direccion, domicilio
        FROM socios
        ORDER BY created_at
    """,
    'comunidades': """
        SELECT id, nombre, descripcion
        FROM comunidades
        ORDER BY created_at
    """,
    'participaciones': """
        SELECT id, socio_id, empresa_id, propiedad_id, comunidad_id, porcentaje, porcentaje_participacion, activa, fecha_inicio, fecha_fin
        FROM participaciones
        ORDER BY created_at
    """,
    'propiedades': """
        SELECT id, codigo, codigo_propiedad, tipo, tipo_propiedad, direccion, numero, depto, comuna, ciudad, rol, rol_tributario,
               empresa_id, socio_id, comunidad_id, es_comunidad, estado
        FROM propiedades
        ORDER BY created_at
    """,
    'cuentas_bancarias': """
        SELECT id, banco, nombre_banco, numero_cuenta, tipo_cuenta, empresa_id, moneda, activa
        FROM cuentas_bancarias
        ORDER BY created_at
    """,
    'arrendatarios': """
        SELECT id, rut, nombre, apellido_paterno, apellido_materno, razon_social, tipo, email, telefono, direccion,
               nombre_completo, comuna, ciudad, estado_registro
        FROM arrendatarios
        ORDER BY created_at
    """,
    'contratos': """
        SELECT id, propiedad_id, arrendatario_id, fecha_inicio, fecha_termino, valor_arriendo, moneda, dia_pago,
               dias_alerta_admin, dias_aviso_termino, garantia_requerida, requiere_garantia, estado
        FROM contratos
        ORDER BY created_at
    """,
    'periodos_contractuales': """
        SELECT id, contrato_id, fecha_inicio, fecha_termino, valor_arriendo, moneda, activo, numero_periodo
        FROM periodos_contractuales
        ORDER BY created_at
    """,
}


def fetch_legacy_rows(connection_string):
    results = {}
    with connect(connection_string, row_factory=dict_row) as conn:
        conn.execute("SET default_transaction_read_only = on")
        with conn.cursor() as cursor:
            for table_name, query in TABLE_QUERIES.items():
                cursor.execute(query)
                results[table_name] = [dict(row) for row in cursor.fetchall()]
    return results
