import os
import importlib
import unicodedata

RUTA = os.path.join(os.path.dirname(__file__), 'diccionario.py')


def leer() -> dict:
    import g_de_flota.moderacion.diccionario as mod
    importlib.reload(mod)
    return dict(mod.PALABRAS)


def guardar(palabras: dict) -> None:
    lineas = [
        '"""\nDiccionario de palabras prohibidas.\n',
        'Gestionado desde el panel del SUPERADMIN.\n"""\n\n',
        'PALABRAS = {\n',
    ]
    for palabra, variantes in sorted(palabras.items()):
        vs = ', '.join(f'"{v}"' for v in variantes)
        lineas.append(f'    "{palabra}": [{vs}],\n')
    lineas.append('}\n')

    with open(RUTA, 'w', encoding='utf-8') as f:
        f.writelines(lineas)

    import g_de_flota.moderacion.diccionario as mod
    importlib.reload(mod)


def normalizar(texto: str) -> str:
    texto = texto.strip().lower()
    texto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn')


def agregar(palabra: str, variantes: list = None) -> dict:
    palabras  = leer()
    key       = normalizar(palabra)
    variantes = [normalizar(v) for v in (variantes or [])]

    if key in palabras:
        existentes = set(palabras[key])
        existentes.update(variantes)
        palabras[key] = list(existentes)
    else:
        palabras[key] = variantes

    guardar(palabras)
    return palabras


def agregar_lote(texto: str) -> dict:
    """
    Acepta texto con una palabra por línea.
    Formato opcional con variantes: weon:hueon,huevón
    """
    palabras  = leer()
    agregadas = 0

    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue

        if ':' in linea:
            partes    = linea.split(':', 1)
            key       = normalizar(partes[0])
            variantes = [normalizar(v.strip()) for v in partes[1].split(',') if v.strip()]
        else:
            key       = normalizar(linea)
            variantes = []

        if not key:
            continue

        if key in palabras:
            existentes = set(palabras[key])
            existentes.update(variantes)
            palabras[key] = list(existentes)
        else:
            palabras[key] = variantes
            agregadas += 1

    guardar(palabras)
    return {'agregadas': agregadas, 'total': len(palabras)}


def eliminar(palabra: str) -> dict:
    palabras = leer()
    key      = normalizar(palabra)
    if key in palabras:
        del palabras[key]
        guardar(palabras)
    return palabras
