## LO QUE DEBES IMPLEMENTAR

Módulo de finanzas con DOS vistas completamente separadas según el rol:
- SUPERADMIN → dashboard de ingresos de la plataforma SaaS
- USUARIO → gestión de gastos operativos de su flota

---

## MODELOS NUEVOS (agregar en models.py)

### GastoOperativo
```python
class GastoOperativo(models.Model):
    CATEGORIAS = [
        ('combustible', 'Combustible'),
        ('mantencion',  'Mantención'),
        ('multa',       'Multa'),
        ('peaje',       'Peaje'),
        ('seguro',      'Seguro'),
        ('otro',        'Otro'),
    ]
    empresa        = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='gastos')
    vehiculo       = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True)
    conductor      = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='gastos_conductor')
    categoria      = models.CharField(max_length=20, choices=CATEGORIAS)
    descripcion    = models.CharField(max_length=300)
    monto          = models.DecimalField(max_digits=10, decimal_places=0)
    fecha          = models.DateField()
    comprobante    = models.FileField(upload_to='comprobantes/', null=True, blank=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='gastos_registrados')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha', '-created_at']
        verbose_name = 'Gasto operativo'
```

### PresupuestoMensual
```python
class PresupuestoMensual(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='presupuestos')
    anio    = models.PositiveSmallIntegerField()
    mes     = models.PositiveSmallIntegerField()
    monto   = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        unique_together = ('empresa', 'anio', 'mes')
        verbose_name = 'Presupuesto mensual'
```

---

## ENDPOINTS — todo en views.py salvo indicación

### Gastos operativos (USUARIO)
GET  /api/empresa/gastos/
Parámetros opcionales: mes, anio, categoria, vehiculo_id, conductor_id
Retorna lista de gastos + resumen:
```json
{
  "gastos": [...],
  "resumen": {
    "total": 4820000,
    "por_categoria": {
      "combustible": 2240000,
      "mantencion": 1680000,
      "multa": 580000,
      "peaje": 200000,
      "seguro": 120000
    },
    "por_vehiculo": [
      { "vehiculo_id": 1, "patente": "PPU-4421", "total": 890000 }
    ],
    "costo_por_km": 480,
    "presupuesto": { "monto": 5750000, "utilizado_pct": 84 }
  }
}
```

El costo_por_km se calcula dividiendo el total del mes por el total de km registrados en mantenciones del mismo período. Si no hay km registrados retorna null.
POST /api/empresa/gastos/
Body: { vehiculo_id, conductor_id (opcional), categoria, descripcion, monto, fecha }
Soportar subida de comprobante como multipart/form-data.
Registrar en audit con registrar_log().
GET  /api/empresa/gastos/:id/
PUT  /api/empresa/gastos/:id/
DELETE /api/empresa/gastos/:id/
Solo el registrado_por o un USUARIO admin de la empresa puede editar/eliminar.
GET  /api/empresa/gastos/exportar/
Parámetros: mes, anio, formato (csv | pdf)
Exportar todos los gastos del período con totales por categoría al final.
Para CSV usar el módulo csv de Python.
Para PDF usar reportlab (ya instalado en el proyecto si existe, sino indicar pip install reportlab).

### Presupuesto (USUARIO)
GET  /api/empresa/presupuesto/?mes=5&anio=2025
POST /api/empresa/presupuesto/
PUT  /api/empresa/presupuesto/:id/

### Dashboard SaaS (SUPERADMIN — agregar en views_planes.py)
GET /api/admin/finanzas/
Parámetros opcionales: periodo (últimos 12 meses por defecto)
Retorna:
```json
{
  "mrr": 3820000,
  "arr": 45840000,
  "churn_rate": 3.2,
  "ltv_promedio": 2840000,
  "empresas_activas": 35,
  "empresas_trial": 8,
  "ingresos_por_plan": [
    { "plan": "pro",        "empresas": 18, "mrr": 2682000, "pct": 70 },
    { "plan": "basico",     "empresas": 14, "mrr": 686000,  "pct": 18 },
    { "plan": "enterprise", "empresas": 3,  "mrr": 452000,  "pct": 12 }
  ],
  "movimientos_mes": {
    "nuevas_suscripciones": { "cantidad": 6, "mrr_ganado": 486000 },
    "upgrades":             { "cantidad": 3, "mrr_expansion": 300000 },
    "cancelaciones":        { "cantidad": 2, "mrr_perdido": 98000 },
    "pagos_fallidos":       { "cantidad": 4 }
  },
  "empresas_suscritas": [
    {
      "empresa_id": 1,
      "nombre": "...",
      "plan": "pro",
      "ciclo": "anual",
      "mrr": 124167,
      "proximo_cobro": "2026-01-15",
      "estado_suscripcion": "activa",
      "stripe_customer_id": "cus_..."
    }
  ]
}
```

