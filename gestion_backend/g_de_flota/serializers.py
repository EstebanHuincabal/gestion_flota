import re
import hashlib
from rest_framework import serializers
from .models import (
    Empresa, Usuario, Rol, Permiso, normalizar_rut, REGIONES_CHILE,
    Flota, Vehiculo, Asignacion, PlanSuscripcion, CambioPlan, LogAuditoria,
    Mantencion, Documento, SolicitudConductor, descifrar,
)


# ─────────────────────────────────────────
# Permiso
# ─────────────────────────────────────────

class PermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Permiso
        fields = ['id', 'codigo', 'nombre', 'categoria']


# ─────────────────────────────────────────
# Helpers RUT
# ─────────────────────────────────────────

def _validar_dv_rut(rut_norm: str) -> bool:
    """Valida dígito verificador con módulo 11. rut_norm: 'XXXXXXXX-Y' sin puntos, en minúscula."""
    if '-' not in rut_norm:
        return False
    partes = rut_norm.split('-')
    if len(partes) != 2:
        return False
    cuerpo, dv = partes
    if not cuerpo.isdigit() or dv not in '0123456789k':
        return False
    # RUTs chilenos válidos tienen entre 7 y 8 dígitos en el cuerpo
    if len(cuerpo) < 7:
        return False
    suma = 0
    serie = [2, 3, 4, 5, 6, 7]
    for i, digito in enumerate(reversed(cuerpo)):
        suma += int(digito) * serie[i % 6]
    resto = suma % 11
    dv_calc = 11 - resto
    if dv_calc == 11:
        esperado = '0'
    elif dv_calc == 10:
        esperado = 'k'
    else:
        esperado = str(dv_calc)
    return dv == esperado


# ─────────────────────────────────────────
# Empresa
# ─────────────────────────────────────────

_REGIONES_CODIGOS = {code for code, _ in REGIONES_CHILE}


