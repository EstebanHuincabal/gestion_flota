import re
import hashlib
from rest_framework import serializers
from .models import (
    Empresa, Usuario, Rol, Permiso, normalizar_rut, REGIONES_CHILE,
    Flota, Vehiculo, Asignacion, PlanSuscripcion, CambioPlan, LogAuditoria,
    Mantencion, Documento
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
    nombre   = serializers.CharField()
    rut      = serializers.CharField()
    email    = serializers.EmailField(required=False, allow_blank=True, default='')
    telefono = serializers.CharField(required=False, allow_blank=True, default='')
    direccion = serializers.CharField(required=False, allow_blank=True, default='')
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
    nombre     = serializers.SerializerMethodField()
    rut        = serializers.SerializerMethodField()
    empresa    = serializers.SerializerMethodField()
    empresa_id = serializers.SerializerMethodField()
    permisos   = serializers.SerializerMethodField()

    class Meta:
        model  = Usuario
        fields = ['id', 'nombre', 'rut', 'email', 'rol', 'empresa', 'empresa_id',
                  'is_active', 'is_blocked', 'permisos']

    def get_nombre(self, obj):
        return obj.nombre

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
    nombre_completo = serializers.CharField()
    rut             = serializers.CharField()
    email           = serializers.EmailField()
    password        = serializers.CharField(write_only=True)
    rol             = serializers.ChoiceField(choices=Rol.choices)
    empresa_id      = serializers.IntegerField(required=False, allow_null=True)
    permisos        = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )

    def validate_nombre_completo(self, value):
        return value.strip().title()

    def validate_email(self, value):
        value = value.strip().lower()
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese email.")
        return value

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
        empresa       = Empresa.objects.filter(pk=empresa_id).first() if empresa_id else None

        user = Usuario.objects.create_user(
            email           = validated_data['email'],
            rut             = validated_data['rut'],
            nombre_completo = validated_data['nombre_completo'],
            password        = password,
            rol             = rol,
            empresa         = empresa,
        )
        if codigos_permisos and rol == Rol.USUARIO:
            permisos = Permiso.objects.filter(codigo__in=codigos_permisos)
            user.permisos.set(permisos)
        return user


# ─────────────────────────────────────────
# Usuario — edición
# ─────────────────────────────────────────