Cálculos:
- MRR: suma de precio_mensual de todas las suscripciones activas. Para ciclo anual: precio_anual / 12.
- ARR: MRR × 12
- Churn rate: (cancelaciones del mes / empresas activas inicio del mes) × 100
- LTV: precio promedio mensual / churn_rate_mensual (como decimal)
- Los movimientos_mes filtran por fecha dentro del mes actual
GET /api/admin/finanzas/historico/
Parámetros: meses (int, default 12)
Retorna array de { mes, anio, mrr, nuevas, cancelaciones } para graficar evolución del MRR.

---

## URLS a agregar en urls.py

```python
path('api/empresa/gastos/',                    GastosListView.as_view()),
path('api/empresa/gastos/exportar/',           GastosExportarView.as_view()),
path('api/empresa/gastos/<int:gasto_id>/',     GastoDetailView.as_view()),
path('api/empresa/presupuesto/',               PresupuestoView.as_view()),
path('api/empresa/presupuesto/<int:pk>/',      PresupuestoDetailView.as_view()),
path('api/admin/finanzas/',                    FinanzasSaasView.as_view()),
path('api/admin/finanzas/historico/',          FinanzasHistoricoView.as_view()),
```

---

## FRONTEND — ARCHIVOS A CREAR

### src/web/finanzas/FinanzasEmpresa.vue
Vista completa para el rol USUARIO.

Tabs: Resumen | Combustible | Mantención | Multas y peajes | Por vehículo | Presupuesto

**Tab Resumen:**
- 4 KPI cards: gasto total del mes, costo por km, vehículo más costoso, presupuesto utilizado (con barra de progreso, naranja si >80%, rojo si >100%)
- Card "Distribución de gastos": lista de categorías con barra de progreso horizontal y monto + porcentaje. Íconos de Tabler por categoría.
- Card "Top 5 vehículos por gasto": tabla con patente, tipo, monto, barra visual de proporción. Click en fila navega al tab "Por vehículo" filtrando ese vehículo.
- Card "Últimos registros": tabla con fecha, vehículo, categoría (badge de color), descripción, conductor, monto, botón comprobante. Botón "Registrar gasto" abre el modal.

**Tab Combustible, Mantención, Multas y peajes:**
Misma estructura: filtros de período + vehículo, tabla de registros filtrada por categoría, totales al pie.

**Tab Por vehículo:**
- Selector de vehículo
- Breakdown de gastos del vehículo seleccionado por categoría
- Histórico de 6 meses (barras simples con div, sin librería de gráficos)
- Indicador de costo por km si hay datos

**Tab Presupuesto:**
- Input para definir el presupuesto del mes
- Barra de progreso de ejecución presupuestaria
- Comparativa: presupuesto vs gasto real mes a mes (últimos 6 meses, barras lado a lado con div, sin librería)

**Modal registrar/editar gasto:**
- Campos: vehículo (select con patentes), categoría (select), descripción, monto (input number formateado CLP), fecha, conductor (select opcional), comprobante (input file, acepta imagen y PDF)
- Validaciones: monto > 0, fecha no futura, categoría requerida, vehículo requerido
- Al guardar: POST multipart/form-data si hay comprobante, POST JSON si no
- Usa ConfirmModal para eliminar

**Filtros globales:**
- Selector de mes/año (default mes actual)
- Al cambiar recarga todos los datos del tab activo

### src/web/finanzas/FinanzasSuperAdmin.vue
Vista completa para el rol SUPERADMIN.

**KPI cards (fila superior):**
MRR | ARR | Churn rate | LTV promedio
Cada card muestra variación vs mes anterior con flecha y color (verde si mejoró, rojo si empeoró).