class EmpresaSerializer(serializers.Serializer):
    id       = serializers.IntegerField(read_only=True)
    nombre   = serializers.CharField(max_length=30)
    rut      = serializers.CharField()
    email    = serializers.EmailField(required=False, allow_blank=True, default='')
    telefono = serializers.CharField(required=False, allow_blank=True, default='')
    direccion = serializers.CharField(required=False, allow_blank=True, default='', max_length=40)
    comuna   = serializers.CharField(required=False, allow_blank=True, default='')
    ciudad   = serializers.CharField(required=False, allow_blank=True, default='')
    region   = serializers.CharField(required=False, allow_blank=True, default='')
    pais     = serializers.CharField(required=False, allow_blank=True, default='Chile')
    estado   = serializers.CharField(default='activa')
    plan_id   = serializers.IntegerField(required=False, allow_null=True, default=None)
    plan_nombre = serializers.SerializerMethodField()
    created_at           = serializers.DateTimeField(read_only=True)
    cantidad_flotas      = serializers.SerializerMethodField()
    cantidad_vehiculos   = serializers.SerializerMethodField()
    cantidad_conductores = serializers.SerializerMethodField()
    ultima_actividad     = serializers.SerializerMethodField()

    def get_plan_nombre(self, obj):          return obj.plan.get_nombre_display() if obj.plan else None

    def get_cantidad_flotas(self, obj):      return getattr(obj, 'cantidad_flotas', None)
    def get_cantidad_vehiculos(self, obj):   return getattr(obj, 'cantidad_vehiculos', None)
    def get_cantidad_conductores(self, obj): return getattr(obj, 'cantidad_conductores', None)
    def get_ultima_actividad(self, obj):     return getattr(obj, 'ultima_actividad', None)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['rut']      = instance.rut
        ret['email']    = instance.email
        ret['telefono'] = instance.telefono
        ret['direccion'] = instance.direccion
        ret['comuna']   = instance.comuna
        ret['ciudad']   = instance.ciudad
        return ret

    def validate_nombre(self, value):
        value = value.strip()
        if len(value) > 30:
            raise serializers.ValidationError("El nombre no puede superar los 30 caracteres.")
        qs = Empresa.objects.filter(nombre__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe una empresa con ese nombre.")
        return value

    def validate_rut(self, value):
        rut_norm = normalizar_rut(value)
        if not _validar_dv_rut(rut_norm):
            raise serializers.ValidationError("El RUT ingresado no es válido.")
        rut_hash = hashlib.sha256(rut_norm.encode()).hexdigest()
        qs = Empresa.objects.filter(rut_hash=rut_hash)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe una empresa con ese RUT.")
        return value

    def validate_region(self, value):
        if value and value not in _REGIONES_CODIGOS:
            raise serializers.ValidationError("Región no válida.")
        return value

    def validate_telefono(self, value):
        if not value:
            return value
        limpio = re.sub(r'[\s\-\(\)]', '', value)
        if not re.match(r'^(\+56)?9\d{8}$', limpio):
            raise serializers.ValidationError(
                'Teléfono inválido. Use el formato +569 XXXXXXXX o 9XXXXXXXX.'
            )
        return limpio

    def validate_estado(self, value):
        if value not in ('activa', 'suspendida'):
            raise serializers.ValidationError("Estado no válido.")
        return value

    def create(self, validated_data):
        validated_data.pop('plan_id', None)
        rut       = validated_data.pop('rut', None)
        email     = validated_data.pop('email', '')
        telefono  = validated_data.pop('telefono', '')
        direccion = validated_data.pop('direccion', '')
        comuna    = validated_data.pop('comuna', '')
        ciudad    = validated_data.pop('ciudad', '')

        empresa = Empresa(**validated_data)
        if rut:
            empresa.set_rut(rut)
        if email:
            empresa.set_email(email)
        if telefono:
            empresa.set_telefono(telefono)
        if direccion:
            empresa.set_direccion(direccion)
        if comuna:
            empresa.set_comuna(comuna)
        if ciudad:
            empresa.set_ciudad(ciudad)
        empresa.save()
        return empresa

    def update(self, instance, validated_data):
        validated_data.pop('plan_id', None)
        rut       = validated_data.pop('rut', None)
        email     = validated_data.pop('email', None)
        telefono  = validated_data.pop('telefono', None)
        direccion = validated_data.pop('direccion', None)
        comuna    = validated_data.pop('comuna', None)
        ciudad    = validated_data.pop('ciudad', None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        if rut is not None:
            instance.set_rut(rut)
        if email is not None:
            instance.set_email(email) if email else setattr(instance, 'email_cifrado', None)
        if telefono is not None:
            instance.set_telefono(telefono) if telefono else setattr(instance, 'telefono_cifrado', None)
        if direccion is not None:
            instance.set_direccion(direccion) if direccion else setattr(instance, 'direccion_cifrada', None)
        if comuna is not None:
            instance.set_comuna(comuna) if comuna else setattr(instance, 'comuna_cifrada', None)
        if ciudad is not None:
            instance.set_ciudad(ciudad) if ciudad else setattr(instance, 'ciudad_cifrada', None)

        instance.save()
        return instance


# ─────────────────────────────────────────
# Usuario — lectura
# ─────────────────────────────────────────

class UsuarioListSerializer(serializers.ModelSerializer):
    nombre           = serializers.SerializerMethodField()
    primer_nombre    = serializers.SerializerMethodField()
    apellido_paterno = serializers.SerializerMethodField()
    apellido_materno = serializers.SerializerMethodField()
    telefono         = serializers.SerializerMethodField()
    rut        = serializers.SerializerMethodField()
    empresa    = serializers.SerializerMethodField()
    empresa_id = serializers.SerializerMethodField()
    permisos   = serializers.SerializerMethodField()

    class Meta:
        model  = Usuario
        fields = ['id', 'nombre', 'primer_nombre', 'apellido_paterno', 'apellido_materno',
                  'telefono', 'rut', 'email', 'rol', 'empresa', 'empresa_id',
                  'is_active', 'is_blocked', 'permisos']

    def get_nombre(self, obj):
        return obj.nombre

    def get_primer_nombre(self, obj):
        return obj.primer_nombre

    def get_apellido_paterno(self, obj):
        return obj.apellido_paterno

    def get_apellido_materno(self, obj):
        return obj.apellido_materno

    def get_telefono(self, obj):
        return obj.telefono

    def get_rut(self, obj):
        return obj.rut

    def get_empresa(self, obj):
        return obj.empresa.nombre if obj.empresa else None

    def get_empresa_id(self, obj):
        return obj.empresa_id

    def get_permisos(self, obj):
        return list(obj.permisos.values_list('codigo', flat=True))


# ─────────────────────────────────────────
# Usuario — creación
# ─────────────────────────────────────────

class UsuarioCrearSerializer(serializers.Serializer):
    nombre           = serializers.CharField()
    apellido_paterno = serializers.CharField()
    apellido_materno = serializers.CharField()
    telefono         = serializers.CharField()
    rut              = serializers.CharField()
    email            = serializers.EmailField()
    password         = serializers.CharField(write_only=True)
    rol              = serializers.ChoiceField(choices=Rol.choices)
    empresa_id       = serializers.IntegerField(required=False, allow_null=True)
    permisos         = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )

    def validate_nombre(self, value):
        return value.strip().title()

    def validate_apellido_paterno(self, value):
        return value.strip().title()

    def validate_apellido_materno(self, value):
        return value.strip().title()

    def validate_telefono(self, value):
        limpio = re.sub(r'[\s\-\(\)]', '', value or '')
        if not re.match(r'^(\+56)?9\d{8}$', limpio):
            raise serializers.ValidationError(
                'Teléfono inválido. Use el formato +569 XXXXXXXX o 9XXXXXXXX.'
            )
        return limpio

    def validate_email(self, value):
        return value.strip().lower()

    def validate_rut(self, value):
        rut_norm = normalizar_rut(value)
        if not _validar_dv_rut(rut_norm):
            raise serializers.ValidationError("El RUT ingresado no es válido.")
        rut_hash = hashlib.sha256(rut_norm.encode()).hexdigest()
        if Usuario.objects.filter(rut_hash=rut_hash).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese RUT.")
        return rut_norm

    def validate(self, data):
        if data.get('rol') in (Rol.USUARIO, Rol.CONDUCTOR) and not data.get('empresa_id'):
            raise serializers.ValidationError(
                {"empresa_id": f"El rol {data['rol']} requiere empresa asignada."}
            )
        return data

    def create(self, validated_data):
        empresa_id    = validated_data.pop('empresa_id', None)
        rol           = validated_data.pop('rol')
        password      = validated_data.pop('password')
        codigos_permisos = validated_data.pop('permisos', [])
        nombre        = validated_data['nombre']
        ap_paterno    = validated_data['apellido_paterno']
        ap_materno    = validated_data['apellido_materno']
        telefono      = validated_data['telefono']
        empresa       = Empresa.objects.filter(pk=empresa_id).first() if empresa_id else None

        nombre_completo = ' '.join(p for p in [nombre, ap_paterno, ap_materno] if p)
        user = Usuario.objects.create_user(
            email           = validated_data['email'],
            rut             = validated_data['rut'],
            nombre_completo = nombre_completo,
            password        = password,
            rol             = rol,
            empresa         = empresa,
        )
        user.set_nombre_partes(nombre, ap_paterno, ap_materno)
        user.set_telefono(telefono)
        user.save(update_fields=[
            'primer_nombre_cifrado', 'apellido_paterno_cifrado',
            'apellido_materno_cifrado', 'nombre_cifrado', 'telefono_cifrado',
        ])
        if codigos_permisos and rol == Rol.USUARIO:
            permisos = Permiso.objects.filter(codigo__in=codigos_permisos)
            user.permisos.set(permisos)
        return user


# ─────────────────────────────────────────
# Usuario — edición
# ─────────────────────────────────────────

class UsuarioEditarSerializer(serializers.Serializer):
    nombre           = serializers.CharField(required=False)
    apellido_paterno = serializers.CharField(required=False)
    apellido_materno = serializers.CharField(required=False)
    telefono         = serializers.CharField(required=False)
    email            = serializers.EmailField(required=False)
    rol              = serializers.ChoiceField(choices=Rol.choices, required=False)
    empresa_id       = serializers.IntegerField(required=False, allow_null=True)
    is_active        = serializers.BooleanField(required=False)
    permisos         = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )

    def validate_nombre(self, value):
        return value.strip().title()

    def validate_apellido_paterno(self, value):
        return value.strip().title()

    def validate_apellido_materno(self, value):
        return value.strip().title()

    def validate_telefono(self, value):
        if not value:
            return value
        limpio = re.sub(r'[\s\-\(\)]', '', value)
        if not re.match(r'^(\+56)?9\d{8}$', limpio):
            raise serializers.ValidationError(
                'Teléfono inválido. Use el formato +569 XXXXXXXX o 9XXXXXXXX.'
            )
        return limpio

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, data):
        rol        = data.get('rol') or self.instance.rol
        empresa_id = data.get('empresa_id', self.instance.empresa_id)
        if rol in (Rol.USUARIO, Rol.CONDUCTOR) and not empresa_id:
            raise serializers.ValidationError(
                {"empresa_id": f"El rol {rol} requiere empresa asignada."}
            )
        return data

    def update(self, instance, validated_data):
        codigos_permisos = validated_data.pop('permisos', None)
        # Si llega cualquier parte del nombre, recomponer con las 3 (usando las existentes)
        if any(k in validated_data for k in ('nombre', 'apellido_paterno', 'apellido_materno')):
            nombre     = validated_data.get('nombre',           instance.primer_nombre or '')
            ap_paterno = validated_data.get('apellido_paterno', instance.apellido_paterno or '')
            ap_materno = validated_data.get('apellido_materno', instance.apellido_materno or '')
            instance.set_nombre_partes(nombre, ap_paterno, ap_materno)
        if 'telefono' in validated_data:
            if validated_data['telefono']:
                instance.set_telefono(validated_data['telefono'])
            else:
                instance.telefono_cifrado = None
        if 'email' in validated_data:
            instance.email = validated_data['email']
        if 'rol' in validated_data:
            instance.rol = validated_data['rol']
        if 'empresa_id' in validated_data:
            instance.empresa = Empresa.objects.filter(pk=validated_data['empresa_id']).first() \
                               if validated_data['empresa_id'] else None
        if 'is_active' in validated_data:
            instance.is_active = validated_data['is_active']
        instance.save()
        if codigos_permisos is not None and instance.rol == Rol.USUARIO:
            permisos = Permiso.objects.filter(codigo__in=codigos_permisos)
            instance.permisos.set(permisos)
        return instance


