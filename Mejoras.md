Vas a corregir y mejorar el módulo de peajes existente. No reescribir lo que funciona — solo aplicar los cambios específicos indicados.

---

## CAMBIO 1 — Modelo Peaje (models.py)

Reemplazar las CATEGORIAS existentes por:
```python
CATEGORIAS = [
    ('moto',        'Moto / Motoneta'),
    ('liviano',     'Auto / Camioneta / SUV'),
    ('liviano_rem', 'Auto/Camioneta con remolque'),
    ('pesado_2',    'Bus / Camión 2 ejes'),
    ('pesado_3',    'Camión 3+ ejes'),
]
```

Agregar dos campos nuevos al modelo Peaje después de longitud:
```python
km_ruta     = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
              help_text='Kilómetro en la ruta donde está el peaje')
radio_metros = models.PositiveIntegerField(default=800,
              help_text='Radio de detección personalizado en metros')
```

## CAMBIO 2 — Modelo Vehiculo (models.py)

Agregar campo después de tipo_combustible:
```python
categoria_peaje = models.CharField(
    max_length=20,
    choices=[
        ('moto',        'Moto / Motoneta'),
        ('liviano',     'Auto / Camioneta / SUV'),
        ('liviano_rem', 'Auto/Camioneta con remolque'),
        ('pesado_2',    'Bus / Camión 2 ejes'),
        ('pesado_3',    'Camión 3+ ejes'),
    ],
    default='liviano',
    help_text='Categoría de peaje del vehículo'
)
```

## CAMBIO 3 — Motor de detección (ruta_calculator.py)

Reemplazar detectar_peajes_en_ruta() por versión mejorada con radio variable:

```python
def detectar_peajes_en_ruta(polyline, categoria_vehiculo='liviano', radio_default_km=0.8):
    """
    Detecta peajes usando radio variable por peaje (radio_metros del modelo).
    Cada peaje tiene su propio radio de detección — los de autopistas urbanas
    necesitan radio menor (200m) para no detectar peajes de carriles paralelos,
    los rurales pueden tener radio mayor (1000m).
    """
    peajes_activos = Peaje.objects.filter(activo=True, categoria=categoria_vehiculo)
    detectados = []
    ids_vistos  = set()

    for peaje in peajes_activos:
        if peaje.id in ids_vistos:
            continue
        radio_km = (peaje.radio_metros / 1000) if peaje.radio_metros else radio_default_km
        for punto in polyline:
            dist = haversine_km(punto[0], punto[1], peaje.latitud, peaje.longitud)
            if dist <= radio_km:
                detectados.append(peaje)
                ids_vistos.add(peaje.id)
                break

    return detectados
```

Modificar calcular_costos() para usar categoria_peaje del vehículo:
- Recibir categoria_vehiculo como parámetro en lugar de asumir 'liviano'
- En la vista POST /rutas/ y POST /rutas/calcular/, pasar vehiculo.categoria_peaje

## CAMBIO 4 — seed_peajes.py (reemplazar completo)

Usar update_or_create. Para cada entrada crear UNA fila por categoría con la tarifa REAL de esa categoría — no multiplicadores, tarifas exactas.

Peajes y tarifas 2026 reales por categoría (moto, liviano, liviano_rem, pesado_2, pesado_3):

Ruta 68 — aplica a Zapata (-33.4456,-70.9789), Lo Prado (-33.4012,-71.1234), Casablanca (-33.3234,-71.4123):
normal: moto=800, liviano=2700, liviano_rem=3400, pesado_2=4800, pesado_3=8600
punta:  moto=1200, liviano=4000, liviano_rem=5000, pesado_2=7200, pesado_3=12900
radio_metros: 600 (carretera de montaña, radio más ajustado)

Ruta 5 Norte troncales — aplica a Las Vegas (-32.8234,-71.0123), Pichidangui (-32.1456,-71.5234):
normal: moto=1200, liviano=4050, liviano_rem=5100, pesado_2=7300, pesado_3=12950
punta: None (tarifa plana)
radio_metros: 1000

Ruta 5 Norte — Lampa (-33.2847,-70.9142):
normal: moto=750, liviano=2917, liviano_rem=3700, pesado_2=5250, pesado_3=9330
radio_metros: 800

