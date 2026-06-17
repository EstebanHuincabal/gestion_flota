from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


def _es_superadmin(request):
    return getattr(request.user, 'rol', None) == 'SUPERADMIN'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def moderar_texto(request):
    texto = str(request.data.get('texto', '')).strip()
    from g_de_flota.moderacion.moderador import moderar
    return Response(moderar(texto))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def palabras_list(request):
    if not _es_superadmin(request):
        return Response({'error': 'Sin acceso.'}, status=status.HTTP_403_FORBIDDEN)
    from g_de_flota.moderacion.gestor import leer
    palabras = leer()
    return Response({
        'palabras': [{'palabra': k, 'variantes': v} for k, v in sorted(palabras.items())],
        'total': len(palabras),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agregar_palabra(request):
    if not _es_superadmin(request):
        return Response({'error': 'Sin acceso.'}, status=status.HTTP_403_FORBIDDEN)
    palabra   = str(request.data.get('palabra', '')).strip()
    variantes = request.data.get('variantes', [])
    if not palabra:
        return Response({'error': 'Palabra requerida.'}, status=status.HTTP_400_BAD_REQUEST)
    from g_de_flota.moderacion.gestor import agregar
    palabras = agregar(palabra, variantes)
    return Response({'ok': True, 'total': len(palabras)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agregar_lote(request):
    if not _es_superadmin(request):
        return Response({'error': 'Sin acceso.'}, status=status.HTTP_403_FORBIDDEN)
    texto = str(request.data.get('texto', '')).strip()
    if not texto:
        return Response({'error': 'Texto requerido.'}, status=status.HTTP_400_BAD_REQUEST)
    from g_de_flota.moderacion.gestor import agregar_lote
    resultado = agregar_lote(texto)
    return Response({'ok': True, **resultado})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_palabra(request):
    if not _es_superadmin(request):
        return Response({'error': 'Sin acceso.'}, status=status.HTTP_403_FORBIDDEN)
    palabra = str(request.data.get('palabra', '')).strip()
    if not palabra:
        return Response({'error': 'Palabra requerida.'}, status=status.HTTP_400_BAD_REQUEST)
    from g_de_flota.moderacion.gestor import eliminar
    palabras = eliminar(palabra)
    return Response({'ok': True, 'total': len(palabras)})