# ─────────────────────────────────────────
# Conductores
# ─────────────────────────────────────────

class ConductorListSerializer(serializers.ModelSerializer):
    nombre   = serializers.SerializerMethodField()
    primer_nombre    = serializers.SerializerMethodField()
    apellido_paterno = serializers.SerializerMethodField()
    apellido_materno = serializers.SerializerMethodField()
    rut      = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()
    licencia = serializers.SerializerMethodField()
    vehiculo = serializers.SerializerMethodField()
    empresa_nombre = serializers.SerializerMethodField()

    class Meta:
        model  = Usuario
        fields = ['id', 'nombre', 'primer_nombre', 'apellido_paterno', 'apellido_materno',
                  'rut', 'email', 'telefono', 'licencia', 'vehiculo', 'is_active', 'empresa_nombre']

    def get_nombre(self, obj):   return obj.nombre
    def get_primer_nombre(self, obj):    return obj.primer_nombre
    def get_apellido_paterno(self, obj): return obj.apellido_paterno
    def get_apellido_materno(self, obj): return obj.apellido_materno
    def get_rut(self, obj):      return obj.rut
    def get_empresa_nombre(self, obj): return obj.empresa.nombre if obj.empresa else None

    def get_telefono(self, obj):
        if obj.telefono: return obj.telefono
        try:    return obj.perfil.telefono
        except: return None

    def get_licencia(self, obj):
        if obj.licencia: return obj.licencia
        try:    return obj.perfil.licencia
        except: return None

    def get_vehiculo(self, obj):
        try:
            asig = obj.asignaciones_conductor.filter(activo=True).select_related('vehiculo').first()
            if not asig and hasattr(obj, 'perfil'):
                asig = obj.perfil.asignaciones.filter(activo=True).select_related('vehiculo').first()
            if asig:
                v = asig.vehiculo
                return {'id': v.id, 'patente': v.patente, 'descripcion': f"{v.marca} {v.modelo}".strip()}
        except:
            pass
        return None

class MantencionSerializer(serializers.ModelSerializer):
    vehiculo_id           = serializers.PrimaryKeyRelatedField(
                                queryset=Vehiculo.objects.all(),
                                source='vehiculo'
                            )
    vehiculo_patente      = serializers.CharField(source='vehiculo.patente', read_only=True)
    vehiculo_descripcion  = serializers.SerializerMethodField()
    estado_display        = serializers.CharField(source='get_estado_display', read_only=True)
    foto_comprobante_url  = serializers.SerializerMethodField()
    confirmado_conductor  = serializers.BooleanField(read_only=True)
    fecha_confirmacion    = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Mantencion
        fields = [
            'id', 'vehiculo_id', 'vehiculo_patente', 'vehiculo_descripcion',
            'tipo_mantencion', 'descripcion', 'taller_proveedor', 'presupuesto',
            'fecha_programada', 'kilometraje_programado',
            'fecha_realizada', 'kilometraje_realizado',
            'estado', 'estado_display', 'costo',
            'foto_comprobante_url', 'confirmado_conductor', 'fecha_confirmacion',
        ]

    def get_vehiculo_descripcion(self, obj):
        return f"{obj.vehiculo.marca} {obj.vehiculo.modelo}".strip()

    def get_foto_comprobante_url(self, obj):
        if not obj.foto_comprobante:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.foto_comprobante.url)
        return obj.foto_comprobante.url

class AsignacionHistorialSerializer(serializers.ModelSerializer):
    vehiculo_patente = serializers.CharField(source='vehiculo.patente', read_only=True)
    vehiculo_descripcion = serializers.SerializerMethodField()
    
    class Meta:
        model = Asignacion
        fields = ['id', 'vehiculo_id', 'vehiculo_patente', 'vehiculo_descripcion', 'activo', 'desde', 'hasta']

    def get_vehiculo_descripcion(self, obj):
        return f"{obj.vehiculo.marca} {obj.vehiculo.modelo}".strip()

class ConductorDetalleSerializer(ConductorListSerializer):
    documentos_conductor = serializers.SerializerMethodField()
    vehiculo_detalle = serializers.SerializerMethodField()
    historial_asignaciones = serializers.SerializerMethodField()
    empresa_admin = serializers.SerializerMethodField()

    class Meta(ConductorListSerializer.Meta):
        fields = ConductorListSerializer.Meta.fields + [
            'documentos_conductor', 'vehiculo_detalle', 'historial_asignaciones', 'empresa_admin'
        ]

    def get_empresa_admin(self, obj):
        if not obj.empresa: return None
        admin = Usuario.objects.filter(empresa=obj.empresa, rol=Rol.USUARIO, is_active=True).first()
        if admin:
            return {"nombre": admin.nombre, "email": admin.email}
        return None

    def get_documentos_conductor(self, obj):
        tipos = dict(Documento.TODOS_TIPOS)
        return [
            {
                'id': d.id,
                'tipo': d.tipo,
                'tipo_display': tipos.get(d.tipo, d.tipo),
                'fecha_vencimiento': d.fecha_vencimiento,
                'estado': d.estado(),
            }
            for d in Documento.objects.filter(entidad='conductor', conductor=obj)
        ]

    def get_vehiculo_detalle(self, obj):
        asig = obj.asignaciones_conductor.filter(activo=True).select_related('vehiculo__flota__empresa').first()
        if not asig and hasattr(obj, 'perfil'):
            asig = obj.perfil.asignaciones.filter(activo=True).select_related('vehiculo__flota__empresa').first()
        if not asig: return None
        v = asig.vehiculo
        return {
            'id': v.id,
            'patente': v.patente,
            'descripcion': f"{v.marca} {v.modelo}".strip(),
            'anio': v.anio,
            'tipo_combustible': v.get_tipo_combustible_display() if hasattr(v, 'get_tipo_combustible_display') else v.tipo_combustible,
            'km_actuales': v.km_actuales,
            'empresa_nombre': v.flota.empresa.nombre if v.flota and v.flota.empresa else None,
            'documentos': [
                {
                    'id': d.id,
                    'tipo': d.tipo,
                    'tipo_display': dict(Documento.TODOS_TIPOS).get(d.tipo, d.tipo),
                    'fecha_vencimiento': d.fecha_vencimiento,
                    'estado': d.estado(),
                }
                for d in v.docs_v.all()
            ],
            'mantenciones': MantencionSerializer(v.mantenciones.all(), many=True).data,
        }

    def get_historial_asignaciones(self, obj):
        asigs = list(obj.asignaciones_conductor.all())
        if hasattr(obj, 'perfil'):
            asigs += list(obj.perfil.asignaciones.all())
        asigs.sort(key=lambda x: x.desde, reverse=True)
        return AsignacionHistorialSerializer(asigs, many=True).data