Ruta 5 Norte Los Vilos–Serena — Socos (-30.7234,-71.4567), Serena (-29.9456,-71.2345):
normal: moto=1200, liviano=4050, liviano_rem=5100, pesado_2=7300, pesado_3=12950
radio_metros: 1000

Ruta 5 Sur troncal Stgo–Talca — Río Maipo (-33.6789,-70.8901), Angostura (-33.8901,-70.8456), Talca (-35.4234,-71.6234):
normal: moto=950, liviano=3800, liviano_rem=4800, pesado_2=6840, pesado_3=12160
radio_metros: 1000

Ruta 5 Sur lateral — mismo lat/lng que troncales pero con _lat field:
Río Maipo lateral (-33.6820,-70.8950): moto=230, liviano=900, liviano_rem=1140, pesado_2=1620, pesado_3=2880
radio_metros: 400 (lateral, radio chico para no confundir con troncal)

Ruta 5 Sur Talca–Chillán — Chillán (-36.6234,-72.1012):
normal: moto=900, liviano=3100, liviano_rem=3900, pesado_2=5580, pesado_3=9920
radio_metros: 1000

Ruta 5 Sur Chillán–Collipulli — Collipulli (-37.9456,-72.4345):
normal: moto=1000, liviano=3200, liviano_rem=4030, pesado_2=5760, pesado_3=10240
radio_metros: 1000

Ruta 5 Sur Temuco–Osorno — Temuco (-38.7345,-72.5901), Osorno (-40.5678,-73.1234):
normal: moto=950, liviano=3500, liviano_rem=4400, pesado_2=6300, pesado_3=11200
radio_metros: 1000

Ruta 57 Santiago–Los Andes — Chacabuco (-33.0234,-70.6789), Los Andes (-32.8345,-70.5901):
normal: moto=680, liviano=2700, liviano_rem=3400, pesado_2=4860, pesado_3=8640
radio_metros: 700

Ruta 78 — Melipilla A (-33.6890,-71.2134):
normal: moto=830, liviano=3300, liviano_rem=4160, pesado_2=5940, pesado_3=10560
radio_metros: 500

Ruta 78 — Melipilla B (-33.7234,-71.4012):
normal: moto=1490, liviano=5940, liviano_rem=7480, pesado_2=10690, pesado_3=19010
radio_metros: 500

Ruta 60 CH — Quillota (-32.8789,-71.2345):
normal: moto=1250, liviano=5000, liviano_rem=6300, pesado_2=9000, pesado_3=16000
punta:  moto=1750, liviano=7000, liviano_rem=8820, pesado_2=12600, pesado_3=22400
radio_metros: 700

## CAMBIO 5 — Formulario de vehículo (frontend)

En la vista de crear/editar vehículo, agregar campo select:
```vue
<div>
  <label class="label">Categoría de peaje</label>
  <select v-model="form.categoria_peaje" class="input">
    <option value="moto">Moto / Motoneta</option>
    <option value="liviano">Auto / Camioneta / SUV</option>
    <option value="liviano_rem">Auto/Camioneta con remolque</option>
    <option value="pesado_2">Bus / Camión 2 ejes</option>
    <option value="pesado_3">Camión 3+ ejes</option>
  </select>
  <p class="text-xs text-gray-400 mt-1">
    Define la tarifa de peaje que paga este vehículo
  </p>
</div>
```

## CAMBIO 6 — Vista de crear ruta (Rutas.vue)

En el paso 3 del modal (calculadora), mostrar la categoría de peaje del vehículo seleccionado:
Vehículo: PPU-4421 — Mercedes Actros · Diésel · Categoría: Bus/Camión 2 ejes
Así el usuario sabe qué tarifa se está aplicando antes de confirmar.

## CAMBIO 7 — Migración

```bash
python manage.py makemigrations --name mejorar_peajes_categorias
python manage.py migrate
python manage.py seed_peajes  # reemplaza datos anteriores
```

## ARCHIVOS A ENTREGAR

1. models_patch.py — solo los cambios en Peaje y Vehiculo
2. ruta_calculator_patch.py — solo detectar_peajes_en_ruta() y calcular_costos() modificados
3. seed_peajes.py — completo, reemplaza el anterior
4. vehiculo_form_patch.vue — solo el campo categoria_peaje a agregar en el form de vehículo
5. rutas_paso3_patch.vue — solo la línea de categoría a mostrar en el paso 3
6. MIGRACION.md — makemigrations → migrate → seed_peajes

Sin "# resto igual".