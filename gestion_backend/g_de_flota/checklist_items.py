"""
checklist_items.py — Ítems del checklist pre-viaje.

Cada ítem es una tupla: (id, categoria, nombre, descripcion, obligatorio)
"""

CHECKLIST_ITEMS = [
    ('doc_permiso',    'documentos', 'Permiso de circulación',   'Vigente y en el vehículo',  True),
    ('doc_revision',   'documentos', 'Revisión técnica',         'Vigente y en el vehículo',  True),
    ('doc_soap',       'documentos', 'Seguro SOAP',              'Vigente y en el vehículo',  True),
    ('doc_licencia',   'documentos', 'Licencia de conducir',     'Vigente y clase correcta',  True),
    ('mec_frenos',     'mecanica',   'Frenos',                   'Freno de pie y de mano',    True),
    ('mec_neumaticos', 'mecanica',   'Neumáticos',               'Estado y presión correcta', True),
    ('mec_aceite',     'mecanica',   'Nivel de aceite',          'En rango normal',           True),
    ('mec_combustible','mecanica',   'Nivel de combustible',     'Suficiente para la ruta',   True),
    ('mec_luces',      'mecanica',   'Luces y señalización',     'Todas funcionando',         True),
    ('seg_extintor',   'seguridad',  'Extintor',                 'Vigente y accesible',       True),
    ('seg_botiquin',   'seguridad',  'Botiquín',                 'Completo y accesible',      True),
    ('seg_triangulos', 'seguridad',  'Triángulos de emergencia', 'Presentes en el vehículo',  True),
]


def get_items():
    """Devuelve la lista de ítems como dicts."""
    return [
        {
            'id':          i[0],
            'categoria':   i[1],
            'nombre':      i[2],
            'descripcion': i[3],
            'obligatorio': i[4],
        }
        for i in CHECKLIST_ITEMS
    ]


# Mapa id → nombre (para armar resumen de fallas)
ITEMS_MAP = {i[0]: i[2] for i in CHECKLIST_ITEMS}

# Mapa tipo_doc del modelo Documento → id del ítem de checklist
MAP_DOC_ITEM = {
    'permiso_circulacion': 'doc_permiso',
    'revision_tecnica':    'doc_revision',
    'seguro_soap':         'doc_soap',
}