class ConductorCrearSerializer(serializers.Serializer):
    nombre           = serializers.CharField()
    apellido_paterno = serializers.CharField()
    apellido_materno = serializers.CharField()
    rut             = serializers.CharField()
    email           = serializers.EmailField()
    password        = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')
    telefono        = serializers.CharField()
    licencia        = serializers.CharField(required=False, allow_blank=True)

    # Opciones de asignación inicial
    vehiculo_id          = serializers.IntegerField(required=False, allow_null=True)
    crear_vehiculo       = serializers.BooleanField(default=False)
    vehiculo_patente     = serializers.CharField(required=False, allow_blank=True)
    vehiculo_marca       = serializers.CharField(required=False, allow_blank=True)
    vehiculo_modelo      = serializers.CharField(required=False, allow_blank=True)
    vehiculo_flota_id    = serializers.IntegerField(required=False, allow_null=True)
    vehiculo_flota_nuevo = serializers.CharField(required=False, allow_blank=True)

    def validate_nombre(self, value):
        return value.strip().title()

    def validate_apellido_paterno(self, value):
        return value.strip().title()

    def validate_apellido_materno(self, value):
        return value.strip().title()

    def validate_email(self, value):
        return value.strip().lower()

    def validate_rut(self, value):
        rut_norm = normalizar_rut(value)
        if not _validar_dv_rut(rut_norm):
            raise serializers.ValidationError("El RUT ingresado no es válido.")
        rut_hash = hashlib.sha256(rut_norm.encode()).hexdigest()
        if Usuario.objects.filter(rut_hash=rut_hash).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese RUT.")
        return rut_norm

    def validate_telefono(self, value):
        limpio = re.sub(r'[\s\-\(\)]', '', value or '')
        if not re.match(r'^(\+56)?9\d{8}$', limpio):
            raise serializers.ValidationError(
                'Teléfono inválido. Use el formato +569 XXXXXXXX o 9XXXXXXXX.'
            )
        return limpio

    def validate_licencia(self, value):
        if not value: return value
        return value.strip().upper()

    def validate(self, data):
        empresa = self.context.get('empresa')
        
        # Validar lógica de creación de vehículo si aplica
        if data.get('crear_vehiculo'):
            patente = data.get('vehiculo_patente', '').replace(' ', '').replace('-', '').upper().strip()
            if not patente:
                raise serializers.ValidationError({"vehiculo_patente": "La patente es obligatoria para crear un vehículo."})
            if Vehiculo.objects.filter(patente_hash=Vehiculo.hash_patente(patente)).exists():
                raise serializers.ValidationError({"vehiculo_patente": "Ya existe un vehículo con esta patente."})
            
            # Validación de Flota
            flota_id = data.get('vehiculo_flota_id')
            nueva_flota_nombre = data.get('vehiculo_flota_nuevo', '').strip()
            
            if not flota_id and not nueva_flota_nombre:
                # Si no hay flotas en la empresa, permitimos que se cree una por defecto
                if not Flota.objects.filter(empresa=empresa).exists():
                    data['vehiculo_flota_nuevo'] = "Flota Principal"
                else:
                    raise serializers.ValidationError({"vehiculo_flota_id": "Debe seleccionar una flota o crear una nueva."})
            
            # Si quiere crear una nueva flota, validar límite
            if nueva_flota_nombre:
                if empresa.plan:
                    actuales = Flota.objects.filter(empresa=empresa).count()
                    if actuales >= empresa.plan.max_flotas:
                        raise serializers.ValidationError({
                            "vehiculo_flota_nuevo": f"Has alcanzado el límite de {empresa.plan.max_flotas} flotas de tu plan."
                        })

            data['vehiculo_patente'] = patente
        elif data.get('vehiculo_id'):
            v_id = data.get('vehiculo_id')
            if not Vehiculo.objects.filter(pk=v_id, activo=True).exists():
                raise serializers.ValidationError({"vehiculo_id": "El vehículo seleccionado no existe o no está activo."})
            if Asignacion.objects.filter(vehiculo_id=v_id, activo=True).exists():
                raise serializers.ValidationError({"vehiculo_id": "Este vehiculo ya fue asignado"})
        return data

    def create(self, validated_data):
        import secrets
        from .email_service import email_acceso_conductor

        empresa  = self.context['empresa']
        telefono = validated_data.pop('telefono', None)
        licencia = validated_data.pop('licencia', None)
        password_raw = validated_data.pop('password', '').strip()

        # Si no se proporcionó contraseña, generar una segura y enviarla por correo
        clave_generada = None
        if not password_raw:
            clave_generada = secrets.token_urlsafe(10)
            password_raw   = clave_generada

        password   = password_raw
        nombre     = validated_data['nombre']
        ap_paterno = validated_data['apellido_paterno']
        ap_materno = validated_data['apellido_materno']

        # Datos de vehículo/asignación
        vehiculo_id       = validated_data.pop('vehiculo_id', None)
        crear_vehiculo    = validated_data.pop('crear_vehiculo', False)
        v_patente         = validated_data.pop('vehiculo_patente', None)
        v_marca           = validated_data.pop('vehiculo_marca', '')
        v_modelo          = validated_data.pop('vehiculo_modelo', '')
        v_flota_id        = validated_data.pop('vehiculo_flota_id', None)
        v_flota_nuevo     = validated_data.pop('vehiculo_flota_nuevo', '').strip()

        nombre_completo = ' '.join(p for p in [nombre, ap_paterno, ap_materno] if p)
        user = Usuario.objects.create_user(
            email           = validated_data['email'],
            rut             = validated_data['rut'],
            nombre_completo = nombre_completo,
            password        = password,
            rol             = Rol.CONDUCTOR,
            empresa         = empresa,
        )

        user.set_nombre_partes(nombre, ap_paterno, ap_materno)
        if telefono:
            user.set_telefono(telefono)
        if licencia:
            user.set_licencia(licencia)
        else:
            user.extra['requiere_licencia'] = True
        user.save()

        # Enviar credenciales por correo si la contraseña fue generada
        if clave_generada:
            try:
                email_acceso_conductor(
                    email          = validated_data['email'],
                    nombre         = nombre,
                    empresa_nombre = empresa.nombre,
                    rut            = validated_data['rut'],
                    clave_temporal = clave_generada,
                )
            except Exception:
                pass  # fail-silent — el conductor puede pedir reset luego

        # Lógica de asignación
        final_vehiculo_id = None
        if crear_vehiculo:
            # Gestionar Flota
            if v_flota_nuevo:
                flota = Flota.objects.create(empresa=empresa, nombre=v_flota_nuevo)
                v_flota_id = flota.id
            
            try:
                nuevo_v = Vehiculo.objects.create(
                    patente = v_patente,
                    marca   = v_marca,
                    modelo  = v_modelo,
                    flota_id = v_flota_id,
                    activo  = True
                )
                final_vehiculo_id = nuevo_v.id
            except Exception:
                pass 
        elif vehiculo_id:
            final_vehiculo_id = vehiculo_id

        if final_vehiculo_id:
            from django.utils import timezone
            Asignacion.objects.create(
                conductor=user,
                vehiculo_id=final_vehiculo_id,
                activo=True,
                desde=timezone.now()
            )

        return user