class UsuarioEditarSerializer(serializers.Serializer):
    nombre_completo = serializers.CharField(required=False)
    email           = serializers.EmailField(required=False)
    rol             = serializers.ChoiceField(choices=Rol.choices, required=False)
    empresa_id      = serializers.IntegerField(required=False, allow_null=True)
    is_active       = serializers.BooleanField(required=False)
    permisos        = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )

    def validate_nombre_completo(self, value):
        return value.strip().title()

    def validate_email(self, value):
        qs = Usuario.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un usuario con ese email.")
        return value

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
        if 'nombre_completo' in validated_data:
            instance.set_nombre(validated_data['nombre_completo'])
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
    rut      = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()
    licencia = serializers.SerializerMethodField()
    vehiculo = serializers.SerializerMethodField()
    empresa_nombre = serializers.SerializerMethodField()

    class Meta:
        model  = Usuario
        fields = ['id', 'nombre', 'rut', 'email', 'telefono', 'licencia', 'vehiculo', 'is_active', 'empresa_nombre']

    def get_nombre(self, obj):   return obj.nombre
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
    vehiculo_id          = serializers.PrimaryKeyRelatedField(
                               queryset=Vehiculo.objects.all(),
                               source='vehiculo'
                           )
    vehiculo_patente     = serializers.CharField(source='vehiculo.patente', read_only=True)
    vehiculo_descripcion = serializers.SerializerMethodField()
    estado_display       = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Mantencion
        fields = [
            'id', 'vehiculo_id', 'vehiculo_patente', 'vehiculo_descripcion',
            'tipo_mantencion', 'descripcion', 'taller_proveedor', 'presupuesto',
            'fecha_programada', 'kilometraje_programado',
            'fecha_realizada', 'kilometraje_realizado',
            'estado', 'estado_display', 'costo',
        ]

    def get_vehiculo_descripcion(self, obj):
        return f"{obj.vehiculo.marca} {obj.vehiculo.modelo}".strip()

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
    nombre_completo = serializers.CharField()
    rut             = serializers.CharField()
    email           = serializers.EmailField()
    password        = serializers.CharField(write_only=True)
    telefono        = serializers.CharField(required=False, allow_blank=True)
    licencia        = serializers.CharField(required=False, allow_blank=True)
    
    # Opciones de asignación inicial
    vehiculo_id          = serializers.IntegerField(required=False, allow_null=True)
    crear_vehiculo       = serializers.BooleanField(default=False)
    vehiculo_patente     = serializers.CharField(required=False, allow_blank=True)
    vehiculo_marca       = serializers.CharField(required=False, allow_blank=True)
    vehiculo_modelo      = serializers.CharField(required=False, allow_blank=True)
    vehiculo_flota_id    = serializers.IntegerField(required=False, allow_null=True)
    vehiculo_flota_nuevo = serializers.CharField(required=False, allow_blank=True)

    def validate_nombre_completo(self, value):
        return value.strip().title()

    def validate_email(self, value):
        value = value.strip().lower()
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese email.")
        return value

    def validate_rut(self, value):
        rut_norm = normalizar_rut(value)
        if not _validar_dv_rut(rut_norm):
            raise serializers.ValidationError("El RUT ingresado no es válido.")
        rut_hash = hashlib.sha256(rut_norm.encode()).hexdigest()
        if Usuario.objects.filter(rut_hash=rut_hash).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese RUT.")
        return rut_norm

    def validate_telefono(self, value):
        if not value: return value
        value = value.replace(' ', '').replace('-', '')
        if not re.match(r'^\+?569\d{8}$', value):
            raise serializers.ValidationError("El teléfono debe tener el formato +569XXXXXXXX.")
        return value

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
            if Vehiculo.objects.filter(patente=patente).exists():
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
        empresa  = self.context['empresa']
        telefono = validated_data.pop('telefono', None)
        licencia = validated_data.pop('licencia', None)
        password = validated_data.pop('password')
        
        # Datos de vehículo/asignación
        vehiculo_id       = validated_data.pop('vehiculo_id', None)
        crear_vehiculo    = validated_data.pop('crear_vehiculo', False)
        v_patente         = validated_data.pop('vehiculo_patente', None)
        v_marca           = validated_data.pop('vehiculo_marca', '')
        v_modelo          = validated_data.pop('vehiculo_modelo', '')
        v_flota_id        = validated_data.pop('vehiculo_flota_id', None)
        v_flota_nuevo     = validated_data.pop('vehiculo_flota_nuevo', '').strip()

        user = Usuario.objects.create_user(
            email           = validated_data['email'],
            rut             = validated_data['rut'],
            nombre_completo = validated_data['nombre_completo'],
            password        = password,
            rol             = Rol.CONDUCTOR,
            empresa         = empresa,
        )
        
        if telefono:
            user.set_telefono(telefono)
        if licencia:
            user.set_licencia(licencia)
        if telefono or licencia:
            user.save()

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
    nombre_completo = serializers.CharField(required=False)
    email           = serializers.EmailField(required=False)
    telefono        = serializers.CharField(required=False, allow_blank=True)
    licencia        = serializers.CharField(required=False, allow_blank=True)

    def validate_nombre_completo(self, value):
        return value.strip().title()

    def validate_email(self, value):
        value = value.strip().lower()
        qs = Usuario.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un usuario con ese email.")
        return value

    def validate_telefono(self, value):
        if not value: return value
        value = value.replace(' ', '').replace('-', '')
        if not re.match(r'^\+?569\d{8}$', value):
            raise serializers.ValidationError("El teléfono debe tener el formato +569XXXXXXXX.")
        return value

    def validate_licencia(self, value):
        if not value: return value
        return value.strip().upper()

    def update(self, instance, validated_data):
        changed = False
        if 'nombre_completo' in validated_data:
            instance.set_nombre(validated_data['nombre_completo'])
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
    flota_nombre = serializers.SerializerMethodField()

    class Meta:
        model  = Vehiculo
        fields = ['id', 'flota', 'flota_nombre', 'patente', 'marca', 'modelo',
                  'anio', 'tipo_combustible', 'km_actuales', 'activo']
        read_only_fields = ['id']

    def get_flota_nombre(self, obj):
        return obj.flota.nombre

    def validate_patente(self, value):
        value = value.replace(' ', '').replace('-', '').upper().strip()
        qs    = Vehiculo.objects.filter(patente=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un vehículo con esa patente.")
        return value

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
            'precio_mensual', 'precio_anual', 'precio_display',
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


class LogAuditoriaSerializer(serializers.ModelSerializer):
    usuario_email  = serializers.SerializerMethodField()
    usuario_nombre = serializers.SerializerMethodField()

    class Meta:
        model  = LogAuditoria
        fields = ['id', 'tipo', 'accion', 'usuario_email', 'usuario_nombre', 'detalle', 'ip', 'fecha']

    def get_usuario_email(self, obj):
        return obj.usuario.email if obj.usuario else None

    def get_usuario_nombre(self, obj):
        return obj.usuario.nombre if obj.usuario else None


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