**Fila media (dos columnas):**
- Card "Ingresos por plan": barras horizontales con monto, cantidad de empresas y porcentaje por plan (Básico / Pro / Enterprise)
- Card "Movimientos del mes": 4 items con fondo semántico — nuevas suscripciones (verde), upgrades (azul), cancelaciones (rojo), pagos fallidos (naranja). Cada uno muestra cantidad y variación en MRR.

**Evolución MRR (últimos 12 meses):**
Gráfico de barras construido con divs (sin librería). Cada barra es un div con height proporcional al MRR máximo del período. Mostrar mes/año debajo de cada barra. Tooltip simple al hover mostrando MRR exacto.

**Tabla de empresas:**
Columnas: empresa, plan (badge), ciclo, MRR, próximo cobro, estado (badge), link externo a Stripe.
Estados con badge de color: activa (verde), trial (azul), gracia (naranja), suspendida (rojo), cancelada (gris).
Ordenable por MRR (click en cabecera).
Botón "Ver en Stripe" abre stripe_customer_id en nueva pestaña: https://dashboard.stripe.com/customers/{id}

**Selector de período:**
Dropdown: Últimos 3 meses / 6 meses / 12 meses. Al cambiar recarga el histórico.

### src/web/finanzas/index.js (o agregar directo al router)
Agregar en router/index.js:
```javascript
{
  path: '/empresa/finanzas',
  component: () => import('@/web/finanzas/FinanzasEmpresa.vue'),
  meta: { requiresAuth: true, roles: ['USUARIO'] }
},
{
  path: '/admin/finanzas',
  component: () => import('@/web/finanzas/FinanzasSuperAdmin.vue'),
  meta: { requiresAuth: true, roles: ['SUPERADMIN'] }
}
```

---

## NAVEGACIÓN — agregar en los sidebars existentes

En el sidebar del USUARIO (EmpresaLayout.vue o donde esté el nav de empresa):
Ítem: Finanzas
Ícono: ti-report-money
Ruta: /empresa/finanzas

En el sidebar del SUPERADMIN (Base.vue o donde esté el nav admin):
Ítem: Finanzas
Ícono: ti-chart-bar
Ruta: /admin/finanzas

---

## COMPORTAMIENTOS Y VALIDACIONES

- Solo USUARIO puede registrar gastos de su propia empresa. No puede ver ni registrar gastos de otras empresas.
- SUPERADMIN no puede registrar gastos de empresas (solo ve el dashboard SaaS).
- Los montos siempre en CLP enteros (sin decimales). Formato de display: $4.820.000 con punto como separador de miles.
- Fechas en formato dd/mm/yyyy en la UI, ISO en la API.
- El comprobante se guarda como archivo. En el listado mostrar ícono de clip si existe, check verde si fue revisado.
- Al eliminar un gasto con comprobante, eliminar también el archivo del filesystem.
- Si la empresa no tiene presupuesto definido para el mes, el KPI de "presupuesto utilizado" muestra "Sin presupuesto" con botón "Definir".
- registrar_log() en: crear gasto, editar gasto, eliminar gasto, crear/editar presupuesto.
- Manejo de errores: si un endpoint falla, mostrar showToast con el mensaje del backend. No dejar pantallas en blanco.
- Loading state en todos los fetch: mostrar spinner o skeleton mientras carga.
- El gráfico de evolución MRR en FinanzasSuperAdmin no usa ninguna librería externa — solo divs con height calculado en JS.

---

## ARCHIVOS A ENTREGAR

1. models_patch.py — clases GastoOperativo y PresupuestoMensual completas
2. views.py — solo las vistas nuevas de gastos y presupuesto (indicar exactamente dónde insertar)
3. views_planes.py — solo las vistas nuevas FinanzasSaasView y FinanzasHistoricoView (indicar dónde insertar)
4. urls_patch.py — solo las rutas nuevas
5. FinanzasEmpresa.vue — completo
6. FinanzasSuperAdmin.vue — completo
7. router_patch.js — solo las rutas a agregar
8. nav_patch.md — instrucciones exactas de qué línea agregar en qué archivo de navegación

Entrega cada archivo completo sin omitir código con comentarios como "// resto igual" o "# código existente".