class ConductorEditarSerializer(serializers.Serializer):
    nombre           = serializers.CharField(required=False)
    apellido_paterno = serializers.CharField(required=False)
    apellido_materno = serializers.CharField(required=False)
    email           = serializers.EmailField(required=False)
    telefono        = serializers.CharField(required=False, allow_blank=True)
    licencia        = serializers.CharField(required=False, allow_blank=True)
    is_active       = serializers.BooleanField(required=False)

    def validate_nombre(self, value):
        return value.strip().title()

    def validate_apellido_paterno(self, value):
        return value.strip().title()

    def validate_apellido_materno(self, value):
        return value.strip().title()

    def validate_email(self, value):
        return value.strip().lower()

    def validate_telefono(self, value):
        if not value:
            return value
        limpio = re.sub(r'[\s\-\(\)]', '', value)
        if not re.match(r'^(\+56)?9\d{8}$', limpio):
            raise serializers.ValidationError(
                'Teléfono inválido. Use el formato +569 XXXXXXXX o 9XXXXXXXX.'
            )
        return limpio

    def validate_licencia(self, value):
        if not value: return value
        return value.strip().upper()

    def update(self, instance, validated_data):
        changed = False
        if any(k in validated_data for k in ('nombre', 'apellido_paterno', 'apellido_materno')):
            nombre     = validated_data.get('nombre',           instance.primer_nombre or '')
            ap_paterno = validated_data.get('apellido_paterno', instance.apellido_paterno or '')
            ap_materno = validated_data.get('apellido_materno', instance.apellido_materno or '')
            instance.set_nombre_partes(nombre, ap_paterno, ap_materno)
            changed = True
        if 'email' in validated_data:
            instance.email = validated_data['email']
            changed = True
            
        if 'telefono' in validated_data:
            if validated_data['telefono']:
                instance.set_telefono(validated_data['telefono'])
            else:
                instance.telefono_cifrado = None
            changed = True
            
        if 'licencia' in validated_data:
            if validated_data['licencia']:
                instance.set_licencia(validated_data['licencia'])
            else:
                instance.licencia_cifrada = None
            changed = True

        if 'is_active' in validated_data:
            instance.is_active = validated_data['is_active']
            changed = True

        if changed:
            instance.save()

        return instance


# ─────────────────────────────────────────
# Flota
# ─────────────────────────────────────────

class VehiculoResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Vehiculo
        fields = ['id', 'patente', 'marca', 'modelo', 'anio',
                  'tipo_combustible', 'km_actuales', 'activo']


class FlotaSerializer(serializers.ModelSerializer):
    vehiculos       = VehiculoResumenSerializer(many=True, read_only=True)
    total_vehiculos = serializers.SerializerMethodField()
    empresa_nombre  = serializers.SerializerMethodField()

    class Meta:
        model  = Flota
        fields = ['id', 'nombre', 'empresa_nombre', 'total_vehiculos', 'vehiculos']
        read_only_fields = ['id']

    def get_total_vehiculos(self, obj):
        return obj.vehiculos.filter(activo=True).count()

    def get_empresa_nombre(self, obj):
        try:
            return obj.empresa.nombre
        except Exception:
            return None

    def validate_nombre(self, value):
        value   = value.strip().title()
        empresa = self.context.get('empresa')
        qs      = Flota.objects.filter(nombre__iexact=value, empresa=empresa)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe una flota con ese nombre en esta empresa.")
        return value


# ─────────────────────────────────────────
# Vehículo
# ─────────────────────────────────────────

class VehiculoSerializer(serializers.ModelSerializer):
    flota_nombre       = serializers.SerializerMethodField()
    conductor_asignado = serializers.SerializerMethodField()

    class Meta:
        model  = Vehiculo
        fields = ['id', 'flota', 'flota_nombre', 'patente', 'marca', 'modelo',
                  'anio', 'tipo_combustible', 'km_actuales',
                  'conductor_asignado', 'activo']
        read_only_fields = ['id']

    def get_flota_nombre(self, obj):
        return obj.flota.nombre

    def get_conductor_asignado(self, obj):
        asig = obj.asignaciones.filter(activo=True).select_related('conductor').first()
        if asig and asig.conductor_id:
            c = asig.conductor
            return {'id': c.id, 'nombre': c.nombre or c.email}
        return None

    def validate_patente(self, value):
        valor = value.upper().replace(' ', '').replace('-', '')
        # Formato nuevo: LLLLNN (4 letras + 2 números), formato antiguo: LLNNNN (2 letras + 4 números)
        if not re.match(r'^[A-Z]{4}\d{2}$|^[A-Z]{2}\d{4}$', valor):
            raise serializers.ValidationError(
                'Formato de patente inválido. Use el formato LLLLNN (ej: ABCD12) o LLNNNN (ej: AB1234).'
            )
        qs = Vehiculo.objects.filter(patente_hash=Vehiculo.hash_patente(valor))
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un vehículo con esa patente.")
        return valor

    def validate_marca(self, value):
        if not value: return value
        return value.strip().title()

    def validate_modelo(self, value):
        if not value: return value
        return value.strip().title()

    def validate_flota(self, value):
        empresa = self.context.get('empresa')
        if empresa and value.empresa_id != empresa.id:
            raise serializers.ValidationError("La flota no pertenece a tu empresa.")
        return value


