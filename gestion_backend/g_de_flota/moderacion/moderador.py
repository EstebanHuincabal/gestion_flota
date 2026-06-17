import re
import json
import unicodedata
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _normalizar(texto: str) -> str:
    texto = texto.lower()
    for k, v in {'4': 'a', '@': 'a', '3': 'e', '1': 'i', '0': 'o', '5': 's'}.items():
        texto = texto.replace(k, v)
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', '', texto)).strip()


def _diccionario(texto: str) -> dict:
    from .gestor import leer
    texto_norm = _normalizar(texto)
    for palabra, variantes in leer().items():
        for termino in [palabra] + variantes:
            termino = termino.strip()
            if not termino:
                continue
            patron = re.escape(_normalizar(termino))
            if re.search(r'\b' + patron + r'\b', texto_norm):
                return {'detectado': True, 'palabra': palabra}
    return {'detectado': False, 'palabra': None}


PROMPT = """Eres moderador de contenido de un sistema de flotas en Chile.
Detecta insultos o lenguaje agresivo hacia personas.
NO es ofensivo: términos técnicos de mecánica, jerga de transporte, frustración sobre situaciones.
Responde solo JSON sin markdown:
{"aprobado": true/false, "razon": "", "sugerencia": ""}
Texto: """


def _gemini(texto: str) -> dict:
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        resp      = genai.GenerativeModel('gemini-2.5-flash').generate_content(PROMPT + texto)
        contenido = resp.text.strip().replace('```json', '').replace('```', '').strip()
        data      = json.loads(contenido)
        return {
            'aprobado':   data.get('aprobado', True),
            'razon':      data.get('razon', ''),
            'sugerencia': data.get('sugerencia', ''),
        }
    except Exception as e:
        logger.error(f'Moderación Gemini error: {e}')
        return {'aprobado': True, 'razon': '', 'sugerencia': ''}


def moderar(texto: str) -> dict:
    """
    Retorna: { aprobado: bool, razon: str, sugerencia: str, capa: str }
    """
    if not texto or len(texto.strip()) < 3:
        return {'aprobado': True, 'razon': '', 'sugerencia': '', 'capa': 'limpio'}

    dic = _diccionario(texto)
    if dic['detectado']:
        return {
            'aprobado':   False,
            'razon':      'Contiene lenguaje inapropiado.',
            'sugerencia': 'Por favor reformula tu mensaje de forma respetuosa.',
            'capa':       'diccionario',
        }

    if getattr(settings, 'GEMINI_API_KEY', None):
        ia = _gemini(texto)
        if not ia['aprobado']:
            return {
                'aprobado':   False,
                'razon':      ia['razon'],
                'sugerencia': ia['sugerencia'],
                'capa':       'ia',
            }

    return {'aprobado': True, 'razon': '', 'sugerencia': '', 'capa': 'limpio'}