# ─────────────────────────────────────────
# Configuración del Sistema
# ─────────────────────────────────────────

class PlanSuscripcionSerializer(serializers.ModelSerializer):
    nombre_display   = serializers.CharField(source='get_nombre_display', read_only=True)
    precio_display   = serializers.SerializerMethodField()
    empresas_activas = serializers.SerializerMethodField()

    class Meta:
        model  = PlanSuscripcion
        fields = [
            'id', 'nombre', 'nombre_display', 'descripcion',
            'precio_mensual', 'precio_display',
            'max_flotas', 'max_vehiculos', 'max_conductores', 'max_usuarios',
            'modulos', 'activo', 'orden', 'empresas_activas',
            'created_at', 'updated_at',
        ]

    def get_precio_display(self, obj):
        if obj.precio_mensual:
            return f"${int(obj.precio_mensual):,}/mes".replace(',', '.')
        return "A convenir"

    def get_empresas_activas(self, obj):
        return obj.empresas.filter(estado='activa').count()


class CambioPlanSerializer(serializers.ModelSerializer):
    empresa_nombre      = serializers.CharField(source='empresa.nombre', read_only=True)
    plan_antes_nombre   = serializers.SerializerMethodField()
    plan_despues_nombre = serializers.SerializerMethodField()
    cambiado_por_email  = serializers.SerializerMethodField()

    class Meta:
        model  = CambioPlan
        fields = [
            'id', 'empresa', 'empresa_nombre',
            'plan_antes', 'plan_antes_nombre',
            'plan_despues', 'plan_despues_nombre',
            'cambiado_por', 'cambiado_por_email',
            'motivo', 'fecha',
        ]

    def get_plan_antes_nombre(self, obj):
        return obj.plan_antes.get_nombre_display() if obj.plan_antes else None

    def get_plan_despues_nombre(self, obj):
        return obj.plan_despues.get_nombre_display() if obj.plan_despues else None

    def get_cambiado_por_email(self, obj):
        return obj.cambiado_por.email if obj.cambiado_por else None


def _generar_descripcion(accion, detalle, nombre):
    """Genera una oración en español que resume el evento del log."""
    u = nombre or 'Un usuario'
    d = detalle or {}

    def _veh():   return d.get('patente') or d.get('vehiculo_patente') or ''
    def _cond():  return d.get('conductor_nombre') or d.get('conductor') or d.get('email') or ''
    def _flota(): return d.get('nombre') or ''
    def _doc():   return d.get('tipo') or ''
    def _arch():  return f' "{d["nombre_archivo"]}"' if d.get('nombre_archivo') else ''
    def _entid(): return _veh() or _cond()

    desc = {
        # Seguridad
        'login_exitoso':          lambda: f'{u} inició sesión correctamente.',
        'login_fallido':          lambda: f'Intento de acceso fallido para {d.get("usuario_email", "usuario desconocido")}.',
        'cambio_password':        lambda: f'{u} restableció la contraseña de {d.get("usuario_email", "")}.',
        'cambio_rol':             lambda: f'{u} cambió el rol de {d.get("usuario_email", "")} de {d.get("rol_anterior", "?")} a {d.get("rol_nuevo", "?")}.',
        'cambio_permisos':        lambda: f'{u} modificó los permisos de {d.get("usuario_email", "")}.',
        'usuario_bloqueado':      lambda: f'{u} bloqueó la cuenta de {d.get("usuario_email", "")}.',
        'usuario_desbloqueado':   lambda: f'{u} desbloqueó la cuenta de {d.get("usuario_email", "")}.',
        # Usuarios
        'usuario_creado':         lambda: f'{u} creó el usuario {d.get("usuario_email", "")} con rol {d.get("rol", "")}.',
        'usuario_modificado':     lambda: f'{u} modificó los datos de {d.get("usuario_email", "")}.',
        'usuario_eliminado':      lambda: f'{u} eliminó al usuario {d.get("usuario_email", "")}.',
        'perfil_actualizado':     lambda: f'{u} actualizó su propio perfil.',
        # Empresa
        'empresa_creada':         lambda: f'{u} registró la empresa "{d.get("empresa_nombre", "")}".',
        'empresa_suspendida':     lambda: f'{u} suspendió la empresa "{d.get("empresa_nombre", "")}".',
        'empresa_eliminada':      lambda: f'{u} eliminó la empresa "{d.get("empresa_nombre", "")}".',
        # Planes
        'plan_creado':            lambda: f'{u} creó el plan "{d.get("plan", "")}".',
        'plan_editado':           lambda: f'{u} editó el plan "{d.get("plan", "")}".',
        'plan_eliminado':         lambda: f'{u} eliminó el plan "{d.get("plan", "")}".',
        'plan_asignado':          lambda: f'{u} asignó el plan "{d.get("plan_nuevo", d.get("plan",""))}" a {d.get("empresa", "")}.',
        'plan_permisos_editados': lambda: f'{u} editó los permisos del plan "{d.get("plan", "")}" ({d.get("total", 0)} permisos).',
        'solicitud_cambio_plan':  lambda: f'{u} solicitó cambiar al plan "{d.get("plan_solicitado", "")}".',
        # Flotas
        'flota_creada':           lambda: f'{u} creó la flota "{_flota()}".',
        'flota_editada':          lambda: f'{u} editó la flota "{_flota()}".',
        'flota_eliminada':        lambda: f'{u} eliminó la flota "{_flota()}".',
        # Vehículos
        'vehiculo_creado':        lambda: f'{u} registró el vehículo {_veh()} ({d.get("marca","")} {d.get("modelo","")}).',
        'vehiculo_editado':       lambda: f'{u} modificó el vehículo {_veh()}.',
        'vehiculo_desactivado':   lambda: f'{u} desactivó el vehículo {_veh()}.',
        # Conductores
        'conductor_creado':       lambda: f'{u} registró al conductor {d.get("nombre", d.get("email", ""))}.',
        'conductor_editado':      lambda: f'{u} editó al conductor {d.get("email", "")}.',
        'conductor_desactivado':  lambda: f'{u} desactivó al conductor {d.get("email", "")}.',
        'conductor_asignado':     lambda: f'{u} asignó a {_cond()} al vehículo {_veh()}.',
        'conductor_desasignado':  lambda: f'{u} desasignó al conductor {_cond()}.',
        # Mantenciones
        'mantencion_creada':      lambda: f'{u} registró una mantención {d.get("tipo","")} para {_veh()}.',
        'mantencion_editada':     lambda: f'{u} editó una mantención {d.get("tipo","")} de {_veh()}.',
        'mantencion_eliminada':   lambda: f'{u} eliminó una mantención {d.get("tipo","")} de {_veh()}.',
        'mantencion_estado_cambiado': lambda: f'{u} cambió el estado de mantención de {_veh()} de "{d.get("estado_previo","")}" a "{d.get("estado_nuevo","")}".',
        # Documentos
        'documento_subido':       lambda: f'{u} subió {_doc()}{_arch()} para {_entid()}.',
        'documento_editado':      lambda: f'{u} editó el documento {_doc()}{_arch()} de {_entid()}.',
        'documento_eliminado':    lambda: f'{u} eliminó el documento {_doc()} de {_entid()}.',
        'documento_descargado':   lambda: f'{u} descargó {_doc()}{_arch()} de {_entid()}.',
        'documento_renovado':     lambda: f'{u} renovó {_doc()}{_arch()} para {_entid()} (ID anterior: {d.get("anterior_id","")}).',
        # Rutas
        'ruta_creada':            lambda: f'{u} creó la ruta "{d.get("nombre", "")}".',
        'ruta_eliminada':         lambda: f'{u} eliminó la ruta "{d.get("nombre", "")}".',
        'ruta_iniciada':          lambda: f'{u} inició la ruta #{d.get("ruta_id","")} (Km inicial: {d.get("km_inicio","")}).',
        'ruta_finalizada':        lambda: f'{u} finalizó la ruta #{d.get("ruta_id","")} ({d.get("km_reales","")} km recorridos).',
        'ruta_cancelada':         lambda: f'{u} canceló la ruta #{d.get("ruta_id","")}. Motivo: {d.get("motivo","")}.',
        # Gastos
        'gasto_creado':           lambda: f'{u} registró un gasto de ${d.get("monto","")} en {d.get("categoria","")}.',
        'gasto_editado':          lambda: f'{u} editó el gasto #{d.get("gasto_id","")}.',
        'gasto_eliminado':        lambda: f'{u} eliminó un gasto de ${d.get("monto","")} en {d.get("categoria","")}.',
        'presupuesto_creado':     lambda: f'{u} creó un presupuesto de ${d.get("monto","")} para {d.get("mes","")}/{d.get("anio","")}.',
        'presupuesto_editado':    lambda: f'{u} editó el presupuesto de {d.get("mes","")}/{d.get("anio","")} a ${d.get("monto","")}.',
        # Predictivo
        'crear_plan_mantenimiento':      lambda: f'{u} creó el plan de mantenimiento #{d.get("plan_id","")}.',
        'actualizar_plan_mantenimiento': lambda: f'{u} actualizó el plan de mantenimiento #{d.get("plan_id","")}.',
        'eliminar_plan_mantenimiento':   lambda: f'{u} eliminó el plan de mantenimiento #{d.get("plan_id","")}.',
        'atender_alerta_mantencion':     lambda: f'{u} atendió la alerta #{d.get("alerta_id","")}.',
        'asignar_plan_vehiculo':         lambda: f'{u} asignó el plan #{d.get("plan_id","")} al vehículo #{d.get("vehiculo_id","")}.',
        'desasignar_plan_vehiculo':      lambda: f'{u} eliminó la asignación #{d.get("asignacion_id","")} de plan.',
        'generar_alertas_predictivas':   lambda: f'{u} generó alertas predictivas.',
        # Pagos y suscripción
        'pago_iniciado':          lambda: f'{u} inició un pago del plan "{d.get("plan","")}" por ${d.get("monto","")}.',
        'pago_aprobado':          lambda: f'Pago aprobado del plan "{d.get("plan","")}" por ${d.get("monto","")}.',
        'pago_oneclick':          lambda: f'{u} pagó el plan "{d.get("plan","")}" por ${d.get("monto","")} con tarjeta guardada.',
        'pago_manual_registrado': lambda: f'{u} registró un pago manual de ${d.get("monto","")} ({d.get("metodo","")}) para "{d.get("empresa","")}".',
        'pago_error_crear':       lambda: f'Error al iniciar un pago con Transbank: {d.get("error","")}.',
        'pago_error':             lambda: f'Error al procesar un pago: {d.get("error","")}.',
        'oneclick_error':         lambda: f'Error al cobrar con tarjeta guardada: {d.get("error","")}.',
        'suscripcion_reactivada': lambda: f'{u} reactivó la suscripción de "{d.get("empresa","")}".',
        'gracia_extendida':       lambda: f'{u} extendió el período de gracia {d.get("dias_extra","")} días.',
        'tarjeta_eliminada':      lambda: f'{u} eliminó la tarjeta guardada de "{d.get("empresa","")}".',
        'terminos_actualizados':  lambda: f'{u} actualizó los términos y condiciones (v{d.get("version","")}).',
        # Email
        'email_config_guardada':  lambda: f'{u} actualizó la configuración de correo.',
        'email_test_enviado':     lambda: f'{u} envió un correo de prueba a {d.get("destino","")}.',
        # Solicitudes de conductores
        'solicitud_creada':       lambda: f'{u} creó una solicitud de {d.get("tipo","")}: "{d.get("titulo","")}".',
        'solicitud_aprobada':     lambda: f'{u} aprobó la solicitud de {d.get("tipo","")}: "{d.get("titulo","")}".',
        'solicitud_rechazada':    lambda: f'{u} rechazó la solicitud de {d.get("tipo","")}: "{d.get("titulo","")}".',
        # App del conductor
        'mantencion_iniciada_conductor':   lambda: f'{u} inició una mantención desde la app móvil.',
        'mantencion_completada_conductor': lambda: f'{u} completó una mantención desde la app móvil.',
        'checklist_completado':   lambda: f'{u} completó el checklist pre-viaje.',
        'checklist_push_fallido': lambda: 'Falló el envío de la notificación push del checklist.',
        # Cuenta / sistema
        'password_cambiado':      lambda: f'{u} cambió su contraseña.',
        'excepcion_no_manejada':  lambda: f'Error interno del servidor: {d.get("error","")}.',
    }

    fn = desc.get(accion)
    if not fn:
        return None
    try:
        return fn()
    except Exception:
        return None


class LogAuditoriaSerializer(serializers.ModelSerializer):
    usuario_email  = serializers.SerializerMethodField()
    usuario_nombre = serializers.SerializerMethodField()
    navegador      = serializers.SerializerMethodField()
    descripcion    = serializers.SerializerMethodField()

    class Meta:
        model  = LogAuditoria
        fields = [
            'id', 'tipo', 'accion', 'descripcion',
            'usuario_email', 'usuario_nombre',
            'detalle', 'ip', 'user_agent', 'navegador', 'so',
            'metodo', 'endpoint',
            'fecha',
        ]

    def get_usuario_email(self, obj):
        return obj.usuario.email if obj.usuario else None

    def get_usuario_nombre(self, obj):
        return obj.usuario.nombre if obj.usuario else None

    def get_navegador(self, obj):
        from .audit import _parse_navegador
        return _parse_navegador(obj.user_agent)

    def get_descripcion(self, obj):
        nombre = obj.usuario.nombre if obj.usuario else None
        return _generar_descripcion(obj.accion, obj.detalle, nombre)


# ─────────────────────────────────────────
# Mantenimiento Predictivo
# ─────────────────────────────────────────

from .models import (
    PlanMantenimiento, ReglaMantenimiento, VehiculoPlan,
    MantencionProgramada, AlertaMantencion
)

class ReglaMantenimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReglaMantenimiento
        fields = ['id', 'tipo', 'prioridad', 'intervalo_dias', 'umbral_alerta_dias', 
                  'canal', 'escalar_sin_respuesta', 'bloquear_despacho', 'costo_estimado']

class PlanMantenimientoSerializer(serializers.ModelSerializer):
    reglas = ReglaMantenimientoSerializer(many=True, read_only=False)

    class Meta:
        model = PlanMantenimiento
        fields = ['id', 'nombre', 'descripcion', 'activo', 'created_at', 'reglas']

    def create(self, validated_data):
        reglas_data = validated_data.pop('reglas', [])
        empresa = validated_data.pop('empresa', None) or self.context['request'].user.empresa
        plan = PlanMantenimiento.objects.create(empresa=empresa, **validated_data)
        for regla_data in reglas_data:
            ReglaMantenimiento.objects.create(plan=plan, **regla_data)
        return plan

    def update(self, instance, validated_data):
        reglas_data = validated_data.pop('reglas', [])
        instance.nombre = validated_data.get('nombre', instance.nombre)
        instance.descripcion = validated_data.get('descripcion', instance.descripcion)
        instance.activo = validated_data.get('activo', instance.activo)
        instance.save()

        # Update o create reglas
        # Por simplicidad, si se envían reglas se eliminan las actuales y se recrean (o se puede hacer más fino)
        instance.reglas.all().delete()
        for regla_data in reglas_data:
            ReglaMantenimiento.objects.create(plan=instance, **regla_data)
        return instance

class VehiculoPlanSerializer(serializers.ModelSerializer):
    vehiculo_patente = serializers.CharField(source='vehiculo.patente', read_only=True)
    plan_nombre = serializers.CharField(source='plan.nombre', read_only=True)

    class Meta:
        model = VehiculoPlan
        fields = ['id', 'vehiculo', 'vehiculo_patente', 'plan', 'plan_nombre', 'fecha_asignacion']

class MantencionProgramadaSerializer(serializers.ModelSerializer):
    vehiculo_patente = serializers.CharField(source='vehiculo.patente', read_only=True)
    regla_tipo = serializers.CharField(source='regla.tipo', read_only=True)

    class Meta:
        model = MantencionProgramada
        fields = ['id', 'vehiculo', 'vehiculo_patente', 'regla', 'regla_tipo', 
                  'fecha_ultima', 'fecha_siguiente', 'estado']

class AlertaMantencionSerializer(serializers.ModelSerializer):
    vehiculo_patente = serializers.CharField(source='mantencion_programada.vehiculo.patente', read_only=True)
    vehiculo_id      = serializers.IntegerField(source='mantencion_programada.vehiculo.id', read_only=True)
    tipo_mantencion  = serializers.CharField(source='mantencion_programada.regla.tipo', read_only=True)
    costo_estimado   = serializers.DecimalField(source='mantencion_programada.regla.costo_estimado', max_digits=12, decimal_places=2, read_only=True)
    fecha_vencimiento = serializers.DateField(source='mantencion_programada.fecha_siguiente', read_only=True)

    class Meta:
        model = AlertaMantencion
        fields = ['id', 'nivel', 'dias_restantes', 'pct_avance', 'enviada', 'atendida',
                  'fecha_creacion', 'fecha_atencion', 'vehiculo_patente', 'vehiculo_id',
                  'tipo_mantencion', 'costo_estimado', 'fecha_vencimiento']


# ─────────────────────────────────────────
# Notificaciones
# ─────────────────────────────────────────

from .models import Notificacion, NOTIF_PREFS_DEFAULT

class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notificacion
        fields = ['id', 'tipo', 'titulo', 'mensaje', 'leida', 'url_accion', 'extra', 'fecha']


class PreferenciasNotificacionSerializer(serializers.Serializer):
    inapp  = serializers.ListField(child=serializers.CharField(), default=list)
    email  = serializers.ListField(child=serializers.CharField(), default=list)
    push_token = serializers.CharField(default='', allow_blank=True)

    CATEGORIAS_VALIDAS = {'mantencion', 'documentos', 'seguridad', 'actividad'}

    def validate_inapp(self, value):
        return [v for v in value if v in self.CATEGORIAS_VALIDAS]

    def validate_email(self, value):
        return [v for v in value if v in self.CATEGORIAS_VALIDAS]


# ─────────────────────────────────────────
# Solicitudes de Conductores
# ─────────────────────────────────────────

class SolicitudConductorSerializer(serializers.ModelSerializer):
    conductor_nombre    = serializers.SerializerMethodField()
    conductor_iniciales = serializers.SerializerMethodField()
    vehiculo_patente    = serializers.CharField(source='vehiculo.patente', read_only=True, default=None)
    tipo_display        = serializers.CharField(source='get_tipo_display',     read_only=True)
    estado_display      = serializers.CharField(source='get_estado_display',   read_only=True)
    prioridad_display   = serializers.CharField(source='get_prioridad_display', read_only=True)
    respondido_por_nombre = serializers.SerializerMethodField()
    tiene_foto          = serializers.SerializerMethodField()
    foto_url            = serializers.SerializerMethodField()

    class Meta:
        model  = SolicitudConductor
        fields = [
            'id', 'tipo', 'tipo_display', 'titulo', 'descripcion',
            'prioridad', 'prioridad_display', 'estado', 'estado_display',
            'foto_url', 'tiene_foto', 'respuesta',
            'conductor', 'conductor_nombre', 'conductor_iniciales',
            'vehiculo', 'vehiculo_patente',
            'respondido_por', 'respondido_por_nombre', 'respondido_at',
            'created_at', 'updated_at', 'extra',
        ]

    def _nombre_usuario(self, usuario):
        if not usuario:
            return None
        try:
            return descifrar(usuario.nombre_cifrado)
        except Exception:
            return usuario.email

    def get_conductor_nombre(self, obj):
        return self._nombre_usuario(obj.conductor)

    def get_conductor_iniciales(self, obj):
        nombre = self.get_conductor_nombre(obj) or ''
        partes = nombre.split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[-1][0]}".upper()
        return nombre[:2].upper() if nombre else '?'

    def get_respondido_por_nombre(self, obj):
        return self._nombre_usuario(obj.respondido_por)

    def get_tiene_foto(self, obj):
        return bool(obj.foto)

    def get_foto_url(self, obj):
        if not obj.foto:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.foto.url)
        return obj.foto.url