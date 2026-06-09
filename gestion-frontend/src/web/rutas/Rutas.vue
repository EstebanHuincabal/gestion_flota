<template>
  <div class="min-h-screen bg-gray-50">
    <div class="p-6 max-w-screen-xl mx-auto">

      <!-- ── Header ── -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Rutas y trabajos</h1>
          <p class="text-sm text-gray-500 mt-0.5">Planificación y seguimiento de rutas vehiculares</p>
        </div>
        <div class="flex items-center gap-2">
          <button @click="abrirModalCarga"
            :disabled="esSuperadmin && !empresaActiva"
            :title="esSuperadmin && !empresaActiva ? 'Selecciona una empresa primero' : ''"
            class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-indigo-700 bg-white border border-indigo-200 rounded-lg hover:bg-indigo-50 transition disabled:opacity-50 disabled:cursor-not-allowed">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1M12 12V4m0 0L8 8m4-4l4 4"/>
            </svg>
            Carga masiva
          </button>
          <button @click="abrirModalCrear"
            :disabled="esSuperadmin && !empresaActiva"
            :title="esSuperadmin && !empresaActiva ? 'Selecciona una empresa primero' : ''"
            class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
            Nueva ruta
          </button>
        </div>
      </div>

      <!-- ── Selector empresa (solo SUPERADMIN) ── -->
      <div v-if="esSuperadmin" class="relative mb-5">
        <button
          @click="mostrarDropdownEmpresa = !mostrarDropdownEmpresa"
          :class="['flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition',
            empresaActiva ? 'bg-white border-gray-200 text-gray-700' : 'bg-amber-50 border-amber-300 text-amber-700']"
        >
          <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
          </svg>
          <span class="font-medium">{{ empresaActiva ? empresaActiva.nombre : 'Seleccionar empresa' }}</span>
          <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </button>

        <div v-if="mostrarDropdownEmpresa"
          class="absolute top-full left-0 mt-1 w-72 bg-white border border-gray-200 rounded-xl shadow-lg z-50 overflow-hidden">
          <div class="p-2 border-b border-gray-100">
            <input v-model="busquedaEmpresa" placeholder="Buscar empresa..."
              class="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-indigo-500"
              autofocus/>
          </div>
          <div class="max-h-60 overflow-y-auto">
            <div v-if="!empresasFiltradas.length" class="px-4 py-3 text-sm text-gray-400 text-center">Sin resultados</div>
            <button v-for="emp in empresasFiltradas" :key="emp.id"
              @click="seleccionarEmpresa(emp)"
              :class="['w-full flex items-center gap-2 px-4 py-2.5 text-sm text-left hover:bg-gray-50 transition',
                empresaActiva?.id === emp.id ? 'text-indigo-600 font-semibold' : 'text-gray-700']"
            >
              <span class="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
                {{ emp.nombre[0].toUpperCase() }}
              </span>
              {{ emp.nombre }}
              <svg v-if="empresaActiva?.id === emp.id" class="w-4 h-4 ml-auto text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- ── Sin empresa seleccionada (SUPERADMIN) ── -->
      <div v-if="sinEmpresa" class="bg-white rounded-xl border border-amber-200 p-12 text-center">
        <svg class="w-12 h-12 mx-auto mb-3 text-amber-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
        </svg>
        <p class="text-gray-500 text-sm">Selecciona una empresa para ver sus rutas</p>
      </div>

      <!-- ── KPI Cards ── -->
      <div v-if="!sinEmpresa" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-xl border border-gray-200 p-4">
          <p class="text-xs text-gray-500 mb-1">Rutas activas</p>
          <p class="text-2xl font-bold text-green-600">{{ resumen.activas }}</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-4">
          <p class="text-xs text-gray-500 mb-1">Pendientes hoy</p>
          <p class="text-2xl font-bold text-blue-600">{{ resumen.pendientes }}</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-4">
          <p class="text-xs text-gray-500 mb-1">Km este mes</p>
          <p class="text-2xl font-bold text-indigo-600">{{ resumen.km_mes.toLocaleString('es-CL') }}</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-4">
          <p class="text-xs text-gray-500 mb-1">Finalizadas este mes</p>
          <p class="text-2xl font-bold text-gray-800">{{ resumen.finalizadas_mes || 0 }}</p>
        </div>
      </div>

      <!-- ── Tabs ── -->
      <div v-if="!sinEmpresa" class="flex gap-1 mb-4 bg-white border border-gray-200 rounded-lg p-1 w-fit">
        <button v-for="tab in tabs" :key="tab.key"
          @click="tabActivo = tab.key"
          :class="['px-4 py-1.5 text-sm rounded-md transition font-medium',
            tabActivo === tab.key ? 'bg-indigo-600 text-white' : 'text-gray-600 hover:bg-gray-100']">
          {{ tab.label }}
        </button>
      </div>

      <!-- ── Tabla ── -->
      <div v-if="!sinEmpresa" class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div v-if="cargando" class="flex justify-center py-16">
          <div class="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        </div>

        <div v-else-if="rutasFiltradas.length === 0" class="text-center py-16 text-gray-400">
          <svg class="w-12 h-12 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
          </svg>
          <p class="text-sm">No hay rutas en esta categoría</p>
        </div>

        <table v-else class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
              <th v-if="esTodas" class="px-4 py-3 text-left font-semibold">Empresa</th>
              <th class="px-4 py-3 text-left font-semibold">Nombre / Ruta</th>
              <th class="px-4 py-3 text-left font-semibold">Tipo</th>
              <th class="px-4 py-3 text-left font-semibold">Conductor</th>
              <th class="px-4 py-3 text-left font-semibold">Vehículo</th>
              <th class="px-4 py-3 text-left font-semibold">Fecha</th>
              <th class="px-4 py-3 text-right font-semibold">Distancia / Duración</th>
              <th class="px-4 py-3 text-right font-semibold">Costo est.</th>
              <th class="px-4 py-3 text-center font-semibold">Estado</th>
              <th class="px-4 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="ruta in paginado" :key="ruta.id"
              @click="abrirPanel(ruta)"
              class="hover:bg-indigo-50/30 cursor-pointer transition group">
              <td v-if="esTodas" class="px-4 py-3 font-medium text-gray-700">{{ ruta.empresa_nombre || '—' }}</td>
              <td class="px-4 py-3">
                <p class="font-medium text-gray-900 group-hover:text-indigo-700">{{ ruta.nombre }}</p>
                <p class="text-xs text-gray-400">
                  {{ ruta.origen || '—' }}
                  <span v-if="ruta.destino"> → {{ ruta.destino }}</span>
                </p>
              </td>
              <td class="px-4 py-3">
                <span :class="['px-2 py-0.5 rounded-full text-xs font-medium',
                  ruta.tipo === 'carga' ? 'bg-amber-100 text-amber-700' : 'bg-purple-100 text-purple-700']">
                  {{ ruta.tipo === 'carga' ? 'Carga' : 'Personas' }}
                </span>
              </td>
              <td class="px-4 py-3 text-gray-600">{{ ruta.conductor || '—' }}</td>
              <td class="px-4 py-3 text-gray-600">{{ ruta.vehiculo || '—' }}</td>
              <td class="px-4 py-3 text-gray-500">
                {{ ruta.fecha_programada ? formatFecha(ruta.fecha_programada) : '—' }}
                <span v-if="ruta.hora_programada" class="ml-1 text-xs font-semibold text-indigo-500">{{ ruta.hora_programada }}</span>
              </td>
              <td class="px-4 py-3 text-right">
                <p class="font-medium text-gray-800">{{ ruta.distancia_km ? ruta.distancia_km.toLocaleString('es-CL') + ' km' : '—' }}</p>
                <p class="text-xs text-gray-400">{{ ruta.duracion_min ? formatDuracion(ruta.duracion_min) : '' }}</p>
              </td>
              <td class="px-4 py-3 text-right">
                <p class="font-medium text-gray-800">{{ combustibleRuta(ruta) ? '~' + formatCLP(combustibleRuta(ruta).total) : '—' }}</p>
                <p v-if="combustibleRuta(ruta)" class="text-xs text-gray-400">combustible</p>
              </td>
              <td class="px-4 py-3 text-center" @click.stop>
                <span :class="['px-2.5 py-1 rounded-full text-xs font-semibold', badgeEstado(ruta.estado)]">
                  <span v-if="ruta.estado === 'activo'" class="inline-block w-1.5 h-1.5 rounded-full bg-current mr-1 animate-pulse"></span>
                  {{ labelEstado(ruta.estado) }}
                </span>
                <span v-if="ruta.atrasada"
                      class="block mt-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-red-100 text-red-700"
                      :title="`Debió iniciar hace ${formatAtraso(ruta.atraso_min)}`">
                  ⚠ Atrasada · {{ formatAtraso(ruta.atraso_min) }}
                </span>
              </td>
              <td class="px-4 py-3 text-center" @click.stop>
                <div class="flex items-center justify-center gap-1">
                  <template v-if="ruta.estado === 'pendiente'">
                    <button @click="prepararIniciar(ruta)" title="Iniciar"
                      :disabled="iniciandoId === ruta.id"
                      class="p-1.5 text-green-600 hover:bg-green-50 rounded-lg transition disabled:opacity-40 disabled:cursor-not-allowed">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                      </svg>
                    </button>
                    <button @click="abrirModalEditar(ruta)" title="Editar"
                      class="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded-lg transition">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                      </svg>
                    </button>
                    <button @click="prepararCancelar(ruta)" title="Cancelar"
                      class="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </template>
                  <template v-else-if="!esTodas && ruta.estado === 'activo'">
                    <button @click="prepararFinalizar(ruta)" title="Finalizar"
                      class="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                      </svg>
                    </button>
                    <button @click="prepararCancelar(ruta)" title="Cancelar"
                      class="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </template>
                  <button @click="abrirPanel(ruta)" title="Ver detalle"
                    class="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg transition">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <PaginacionTabla
          :pagina="pagina"
          :total-paginas="totalPaginas"
          :total="total"
          :por-pagina="20"
          @update:pagina="irA"
        />
      </div>
    </div>

    <!-- ── Panel lateral ── -->
    <Transition name="panel">
      <div v-if="panelAbierto" class="fixed inset-0 z-30 flex justify-end">
        <div class="absolute inset-0 bg-black/20" @click="panelAbierto = false"></div>
        <div class="relative bg-white w-full max-w-3xl shadow-2xl flex flex-col overflow-hidden">
          <!-- Header panel -->
          <div class="flex items-start justify-between p-5 border-b border-gray-100">
            <div>
              <h2 class="text-lg font-bold text-gray-900">{{ rutaDetalle?.nombre }}</h2>
              <p class="text-sm text-gray-400 mt-0.5">
                {{ rutaDetalle?.origen }}
                <span v-if="rutaDetalle?.destino"> → {{ rutaDetalle.destino }}</span>
              </p>
            </div>
            <button @click="panelAbierto = false" class="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Tabs del panel -->
          <div class="flex border-b border-gray-100 px-5">
            <button v-for="t in ['detalle','mapa','historial']" :key="t"
              @click="cambiarTabPanel(t)"
              :class="['py-3 mr-5 text-sm font-medium border-b-2 transition capitalize',
                tabPanel === t ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-gray-500 hover:text-gray-700']">
              {{ t }}
            </button>
          </div>

          <!-- Contenido panel -->
          <div class="flex-1 overflow-y-auto p-5">

            <!-- Tab Detalle -->
            <div v-if="tabPanel === 'detalle'" class="space-y-4">
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Estado</p>
                  <span :class="['px-2.5 py-0.5 rounded-full text-xs font-semibold', badgeEstado(rutaDetalle?.estado)]">
                    {{ labelEstado(rutaDetalle?.estado) }}
                  </span>
                  <span v-if="rutaDetalle?.atrasada"
                        class="ml-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700">
                    ⚠ Atrasada · {{ formatAtraso(rutaDetalle.atraso_min) }}
                  </span>
                </div>
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Tipo</p>
                  <p class="font-medium text-gray-800">{{ rutaDetalle?.tipo === 'carga' ? 'Carga' : 'Personas' }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Conductor</p>
                  <p class="font-medium text-gray-800">{{ rutaDetalle?.conductor || '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Vehículo</p>
                  <p class="font-medium text-gray-800">{{ rutaDetalle?.vehiculo || '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Fecha programada</p>
                  <p class="font-medium text-gray-800">
                    {{ rutaDetalle?.fecha_programada ? formatFecha(rutaDetalle.fecha_programada) : '—' }}
                    <span v-if="rutaDetalle?.hora_programada" class="ml-1 text-indigo-600 font-semibold">
                      {{ rutaDetalle.hora_programada }}
                    </span>
                  </p>
                </div>
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Distancia</p>
                  <p class="font-medium text-gray-800">{{ rutaDetalle?.distancia_km ? rutaDetalle.distancia_km.toLocaleString('es-CL') + ' km' : '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-400 mb-0.5">Duración estimada</p>
                  <p class="font-medium text-gray-800">{{ rutaDetalle?.duracion_min ? formatDuracion(rutaDetalle.duracion_min) : '—' }}</p>
                </div>
                <div v-if="combustibleRuta(rutaDetalle)">
                  <p class="text-xs text-gray-400 mb-0.5">Combustible estimado</p>
                  <p class="font-medium text-gray-800">~{{ formatCLP(combustibleRuta(rutaDetalle).total) }}</p>
                </div>
                <div v-if="rutaDetalle?.km_reales">
                  <p class="text-xs text-gray-400 mb-0.5">Km recorridos</p>
                  <p class="font-medium text-gray-800">{{ rutaDetalle.km_reales.toLocaleString('es-CL') }} km</p>
                </div>
              </div>

              <!-- Paradas -->
              <div v-if="rutaDetalle?.paradas?.length" class="mt-4">
                <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Paradas</p>
                <ol class="relative border-l-2 border-gray-200 ml-2 space-y-3">
                  <li v-for="p in rutaDetalle.paradas" :key="p.id" class="ml-4">
                    <div :class="['absolute w-3 h-3 rounded-full -left-1.5 border-2 border-white',
                      p.tipo === 'origen' ? 'bg-green-500' : p.tipo === 'destino' ? 'bg-red-500' : 'bg-blue-400']"></div>
                    <p class="text-sm font-medium text-gray-800">{{ p.nombre }}</p>
                    <p class="text-xs text-gray-400">{{ p.direccion || p.tipo }}</p>
                  </li>
                </ol>
              </div>

            </div>

            <!-- Tab Mapa -->
            <div v-if="tabPanel === 'mapa'" style="height:420px">
              <MapaRuta
                map-id="panel-mapa"
                :paradas="rutaDetalle?.paradas || []"
                :polyline="rutaDetalle?.polyline || []"
              />
            </div>

            <!-- Tab Historial -->
            <div v-if="tabPanel === 'historial'" class="flex flex-col h-full">
              <!-- Lista de eventos -->
              <div v-if="cargandoEventos" class="flex justify-center py-8">
                <div class="w-6 h-6 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
              </div>

              <div v-else class="flex-1 space-y-3 mb-4">
                <div v-if="!eventos.length" class="text-center py-8 text-gray-400 text-sm">
                  No hay eventos aún.
                </div>
                <div v-for="e in eventos" :key="e.id"
                  class="flex gap-3 items-start">
                  <!-- Icono -->
                  <div :class="['flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white',
                    e.tipo === 'auto' ? 'bg-indigo-500' : 'bg-green-500']">
                    <!-- auto: engranaje -->
                    <svg v-if="e.tipo === 'auto'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                    </svg>
                    <!-- comentario: burbuja -->
                    <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
                    </svg>
                  </div>
                  <!-- Contenido -->
                  <div class="flex-1 min-w-0">
                    <p class="text-sm text-gray-800">{{ e.texto }}</p>
                    <p class="text-xs text-gray-400 mt-0.5">
                      {{ e.autor || 'Sistema' }} · {{ formatTimestamp(e.created_at) }}
                    </p>
                  </div>
                </div>
              </div>

              <!-- Input nuevo comentario -->
              <div class="border-t border-gray-100 pt-4">
                <div class="flex gap-2">
                  <input v-model="nuevoComentario" type="text" placeholder="Agregar comentario..."
                    class="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                    @keydown.enter="enviarComentario"/>
                  <button @click="enviarComentario" :disabled="!nuevoComentario.trim() || enviandoComentario"
                    class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50">
                    Enviar
                  </button>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Modal crear / editar (3 pasos) ── -->
    <Transition name="modal">
      <div v-if="modalCrear" class="fixed inset-0 z-40 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40" @click="cerrarModal"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col">

          <!-- Header modal -->
          <div class="flex items-center justify-between p-5 border-b border-gray-100">
            <div>
              <h3 class="text-lg font-bold text-gray-900">{{ modoEdicion ? 'Editar ruta' : 'Nueva ruta' }}</h3>
              <p class="text-xs text-gray-400 mt-0.5">Paso {{ paso }} de 3</p>
            </div>
            <button @click="cerrarModal" class="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Indicador de pasos -->
          <div class="flex px-5 pt-4 gap-2">
            <div v-for="n in 3" :key="n"
              :class="['h-1 flex-1 rounded-full transition-all', n <= paso ? 'bg-indigo-600' : 'bg-gray-200']"></div>
          </div>

          <!-- Contenido del paso -->
          <div class="flex-1 overflow-y-auto p-5">

            <!-- Paso 1 — Datos generales -->
            <div v-if="paso === 1" class="space-y-4">
              <!-- Empresa (solo SUPERADMIN en modo "Todas", al crear) -->
              <div v-if="esTodas && !modoEdicion">
                <label class="block text-xs font-semibold text-gray-600 mb-1">Empresa *</label>
                <select v-model="empresaIdForm"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
                  <option value="" disabled>— Seleccionar empresa —</option>
                  <option v-for="e in empresas.filter(e => e.id !== '__todas__')" :key="e.id" :value="e.id">{{ e.nombre }}</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-2">Tipo de ruta</label>
                <div class="grid grid-cols-2 gap-3">
                  <label v-for="opt in [{v:'carga',l:'Carga'},{v:'personas',l:'Personas'}]" :key="opt.v"
                    :class="['flex items-center gap-2.5 p-3 border-2 rounded-xl cursor-pointer transition',
                      form.tipo === opt.v ? 'border-indigo-600 bg-indigo-50' : 'border-gray-200 hover:border-gray-300']">
                    <input type="radio" :value="opt.v" v-model="form.tipo" class="sr-only">
                    <span class="text-sm font-medium text-gray-800">{{ opt.l }}</span>
                  </label>
                </div>
              </div>
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1">Nombre de la ruta *</label>
                <input v-model="form.nombre" type="text" placeholder="Ej: Santiago → Valparaíso"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-1">Conductor</label>
                  <select v-model="form.conductor_id" @change="onConductorChange"
                    :disabled="esTodas && !modoEdicion && !empresaIdForm"
                    :class="['w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 transition disabled:opacity-50 disabled:cursor-not-allowed',
                      autoFillConductor ? 'border-indigo-400 bg-indigo-50' : 'border-gray-200']">
                    <option :value="null">{{ esTodas && !modoEdicion && !empresaIdForm ? 'Selecciona empresa primero' : 'Sin asignar' }}</option>
                    <option v-for="c in conductores" :key="c.id" :value="c.id">{{ c.nombre }}</option>
                  </select>
                  <p v-if="autoFillConductor" class="mt-1 text-xs text-indigo-600 flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                    Autocompletado por vehículo asignado
                  </p>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-1">Vehículo</label>
                  <select v-model="form.vehiculo_id" @change="onVehiculoChange"
                    :disabled="esTodas && !modoEdicion && !empresaIdForm"
                    :class="['w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 transition disabled:opacity-50 disabled:cursor-not-allowed',
                      autoFillVehiculo ? 'border-indigo-400 bg-indigo-50' : 'border-gray-200']">
                    <option :value="null">{{ esTodas && !modoEdicion && !empresaIdForm ? 'Selecciona empresa primero' : 'Sin asignar' }}</option>
                    <option v-for="v in vehiculos" :key="v.id" :value="v.id">{{ v.patente }} — {{ v.marca }} {{ v.modelo }}</option>
                  </select>
                  <p v-if="autoFillVehiculo" class="mt-1 text-xs text-indigo-600 flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                    Autocompletado por conductor asignado
                  </p>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-1">
                    Fecha programada <span class="text-red-500">*</span>
                  </label>
                  <input v-model="form.fecha_programada" type="date"
                    @change="validacionResult = null; advertenciasAceptadas = false"
                    class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-600 mb-1">
                    Hora programada <span class="text-red-500">*</span>
                  </label>
                  <input v-model="form.hora_programada" type="time"
                    @change="validacionResult = null; advertenciasAceptadas = false"
                    class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
                </div>
              </div>
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1">Notas</label>
                <textarea v-model="form.notas" rows="2" placeholder="Instrucciones, observaciones..."
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"></textarea>
              </div>

              <!-- ── Panel de validación pre-vuelo ─────────────────────── -->
              <transition name="fade-slide">
              <div v-if="validacionResult" class="mt-1">

                <!-- Errores bloqueantes -->
                <div v-if="validacionResult.errores?.length"
                  class="rounded-xl border border-red-300 bg-red-50 overflow-hidden">
                  <div class="flex items-center gap-2.5 px-4 py-3 bg-red-100 border-b border-red-200">
                    <div class="w-7 h-7 rounded-full bg-red-500 flex items-center justify-center shrink-0">
                      <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </div>
                    <p class="text-sm font-bold text-red-800">No se puede programar esta ruta</p>
                  </div>
                  <ul class="px-4 py-3 space-y-2">
                    <li v-for="e in validacionResult.errores" :key="e.codigo"
                      class="flex items-start gap-2 text-sm text-red-700">
                      <svg class="w-4 h-4 text-red-400 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd"/>
                      </svg>
                      <span>{{ e.mensaje }}</span>
                    </li>
                  </ul>
                </div>

                <!-- Advertencias (solo si no hay errores) -->
                <div v-if="validacionResult.advertencias?.length && !validacionResult.errores?.length"
                  class="rounded-xl border overflow-hidden"
                  :class="advertenciasAceptadas ? 'border-green-300 bg-green-50' : 'border-amber-300 bg-amber-50'">

                  <!-- Header -->
                  <div class="flex items-center gap-2.5 px-4 py-3 border-b"
                    :class="advertenciasAceptadas ? 'bg-green-100 border-green-200' : 'bg-amber-100 border-amber-200'">
                    <div class="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                      :class="advertenciasAceptadas ? 'bg-green-500' : 'bg-amber-400'">
                      <svg v-if="advertenciasAceptadas" class="w-4 h-4 text-white" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                      </svg>
                      <svg v-else class="w-4 h-4 text-white" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                      </svg>
                    </div>
                    <p class="text-sm font-bold"
                      :class="advertenciasAceptadas ? 'text-green-800' : 'text-amber-800'">
                      {{ advertenciasAceptadas ? 'Confirmado — puedes continuar' : `${validacionResult.advertencias.length} advertencia${validacionResult.advertencias.length > 1 ? 's' : ''} detectada${validacionResult.advertencias.length > 1 ? 's' : ''}` }}
                    </p>
                  </div>

                  <!-- Lista de advertencias -->
                  <ul class="px-4 py-3 space-y-2">
                    <li v-for="a in validacionResult.advertencias" :key="a.codigo"
                      class="flex items-start gap-2 text-sm"
                      :class="advertenciasAceptadas ? 'text-green-700' : 'text-amber-700'">
                      <svg class="w-4 h-4 shrink-0 mt-0.5" :class="advertenciasAceptadas ? 'text-green-400' : 'text-amber-400'" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/>
                      </svg>
                      <span>{{ a.mensaje }}</span>
                    </li>
                  </ul>

                  <!-- Botón "Programar de todas formas" -->
                  <div v-if="!advertenciasAceptadas" class="px-4 pb-4">
                    <button
                      @click="advertenciasAceptadas = true"
                      class="w-full py-2.5 text-sm font-semibold text-white bg-amber-500 hover:bg-amber-600 rounded-lg transition flex items-center justify-center gap-2">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                      </svg>
                      Programar de todas formas
                    </button>
                  </div>
                </div>

              </div>
              </transition>
            </div>

            <!-- Paso 2 — Paradas -->
            <div v-if="paso === 2" class="space-y-3">
              <p class="text-xs text-gray-500 mb-1">Ingresa el origen, destino y las paradas intermedias.</p>

              <div v-for="(parada, idx) in form.paradas" :key="idx"
                @click="paradaActiva = idx"
                :class="['border rounded-xl p-3 relative cursor-pointer transition',
                  paradaActiva === idx ? 'border-indigo-400 ring-2 ring-indigo-200 bg-indigo-50/30' : 'border-gray-200 hover:border-indigo-200']">
                <div class="flex items-center justify-between mb-2">
                  <div class="flex items-center gap-2">
                    <span :class="['text-xs font-semibold px-2 py-0.5 rounded-full',
                      parada.tipo === 'origen' ? 'bg-green-100 text-green-700' :
                      parada.tipo === 'destino' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700']">
                      {{ parada.tipo === 'origen' ? 'Origen' : parada.tipo === 'destino' ? 'Destino' : `Parada ${idx}` }}
                    </span>
                    <span v-if="paradaActiva === idx" class="text-xs text-indigo-600 font-medium">📍 clic en el mapa para fijar</span>
                  </div>
                  <button v-if="parada.tipo === 'parada'" @click.stop="quitarParada(idx)"
                    class="p-1 text-red-400 hover:bg-red-50 rounded-lg transition">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
                <!-- Buscador de dirección -->
                <div class="relative">
                  <input :value="parada.nombre || parada.direccion"
                    @input="e => buscarDireccion(e.target.value, idx)"
                    type="text" :placeholder="parada.tipo === 'origen' ? 'Buscar dirección de origen...' : parada.tipo === 'destino' ? 'Buscar dirección de destino...' : 'Buscar dirección de parada...'"
                    class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
                  <div v-if="geoSugerencias[idx]?.length"
                    class="absolute top-full mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-48 overflow-y-auto">
                    <button v-for="(sug, si) in geoSugerencias[idx]" :key="si"
                      @click="seleccionarDireccion(sug, idx)"
                      class="w-full text-left px-3 py-2 text-xs text-gray-700 hover:bg-indigo-50 border-b border-gray-50 last:border-0">
                      {{ sug.display_name }}
                    </button>
                  </div>
                </div>

                <!-- Coordenadas manuales (toggle) -->
                <button type="button" @click="coordsAbiertas[idx] = !coordsAbiertas[idx]"
                  class="mt-1.5 text-xs text-gray-400 hover:text-indigo-500 transition">
                  {{ coordsAbiertas[idx] ? '− Ocultar coordenadas' : '± Coordenadas manuales' }}
                </button>
                <div v-if="coordsAbiertas[idx]" class="grid grid-cols-2 gap-2 mt-1">
                  <input v-model.number="parada.latitud" @change="validarCoordParada(idx)" type="number" step="any"
                    placeholder="Latitud (-33.44)"
                    class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-400">
                  <input v-model.number="parada.longitud" @change="validarCoordParada(idx)" type="number" step="any"
                    placeholder="Longitud (-70.66)"
                    class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-400">
                </div>
                <p v-if="coordsError[idx]" class="mt-1 text-xs text-red-500">{{ coordsError[idx] }}</p>

                <div v-if="parada.latitud && parada.longitud" class="mt-1 text-xs text-green-600">
                  ✓ {{ Number(parada.latitud).toFixed(4) }}, {{ Number(parada.longitud).toFixed(4) }}
                </div>
              </div>

              <button @click="agregarParada"
                class="w-full border-2 border-dashed border-gray-200 text-gray-400 rounded-xl py-2.5 text-sm hover:border-indigo-300 hover:text-indigo-500 transition">
                + Agregar parada intermedia
              </button>

              <!-- Mapa único con todas las paradas -->
              <p class="text-xs text-gray-400 mt-1">📍 Selecciona una parada arriba y haz clic en el mapa para fijar su ubicación.</p>
              <div style="height:260px" class="rounded-xl overflow-hidden border border-gray-200 mt-1">
                <MapaRuta
                  ref="mapaParadasRef"
                  map-id="paradas-mapa"
                  :paradas="form.paradas.filter(p => p.latitud && p.longitud)"
                  :polyline="[]"
                  :buscador="true"
                  :seleccionable="true"
                  @map-click="onMapaClick"
                />
              </div>
            </div>

            <!-- Paso 3 — Calcular y confirmar -->
            <div v-if="paso === 3" class="space-y-4">
              <div v-if="calculando" class="flex flex-col items-center justify-center py-10 gap-3 text-gray-400">
                <div class="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                <p class="text-sm">Calculando ruta con OSRM...</p>
              </div>

              <div v-else-if="calculoResult">
                <!-- Mapa del cálculo -->
                <div style="height:250px" class="rounded-xl overflow-hidden border border-gray-200 mb-3">
                  <MapaRuta
                    map-id="calc-mapa"
                    :paradas="form.paradas.filter(p => p.latitud)"
                    :polyline="calculoResult.polyline || []"
                  />
                </div>

                <!-- Alerta OSRM falla -->
                <div v-if="calculoResult.aviso" class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-700 mb-3">
                  ⚠️ {{ calculoResult.aviso }}
                </div>

                <!-- Datos calculados -->
                <div class="grid grid-cols-2 gap-3">
                  <div class="bg-gray-50 rounded-lg p-3 text-sm">
                    <p class="text-xs text-gray-400">Distancia</p>
                    <p class="font-bold text-gray-800">{{ calculoResult.distancia_km ? calculoResult.distancia_km.toLocaleString('es-CL') + ' km' : '—' }}</p>
                  </div>
                  <div class="bg-gray-50 rounded-lg p-3 text-sm">
                    <p class="text-xs text-gray-400">Duración estimada</p>
                    <p class="font-bold text-gray-800">{{ calculoResult.duracion_min ? formatDuracion(calculoResult.duracion_min) : '—' }}</p>
                  </div>
                </div>

                <!-- Combustible estimado -->
                <div class="mt-3 bg-indigo-50/60 border border-indigo-100 rounded-lg p-3 text-sm">
                  <div class="flex items-center justify-between">
                    <span class="text-gray-700 font-medium">⛽ Combustible estimado</span>
                    <span class="font-bold text-gray-900">{{ combustibleCalc ? formatCLP(combustibleCalc.total) : 'Sin datos' }}</span>
                  </div>
                  <p v-if="combustibleCalc" class="text-xs text-gray-500 mt-0.5">
                    {{ combustibleCalc.litros }} L × {{ formatCLP(combustibleCalc.precioLitro) }}/L
                    ({{ labelCombustible(combustibleCalc.combustible) }} · {{ combustibleCalc.consumo_l100 }} L/100km estimado)
                  </p>
                  <p v-else class="text-xs text-gray-400 mt-0.5">Calcula la distancia para estimar el combustible.</p>
                </div>
              </div>

              <div v-else class="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-700">
                No se pudo conectar con el servicio de rutas. Puede crear la ruta de todas formas sin datos de distancia.
              </div>
            </div>
          </div>

          <!-- Footer modal -->
          <div class="border-t border-gray-100">
            <div v-if="errorModal"
                 class="flex items-start gap-2 px-4 py-3 bg-red-50 border-b border-red-100">
              <svg class="w-4 h-4 text-red-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
              <p class="text-xs text-red-700 whitespace-pre-line leading-relaxed">{{ errorModal }}</p>
            </div>

            <div class="flex items-center justify-between p-4">
              <button v-if="paso > 1" @click="paso--; errorModal = ''"
                class="px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition">
                Anterior
              </button>
              <div v-else></div>
              <div class="flex gap-2">
                <button @click="cerrarModal" class="px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded-lg transition">
                  Cancelar
                </button>
                <button v-if="paso < 3" @click="siguientePaso"
                  :disabled="(paso === 1 && !form.nombre.trim()) || validando || (validacionResult?.errores?.length > 0)"
                  class="px-5 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5">
                  <svg v-if="validando" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  {{ validando ? 'Verificando...' : 'Siguiente' }}
                </button>
                <button v-else @click="guardarRuta" :disabled="guardando"
                  class="px-5 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50">
                  {{ guardando ? 'Guardando...' : (modoEdicion ? 'Guardar cambios' : 'Crear ruta') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Modal Finalizar ── -->
    <Transition name="modal">
      <div v-if="modalFinalizar" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40" @click="modalFinalizar = false"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
          <h3 class="text-lg font-bold text-gray-900 mb-1">Finalizar ruta</h3>
          <p class="text-sm text-gray-500 mb-4">{{ rutaAccion?.nombre }}</p>
          <div class="space-y-3">
            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1">
                Km finales del vehículo *
              </label>
              <input v-model.number="finalizarForm.km_fin" type="number" min="0"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-4">
            <button @click="modalFinalizar = false" class="px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded-lg">Cancelar</button>
            <button @click="confirmarFinalizar" :disabled="finalizando || (!finalizarForm.km_fin && finalizarForm.km_fin !== 0)"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed">
              {{ finalizando ? 'Finalizando...' : 'Finalizar' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Modal Cancelar ── -->
    <Transition name="modal">
      <div v-if="modalCancelar" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40" @click="modalCancelar = false"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
          <h3 class="text-lg font-bold text-gray-900 mb-1">Cancelar ruta</h3>
          <p class="text-sm text-gray-500 mb-4">{{ rutaAccion?.nombre }}</p>
          <label class="block text-xs font-semibold text-gray-600 mb-1">Motivo de cancelación</label>
          <textarea v-model="motivoCancelar" rows="3" placeholder="Ingresa el motivo..."
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none mb-4"></textarea>
          <div class="flex justify-end gap-2">
            <button @click="modalCancelar = false" class="px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded-lg">Volver</button>
            <button @click="confirmarCancelar"
              class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition">
              Cancelar ruta
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Modal Carga masiva ── -->
    <Transition name="modal">
      <div v-if="modalCarga" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40" @click="cerrarModalCarga"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-3xl flex flex-col max-h-[90vh]">
          <div class="flex items-center justify-between p-5 border-b border-gray-100">
            <h3 class="text-lg font-bold text-gray-900">Carga masiva de rutas</h3>
            <button @click="cerrarModalCarga" :disabled="importando"
              class="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg disabled:opacity-50">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <div class="p-5 overflow-y-auto space-y-4">
            <!-- Empresa destino (solo SUPERADMIN en modo Todas) -->
            <div v-if="esTodas">
              <label class="block text-xs font-semibold text-gray-600 mb-1">Empresa destino *</label>
              <select v-model="empresaMasivaId"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
                <option value="" disabled>— Seleccionar empresa —</option>
                <option v-for="e in empresas.filter(e => e.id !== '__todas__')" :key="e.id" :value="e.id">{{ e.nombre }}</option>
              </select>
            </div>

            <!-- Paso 1: plantilla -->
            <div>
              <p class="text-sm font-semibold text-gray-700 mb-1">1. Descarga la plantilla</p>
              <button @click="descargarPlantillaExcel"
                class="inline-flex items-center gap-1.5 px-3 py-2 text-sm text-indigo-700 bg-indigo-50 border border-indigo-100 rounded-lg hover:bg-indigo-100 transition">
                ⬇ Descargar plantilla Excel
              </button>
            </div>

            <!-- Paso 2: archivo -->
            <div>
              <p class="text-sm font-semibold text-gray-700 mb-1">2. Completa los datos y sube el archivo</p>
              <label :class="['flex items-center justify-center gap-2 w-full border-2 border-dashed rounded-xl py-4 text-sm transition',
                esTodas && !empresaMasivaId
                  ? 'border-gray-100 text-gray-300 cursor-not-allowed'
                  : 'border-gray-200 text-gray-500 cursor-pointer hover:border-indigo-300 hover:text-indigo-600']">
                📂 {{ archivoNombre || (esTodas && !empresaMasivaId ? 'Selecciona una empresa primero' : 'Seleccionar archivo') }}
                <input type="file" accept=".xlsx,.xls" class="hidden" :disabled="esTodas && !empresaMasivaId" @change="onArchivoCarga"/>
              </label>
              <p class="text-xs text-gray-400 mt-1">Acepta: .xlsx · máx 5MB · columnas: nombre, tipo, conductor_rut, fecha_programada, hora_programada, origen_direccion, destino_direccion, notas</p>
            </div>

            <div v-if="errorCarga" class="bg-red-50 border border-red-100 rounded-lg p-3 text-xs text-red-700">{{ errorCarga }}</div>
            <div v-if="parseandoArchivo" class="text-sm text-gray-400">Leyendo archivo...</div>

            <!-- Validando conductor/vehículo/mantención -->
            <div v-if="validandoCarga">
              <p class="text-sm text-gray-600 mb-1">Verificando conductor y vehículo... {{ progresoVal }} / {{ progresoValTotal }}</p>
              <div class="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                <div class="h-full bg-amber-500 transition-all"
                  :style="{ width: progresoValTotal ? (progresoVal / progresoValTotal * 100) + '%' : '0%' }"></div>
              </div>
            </div>

            <!-- Geocodificando direcciones -->
            <div v-if="geocodificando">
              <p class="text-sm text-gray-600 mb-1">Ubicando direcciones... {{ progresoGeo }} / {{ progresoGeoTotal }}</p>
              <div class="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                <div class="h-full bg-indigo-600 transition-all"
                  :style="{ width: progresoGeoTotal ? (progresoGeo / progresoGeoTotal * 100) + '%' : '0%' }"></div>
              </div>
            </div>

            <!-- Vista previa -->
            <div v-if="filasParseadas.length">
              <div class="flex items-center justify-between mb-2">
                <p class="text-sm font-semibold text-gray-700">Vista previa</p>
                <p class="text-xs text-gray-500">
                  {{ filasValidas.length }} válidas
                  <span v-if="filasParseadas.some(f => f._advertencias?.length)" class="text-amber-600">
                    · {{ filasParseadas.filter(f => f._advertencias?.length && f.valida).length }} con avisos
                  </span>
                  <span v-if="filasParseadas.length - filasValidas.length > 0" class="text-red-500">
                    · {{ filasParseadas.length - filasValidas.length }} con errores (no se crearán)
                  </span>
                </p>
              </div>
              <div class="border border-gray-100 rounded-lg overflow-hidden max-h-64 overflow-y-auto">
                <table class="w-full text-xs">
                  <thead class="bg-gray-50 text-gray-500 sticky top-0">
                    <tr>
                      <th class="px-2 py-2 text-left font-semibold">#</th>
                      <th class="px-2 py-2 text-left font-semibold">Nombre</th>
                      <th class="px-2 py-2 text-left font-semibold">Origen → Destino</th>
                      <th class="px-2 py-2 text-left font-semibold">RUT</th>
                      <th class="px-2 py-2 text-left font-semibold">Vehículo</th>
                      <th class="px-2 py-2 text-left font-semibold">Fecha</th>
                      <th class="px-2 py-2 text-left font-semibold">Hora</th>
                      <th class="px-2 py-2 text-left font-semibold">Estado</th>
                      <th class="px-2 py-2 text-left font-semibold">Avisos</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="f in filasParseadas" :key="f._fila"
                      :class="!f.valida && !f._importada ? 'bg-red-50' : f._advertencias?.length ? 'bg-amber-50/50' : ''">
                      <td class="px-2 py-1.5 text-gray-400">{{ f._fila }}</td>
                      <td class="px-2 py-1.5 text-gray-700">{{ f.nombre || '—' }}</td>
                      <td class="px-2 py-1.5 text-gray-600 max-w-[180px] truncate"
                        :title="`${f.origen_direccion || ''} → ${f.destino_direccion || ''}`">
                        {{ (f.origen_nombre || f.origen_direccion || '—') }} → {{ (f.destino_nombre || f.destino_direccion || '—') }}
                      </td>
                      <td class="px-2 py-1.5 text-gray-600">{{ f.conductor_rut || '—' }}</td>
                      <td class="px-2 py-1.5 text-gray-600">{{ patenteDeConductor(f.conductor_rut) || '—' }}</td>
                      <td class="px-2 py-1.5 text-gray-600">{{ f.fecha_programada || '—' }}</td>
                      <td class="px-2 py-1.5 text-gray-600">{{ f.hora_programada || '—' }}</td>
                      <td class="px-2 py-1.5">
                        <span v-if="f._importada" class="text-green-600 font-medium">✓ Importada</span>
                        <span v-else-if="!f.valida" class="text-red-600 font-medium" :title="f.errores?.join('\n')">✗ {{ f.errores?.[0] }}</span>
                        <span v-else-if="f._advertencias?.length" class="text-amber-600 font-medium">⚠ Con avisos</span>
                        <span v-else class="text-indigo-600 font-medium">✓ OK</span>
                      </td>
                      <td class="px-2 py-1.5 max-w-[200px]">
                        <ul v-if="f._advertencias?.length" class="space-y-0.5">
                          <li v-for="(a, ai) in f._advertencias" :key="ai"
                            class="text-amber-700 leading-tight">
                            ⚠ {{ a.mensaje }}
                          </li>
                        </ul>
                        <span v-else class="text-gray-300">—</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Progreso -->
            <div v-if="importando">
              <p class="text-sm text-gray-600 mb-1">Importando... {{ progresoActual }} / {{ progresoTotal }} rutas</p>
              <div class="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                <div class="h-full bg-indigo-600 transition-all"
                  :style="{ width: progresoTotal ? (progresoActual / progresoTotal * 100) + '%' : '0%' }"></div>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-end gap-2 p-4 border-t border-gray-100">
            <button @click="cerrarModalCarga" :disabled="importando"
              class="px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded-lg disabled:opacity-50">Cancelar</button>
            <button @click="importarRutas" :disabled="!filasValidas.length || importando || (esTodas && !empresaMasivaId)"
              class="px-5 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50">
              {{ importando ? 'Importando...' : `Importar ${filasValidas.length} ruta(s) válida(s)` }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { apiFetch as apiFetchBase } from '../../utils/api.js'
import { apiFetchEmpresa as apiFetch, getEmpresaActiva, setEmpresaActiva, conOpcionTodas, EMPRESA_TODAS } from '../../utils/empresaActiva.js'
import MapaRuta from './MapaRuta.vue'
import { validarRut } from '../../utils/validators.js'
import { usePaginacion } from '../../composables/usePaginacion.js'
import PaginacionTabla from '../../components/PaginacionTabla.vue'

// ── Estado principal ──────────────────────────────────────────────────────
const rutas       = ref([])
const resumen     = ref({ total: 0, activas: 0, pendientes: 0, finalizadas: 0, canceladas: 0, km_mes: 0, finalizadas_mes: 0 })
const vehiculos   = ref([])
const conductores = ref([])

// ── Superadmin: selector de empresa ──────────────────────────────────────
const usuario    = computed(() => JSON.parse(localStorage.getItem('usuario') || '{}'))
const esSuperadmin = computed(() => usuario.value.rol === 'SUPERADMIN')
const sinEmpresa = ref(false)
const empresas   = ref([])
const empresaActiva = ref(getEmpresaActiva())
// Modo "Todas las empresas": vista de solo lectura con columna de empresa.
const esTodas = computed(() => empresaActiva.value?.id === EMPRESA_TODAS)
const mostrarDropdownEmpresa = ref(false)
const busquedaEmpresa = ref('')
const empresasFiltradas = computed(() =>
  busquedaEmpresa.value
    ? empresas.value.filter(e => e.nombre.toLowerCase().includes(busquedaEmpresa.value.toLowerCase()))
    : empresas.value
)
function seleccionarEmpresa(emp) {
  setEmpresaActiva(emp)
  empresaActiva.value = { id: emp.id, nombre: emp.nombre }
  mostrarDropdownEmpresa.value = false
  busquedaEmpresa.value = ''
  sinEmpresa.value = false
  Promise.all([cargarRutas(), cargarVehiculos(), cargarConductores()])
}
const cargando = ref(false)

const tabs = [
  { key: 'todas',      label: 'Todas' },
  { key: 'activo',     label: 'Activas' },
  { key: 'pendiente',  label: 'Pendientes' },
  { key: 'finalizado', label: 'Finalizadas' },
]
const tabActivo = ref('todas')

// ── Panel lateral ─────────────────────────────────────────────────────────
const panelAbierto = ref(false)
const rutaDetalle  = ref(null)
const tabPanel     = ref('detalle')

// ── Historial / comentarios ───────────────────────────────────────────────
const eventos           = ref([])
const cargandoEventos   = ref(false)
const nuevoComentario   = ref('')
const enviandoComentario = ref(false)

async function cargarEventos(rutaId) {
  cargandoEventos.value = true
  try {
    const res = await apiFetch(`/api/empresa/rutas/${rutaId}/comentarios/`)
    if (res.ok) {
      eventos.value = await res.json()
    }
  } finally {
    cargandoEventos.value = false
  }
}

async function enviarComentario() {
  if (!nuevoComentario.value.trim() || enviandoComentario.value) return
  enviandoComentario.value = true
  try {
    const res = await apiFetch(`/api/empresa/rutas/${rutaDetalle.value.id}/comentarios/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto: nuevoComentario.value.trim() }),
    })
    if (res.ok) {
      const evento = await res.json()
      eventos.value.push(evento)
      nuevoComentario.value = ''
    }
  } finally {
    enviandoComentario.value = false
  }
}

async function cambiarTabPanel(tab) {
  tabPanel.value = tab
  if (tab === 'historial' && rutaDetalle.value?.id) {
    await cargarEventos(rutaDetalle.value.id)
  }
}

// ── Modal crear/editar ────────────────────────────────────────────────────
const modalCrear    = ref(false)
const modoEdicion   = ref(false)
const editandoId    = ref(null)
const paso          = ref(1)
const guardando     = ref(false)
const calculando    = ref(false)
const calculoResult = ref(null)
const mapaParadasRef = ref(null)   // ref al MapaRuta del paso 2
const errorModal     = ref('')
const empresaIdForm  = ref('')     // empresa elegida al crear en modo "Todas"

// Al seleccionar empresa en el modal (modo Todas), recargar conductores y vehículos de esa empresa
watch(empresaIdForm, (id) => {
  if (id && id !== '__todas__') {
    form.value.conductor_id = null
    form.value.vehiculo_id  = null
    cargarConductores(id)
    cargarVehiculos(id)
  }
})

// ── Validación pre-vuelo ──────────────────────────────────────────────────
const validando             = ref(false)
const validacionResult      = ref(null)   // { errores: [], advertencias: [] }
const advertenciasAceptadas = ref(false)

const formInicial = () => ({
  tipo: 'carga',
  nombre: '',
  conductor_id: null,
  vehiculo_id: null,
  fecha_programada: '',
  hora_programada: '',
  notas: '',
  paradas: [
    { tipo: 'origen',  orden: 0, nombre: '', direccion: '', latitud: null, longitud: null, notas: '' },
    { tipo: 'destino', orden: 1, nombre: '', direccion: '', latitud: null, longitud: null, notas: '' },
  ],
})
const form = ref(formInicial())

// ── Geocoding ─────────────────────────────────────────────────────────────
const geoSugerencias = ref({})
const geoTimers      = {}

// ── Modales de acción ─────────────────────────────────────────────────────
const rutaAccion     = ref(null)
const modalFinalizar = ref(false)
const finalizarForm  = ref({ km_fin: '' })
const finalizando    = ref(false)   // evita doble envío al finalizar
const modalCancelar  = ref(false)
const motivoCancelar = ref('')

// ── Computed ──────────────────────────────────────────────────────────────
const rutasFiltradas = computed(() =>
  tabActivo.value === 'todas' ? rutas.value : rutas.value.filter(r => r.estado === tabActivo.value)
)

const { pagina, totalPaginas, total, paginado, irA } = usePaginacion(rutasFiltradas, 20)

// ── Autocompletado conductor ↔ vehículo ───────────────────────────────────
const autoFillConductor = ref(false)
const autoFillVehiculo  = ref(false)

function onConductorChange() {
  autoFillConductor.value = false
  autoFillVehiculo.value  = false
  validacionResult.value      = null
  advertenciasAceptadas.value = false
  const id = form.value.conductor_id
  if (!id) return
  const conductor  = conductores.value.find(c => c.id === id)
  const vehiculoId = conductor?.vehiculo?.id
    ?? vehiculos.value.find(v => v.conductor_asignado?.id === id)?.id
  if (vehiculoId) {
    form.value.vehiculo_id = vehiculoId
    autoFillVehiculo.value = true
  }
}

function onVehiculoChange() {
  autoFillConductor.value = false
  autoFillVehiculo.value  = false
  validacionResult.value      = null
  advertenciasAceptadas.value = false
  const id = form.value.vehiculo_id
  if (!id) return
  const vehiculo    = vehiculos.value.find(v => v.id === id)
  const conductorId = vehiculo?.conductor_asignado?.id
    ?? conductores.value.find(c => c.vehiculo?.id === id)?.id
  if (conductorId) {
    form.value.conductor_id = conductorId
    autoFillConductor.value = true
  }
}

// ── Carga de datos ────────────────────────────────────────────────────────
async function cargarRutas() {
  cargando.value = true
  try {
    const res = await apiFetch('/api/empresa/rutas/')
    if (res.status === 400) {
      const d = await res.json()
      if (d.error === 'sin_empresa') { sinEmpresa.value = true; return }
    }
    if (!res.ok) return
    sinEmpresa.value = false
    const data = await res.json()
    rutas.value   = data.rutas || []
    resumen.value = data.resumen || resumen.value
  } finally {
    cargando.value = false
  }
}

async function cargarVehiculos(empresaId = null) {
  const url = empresaId ? `/api/empresa/vehiculos/?empresa_id=${empresaId}` : '/api/empresa/vehiculos/'
  const res = await apiFetch(url)
  if (!res.ok) return
  const data = await res.json()
  vehiculos.value = Array.isArray(data) ? data : (data.vehiculos || data.results || [])
}

async function cargarConductores(empresaId = null) {
  const url = empresaId ? `/api/empresa/conductores/?empresa_id=${empresaId}` : '/api/empresa/conductores/'
  const res = await apiFetch(url)
  if (!res.ok) return
  const data = await res.json()
  conductores.value = Array.isArray(data) ? data : (data.conductores || data.results || [])
}

// ── Panel lateral ─────────────────────────────────────────────────────────
async function abrirPanel(ruta) {
  panelAbierto.value = true
  tabPanel.value     = 'detalle'
  eventos.value      = []
  rutaDetalle.value  = { ...ruta }
  const res = await apiFetch(`/api/empresa/rutas/${ruta.id}/`)
  if (res.ok) {
    rutaDetalle.value = await res.json()
  }
}

// ── Modal crear / editar ──────────────────────────────────────────────────
function abrirModalCrear() {
  modoEdicion.value    = false
  editandoId.value     = null
  empresaIdForm.value  = ''
  form.value           = formInicial()
  calculoResult.value  = null
  paso.value           = 1
  paradaActiva.value   = 0
  coordsAbiertas.value = {}
  coordsError.value    = {}
  modalCrear.value     = true
}

function abrirModalEditar(ruta) {
  modoEdicion.value = true
  editandoId.value  = ruta.id
  form.value = {
    tipo:             ruta.tipo,
    nombre:           ruta.nombre,
    conductor_id:     ruta.conductor_id,
    vehiculo_id:      ruta.vehiculo_id,
    fecha_programada: ruta.fecha_programada || '',
    hora_programada:  ruta.hora_programada  || '',
    notas:            ruta.notas || '',
    paradas: (ruta.paradas || []).map(p => ({
      tipo:      p.tipo,
      orden:     p.orden,
      nombre:    p.nombre,
      direccion: p.direccion,
      latitud:   p.latitud,
      longitud:  p.longitud,
      notas:     p.notas || '',
    })),
  }
  if (!form.value.paradas.some(p => p.tipo === 'origen')) {
    form.value.paradas.unshift({ tipo: 'origen', orden: 0, nombre: '', direccion: '', latitud: null, longitud: null, notas: '' })
  }
  if (!form.value.paradas.some(p => p.tipo === 'destino')) {
    form.value.paradas.push({ tipo: 'destino', orden: 99, nombre: '', direccion: '', latitud: null, longitud: null, notas: '' })
  }
  calculoResult.value = null
  paso.value          = 1
  paradaActiva.value  = 0
  coordsAbiertas.value = {}
  coordsError.value    = {}
  modalCrear.value    = true
}

function cerrarModal() {
  modalCrear.value            = false
  errorModal.value            = ''
  geoSugerencias.value        = {}
  autoFillConductor.value     = false
  autoFillVehiculo.value      = false
  validacionResult.value      = null
  advertenciasAceptadas.value = false
}

async function siguientePaso() {
  errorModal.value = ''

  if (paso.value === 1) {
    // Fecha y hora son obligatorias
    if (!form.value.fecha_programada) {
      errorModal.value = 'La fecha programada es obligatoria.'
      return
    }
    if (!form.value.hora_programada) {
      errorModal.value = 'La hora programada es obligatoria.'
      return
    }
    // Validación de fecha
    {
      const hoy     = new Date(); hoy.setHours(0, 0, 0, 0)
      const elegida = new Date(form.value.fecha_programada + 'T00:00:00')
      if (elegida < hoy) {
        errorModal.value = 'La fecha programada no puede ser anterior a hoy.'
        return
      }
    }

    // Pre-flight: validar conductor + vehículo
    if ((form.value.conductor_id || form.value.vehiculo_id) && !advertenciasAceptadas.value) {
      validando.value = true
      try {
        const res = await apiFetch('/api/empresa/rutas/validar/', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({
            conductor_id:     form.value.conductor_id,
            vehiculo_id:      form.value.vehiculo_id,
            fecha_programada: form.value.fecha_programada || null,
            ruta_id:          modoEdicion.value ? editandoId.value : null,
          }),
        })
        const data = res.ok ? await res.json() : { errores: [], advertencias: [] }
        validacionResult.value = data

        // Si hay errores duros → bloquear
        if (data.errores?.length) { validando.value = false; return }

        // Si hay advertencias → mostrar panel y esperar confirmación del usuario
        if (data.advertencias?.length) { validando.value = false; return }
      } catch {
        // Si el endpoint falla no bloqueamos la creación
        validacionResult.value = null
      }
      validando.value = false
    }

    paso.value++
    // Leaflet no puede medir el contenedor hasta que el DOM del paso 2 sea visible.
    await nextTick()
    mapaParadasRef.value?.invalidarTamano()
    return
  }

  if (paso.value === 2) {
    paso.value = 3
    await ejecutarCalculo()
  } else {
    paso.value++
  }
}

async function ejecutarCalculo() {
  calculando.value    = true
  calculoResult.value = null
  const payload = {
    paradas: form.value.paradas.filter(p => p.latitud && p.longitud).map((p, i) => ({
      tipo: p.tipo, orden: i, nombre: p.nombre, lat: p.latitud, lng: p.longitud,
    })),
  }
  try {
    const res = await apiFetch('/api/empresa/rutas/calcular/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    calculoResult.value = res.ok ? await res.json() : null
  } catch {
    calculoResult.value = null
  } finally {
    calculando.value = false
  }
}

async function guardarRuta() {
  if (esTodas.value && !modoEdicion.value && !empresaIdForm.value) {
    errorModal.value = 'Selecciona una empresa para crear la ruta.'
    return
  }
  guardando.value  = true
  errorModal.value = ''
  const payload = {
    tipo:             form.value.tipo,
    nombre:           form.value.nombre,
    conductor_id:     form.value.conductor_id,
    vehiculo_id:      form.value.vehiculo_id,
    fecha_programada: form.value.fecha_programada || null,
    hora_programada:  form.value.hora_programada  || null,
    notas:            form.value.notas,
    paradas:          form.value.paradas.map((p, i) => ({
      tipo: p.tipo, orden: i, nombre: p.nombre, direccion: p.direccion,
      lat: p.latitud, lng: p.longitud, notas: p.notas || '',
    })),
    ...(esTodas.value && !modoEdicion.value ? { empresa_id: empresaIdForm.value } : {}),
  }
  const url    = modoEdicion.value ? `/api/empresa/rutas/${editandoId.value}/` : '/api/empresa/rutas/'
  const method = modoEdicion.value ? 'PUT' : 'POST'
  try {
    const res = await apiFetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (res.ok) {
      const data = await res.json()
      cerrarModal()
      await cargarRutas()
      toast('exito', modoEdicion.value ? 'Ruta actualizada correctamente.' : 'Ruta creada correctamente.')
      if (data.aviso) setTimeout(() => toast('info', data.aviso), 400)
    } else {
      const errData = await res.json().catch(() => ({}))
      const msgs = [errData.fecha_programada, errData.conductor_id, errData.vehiculo_id, errData.error].filter(Boolean)
      errorModal.value = msgs.length ? msgs.join('\n') : (errData.detail || 'No se pudo guardar la ruta.')
    }
  } catch {
    errorModal.value = 'Error de conexión al guardar la ruta.'
  } finally {
    guardando.value = false
  }
}

// ── Geocoding Nominatim ───────────────────────────────────────────────────
function buscarDireccion(texto, idx) {
  form.value.paradas[idx].nombre   = texto
  form.value.paradas[idx].latitud  = null
  form.value.paradas[idx].longitud = null
  if (geoTimers[idx]) clearTimeout(geoTimers[idx])
  if (!texto || texto.length < 3) { geoSugerencias.value[idx] = []; return }
  geoTimers[idx] = setTimeout(async () => {
    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(texto)}&countrycodes=cl&limit=5`
      const res = await fetch(url, { headers: { 'Accept-Language': 'es' } })
      geoSugerencias.value[idx] = await res.json()
    } catch {
      geoSugerencias.value[idx] = []
    }
  }, 500)
}

function seleccionarDireccion(sug, idx) {
  const partes = sug.display_name.split(',')
  form.value.paradas[idx].nombre    = partes[0].trim()
  form.value.paradas[idx].direccion = sug.display_name
  form.value.paradas[idx].latitud   = parseFloat(sug.lat)
  form.value.paradas[idx].longitud  = parseFloat(sug.lon)
  geoSugerencias.value[idx] = []
}

// Coordenadas manuales por parada (toggle + validación de rango Chile)
const coordsAbiertas = ref({})
const coordsError    = ref({})

// Parada que recibirá el próximo clic en el mapa
const paradaActiva = ref(0)

async function onMapaClick({ lat, lng }) {
  const p = form.value.paradas[paradaActiva.value]
  if (!p) return
  p.latitud  = lat
  p.longitud = lng
  coordsError.value[paradaActiva.value] = ''
  try {
    const url  = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&accept-language=es`
    const res  = await fetch(url)
    const data = await res.json()
    const nom  = data.display_name?.split(',').slice(0, 3).join(',').trim()
    if (nom) { p.nombre = nom; p.direccion = data.display_name }
  } catch { /* sin geocodificación, usamos las coordenadas como nombre */ }
  if (!p.nombre) { p.nombre = `${lat.toFixed(5)}, ${lng.toFixed(5)}`; p.direccion = p.nombre }
}

function validarCoordParada(idx) {
  const p = form.value.paradas[idx]
  coordsError.value[idx] = ''
  const la = parseFloat(p.latitud)
  const ln = parseFloat(p.longitud)
  if (Number.isNaN(la) || Number.isNaN(ln)) return   // aún incompleto
  if (!_enChile(la, ln)) {
    coordsError.value[idx] = 'Las coordenadas no corresponden a Chile.'
    p.latitud = null
    p.longitud = null
    return
  }
  p.latitud = la
  p.longitud = ln
  if (!p.nombre) {
    p.nombre    = `${la.toFixed(5)}, ${ln.toFixed(5)}`
    p.direccion = p.nombre
  }
}

function agregarParada() {
  const destinoIdx = form.value.paradas.findIndex(p => p.tipo === 'destino')
  form.value.paradas.splice(destinoIdx, 0, { tipo: 'parada', orden: destinoIdx, nombre: '', direccion: '', latitud: null, longitud: null, notas: '' })
  form.value.paradas.forEach((p, i) => { p.orden = i })
}

function quitarParada(idx) {
  form.value.paradas.splice(idx, 1)
  form.value.paradas.forEach((p, i) => { p.orden = i })
}

// ── Acciones de ruta ──────────────────────────────────────────────────────
const iniciandoId = ref(null)

async function prepararIniciar(ruta) {
  if (iniciandoId.value) return
  iniciandoId.value = ruta.id
  try {
    const res = await apiFetch(`/api/empresa/rutas/${ruta.id}/iniciar/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}),
    })
    await cargarRutas()
    if (res.ok) toast('exito', 'Ruta iniciada.')
    else { const err = await res.json(); toast('error', err.error || 'Error al iniciar la ruta.') }
  } finally {
    iniciandoId.value = null
  }
}

function prepararFinalizar(ruta) {
  rutaAccion.value = ruta
  const distancia  = Math.round(ruta.distancia_km || 0)
  const kmFin      = ruta.km_inicio != null ? ruta.km_inicio + distancia : distancia || ''
  finalizarForm.value = { km_fin: kmFin }
  modalFinalizar.value = true
}

async function confirmarFinalizar() {
  if (finalizando.value) return            // ya hay un envío en curso
  finalizando.value = true
  try {
    const res = await apiFetch(`/api/empresa/rutas/${rutaAccion.value.id}/finalizar/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(finalizarForm.value),
    })
    if (res.ok) {
      modalFinalizar.value = false
      await cargarRutas()
      toast('exito', 'Ruta finalizada.')
    } else {
      const err = await res.json().catch(() => ({}))
      toast('error', err.error || 'Error al finalizar la ruta.')
      await cargarRutas()   // resincroniza por si la ruta ya cambió de estado
    }
  } finally {
    finalizando.value = false
  }
}

function prepararCancelar(ruta) {
  rutaAccion.value     = ruta
  motivoCancelar.value = ''
  modalCancelar.value  = true
}

async function confirmarCancelar() {
  const res = await apiFetch(`/api/empresa/rutas/${rutaAccion.value.id}/cancelar/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ motivo: motivoCancelar.value }),
  })
  if (res.ok) { modalCancelar.value = false; await cargarRutas(); toast('exito', 'Ruta cancelada.') }
  else { const err = await res.json(); toast('error', err.error || 'Error al cancelar la ruta.') }
}

// ── Helpers ───────────────────────────────────────────────────────────────
function formatFecha(s) {
  if (!s) return '—'
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
}

function formatDuracion(min) {
  if (!min) return '—'
  const h = Math.floor(min / 60)
  const m = min % 60
  return h > 0 ? `${h}h ${m}min` : `${m} min`
}

function formatTimestamp(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('es-CL', { day: '2-digit', month: 'short' }) +
    ' ' + d.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })
}

// ── Combustible (estimado solo-frontend, valores por defecto) ──────────────────
const CONSUMO_DEFAULT = 10     // L/100km (no hay consumo por vehículo en el modelo)
const PRECIO_BENCINA  = 1380
const PRECIO_DIESEL   = 1250

function calcularCombustible(distanciaKm, vehiculo) {
  if (!distanciaKm) return null
  const consumo     = CONSUMO_DEFAULT
  const litros      = (distanciaKm / 100) * consumo
  const precioLitro = vehiculo?.tipo_combustible === 'diesel' ? PRECIO_DIESEL : PRECIO_BENCINA
  return {
    litros:       Math.round(litros * 10) / 10,
    precioLitro,
    total:        Math.round(litros * precioLitro),
    combustible:  vehiculo?.tipo_combustible || 'bencina',
    consumo_l100: consumo,
  }
}

function formatCLP(n) {
  if (n == null) return '—'
  return '$' + Math.round(n).toLocaleString('es-CL')
}

function labelCombustible(tipo) {
  return { bencina: 'bencina', diesel: 'diésel', electrico: 'eléctrico', hibrido: 'híbrido' }[tipo] || tipo
}

// Combustible del paso 3 (cálculo en curso) según el vehículo seleccionado.
const vehiculoSeleccionado = computed(() =>
  vehiculos.value.find(v => v.id === form.value.vehiculo_id) || null
)
const combustibleCalc = computed(() =>
  calcularCombustible(calculoResult.value?.distancia_km, vehiculoSeleccionado.value)
)

// Combustible de una fila de la tabla / detalle (busca el vehículo por id).
function combustibleRuta(ruta) {
  if (!ruta?.distancia_km) return null
  const v = vehiculos.value.find(x => x.id === ruta.vehiculo_id) || null
  return calcularCombustible(ruta.distancia_km, v)
}

function badgeEstado(estado) {
  return {
    activo:     'bg-green-100 text-green-700',
    pendiente:  'bg-blue-100 text-blue-700',
    finalizado: 'bg-gray-100 text-gray-600',
    cancelado:  'bg-red-100 text-red-600',
    borrador:   'bg-yellow-100 text-yellow-700',
  }[estado] || 'bg-gray-100 text-gray-600'
}

function labelEstado(estado) {
  return {
    activo: 'Activo', pendiente: 'Pendiente',
    finalizado: 'Finalizado', cancelado: 'Cancelado', borrador: 'Borrador',
  }[estado] || estado
}

// Formatea el atraso (minutos) como "45 min" o "2 h 15 min".
function formatAtraso(min) {
  if (!min || min <= 0) return ''
  const h = Math.floor(min / 60)
  const m = min % 60
  if (h && m) return `${h} h ${m} min`
  if (h)      return `${h} h`
  return `${m} min`
}

function toast(tipo, mensaje) {
  // AppToast espera { msg, tipo } con tipo = 'success' | 'error' | 'info'
  const tipoNorm = tipo === 'exito' ? 'success' : tipo
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { msg: mensaje, tipo: tipoNorm } }))
}

// ── Inicialización ────────────────────────────────────────────────────────
// ── Carga masiva (Excel / xlsx) ───────────────────────────────────────────────
const modalCarga       = ref(false)
const empresaMasivaId  = ref('')   // empresa destino en modo Todas
const archivoNombre    = ref('')
const filasParseadas   = ref([])
const parseandoArchivo = ref(false)
const importando       = ref(false)
const progresoActual   = ref(0)
const progresoTotal    = ref(0)
const errorCarga       = ref('')
const geocodificando   = ref(false)
const progresoGeo      = ref(0)
const progresoGeoTotal = ref(0)
const validandoCarga   = ref(false)
const progresoVal      = ref(0)
const progresoValTotal = ref(0)

const filasValidas = computed(() => filasParseadas.value.filter(f => f.valida))

// Geocodificación de direcciones (Nominatim) con caché y throttle para respetar el rate limit.
const _geoCache = new Map()
const _delay = (ms) => new Promise(r => setTimeout(r, ms))

async function _geocodificar(direccion) {
  const key = String(direccion || '').trim().toLowerCase()
  if (!key) return null
  if (_geoCache.has(key)) return _geoCache.get(key)
  let r = null
  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(direccion)}&countrycodes=cl&limit=1&accept-language=es`
    const res  = await fetch(url)
    const data = res.ok ? await res.json() : []
    if (data.length) {
      r = {
        lat:    parseFloat(data[0].lat),
        lng:    parseFloat(data[0].lon),
        nombre: data[0].display_name?.split(',').slice(0, 3).join(',').trim() || String(direccion).trim(),
      }
    }
  } catch { /* sin red → r queda null */ }
  _geoCache.set(key, r)
  await _delay(700)   // ~1 req/s recomendado por Nominatim
  return r
}

function abrirModalCarga() {
  modalCarga.value       = true
  empresaMasivaId.value  = ''
  archivoNombre.value    = ''
  filasParseadas.value   = []
  errorCarga.value       = ''
  progresoActual.value   = 0
  progresoTotal.value    = 0
}

watch(empresaMasivaId, (id) => {
  if (id && id !== '__todas__') {
    filasParseadas.value = []   // limpiar preview al cambiar empresa
    archivoNombre.value  = ''
    cargarConductores(id)
    cargarVehiculos(id)
  }
})
function cerrarModalCarga() {
  if (importando.value) return
  modalCarga.value = false
}

async function descargarPlantillaExcel() {
  const XLSX = await import('xlsx')
  const datos = [
    ['nombre','tipo','conductor_rut','fecha_programada','hora_programada','origen_direccion','destino_direccion','notas'],
    ['STG -> VAL #090','carga','12.333.444-5','2025-06-01','08:30','Av. Vicuña Mackenna 4860, Macul','Muelle Prat, Valparaíso',''],
  ]
  const ws = XLSX.utils.aoa_to_sheet(datos)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Rutas')
  XLSX.writeFile(wb, 'plantilla_rutas.xlsx')
}

// Normaliza celdas que Excel puede entregar como Date (fecha/hora) o como texto.
function _celdaFecha(v) {
  if (v == null || v === '') return ''
  if (v instanceof Date) {
    const y = v.getFullYear(), m = String(v.getMonth() + 1).padStart(2, '0'), d = String(v.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }
  return String(v).trim()
}
function _celdaHora(v) {
  if (v == null || v === '') return ''
  if (v instanceof Date) {
    return `${String(v.getHours()).padStart(2, '0')}:${String(v.getMinutes()).padStart(2, '0')}`
  }
  const m = String(v).trim().match(/^(\d{1,2}):(\d{2})/)
  return m ? `${m[1].padStart(2, '0')}:${m[2]}` : String(v).trim()
}

// Vehículo inferido a partir del RUT del conductor (para mostrar en el preview).
function patenteDeConductor(rut) {
  if (!rut) return ''
  const c = conductores.value.find(x => _normRut(x.rut) === _normRut(rut))
  return c?.vehiculo?.patente || ''
}

function _enChile(la, ln) {
  return la >= -56 && la <= -17 && ln >= -76 && ln <= -65
}

function _normRut(r) {
  return String(r || '').replace(/\./g, '').trim().toLowerCase()
}

function _validarFilaCarga(f, i) {
  const errores = []
  if (!f.nombre || !String(f.nombre).trim()) errores.push('Nombre requerido')
  if (!['carga','personas'].includes(String(f.tipo || '').toLowerCase().trim())) errores.push('Tipo inválido')
  if (!f.origen_direccion)  errores.push('Dirección de origen requerida')
  else if (!f._origen_ok)   errores.push('No se pudo ubicar la dirección de origen')
  if (!f.destino_direccion) errores.push('Dirección de destino requerida')
  else if (!f._destino_ok)  errores.push('No se pudo ubicar la dirección de destino')
  for (const [etq, ok, la, ln] of [['origen', f._origen_ok, f.origen_lat, f.origen_lng], ['destino', f._destino_ok, f.destino_lat, f.destino_lng]]) {
    if (ok && !_enChile(la, ln)) errores.push(`${etq} fuera de Chile`)
  }
  if (f.fecha_programada) {
    const d = new Date(`${String(f.fecha_programada).trim()}T00:00:00`)
    if (Number.isNaN(d.getTime())) errores.push('Fecha inválida (use AAAA-MM-DD)')
    else { const hoy = new Date(); hoy.setHours(0,0,0,0); if (d < hoy) errores.push('Fecha en el pasado') }
  }
  if (f.hora_programada && !/^([01]?\d|2[0-3]):[0-5]\d$/.test(String(f.hora_programada).trim())) {
    errores.push('Hora inválida (use HH:mm)')
  }
  // Conductor: el RUT es opcional, pero si viene debe ser válido y existir como
  // conductor de esta empresa. El vehículo se infiere del conductor (no se pide patente).
  if (f.conductor_rut) {
    if (!validarRut(f.conductor_rut).valido) {
      errores.push('RUT con formato inválido (ej: 12.333.444-5)')
    } else if (!conductores.value.some(c => _normRut(c.rut) === _normRut(f.conductor_rut))) {
      errores.push('Conductor no registrado en la empresa')
    }
  }
  return { ...f, _fila: i + 1, valida: errores.length === 0, errores }
}

async function onArchivoCarga(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (file.size > 5 * 1024 * 1024) { errorCarga.value = 'El archivo supera los 5 MB.'; e.target.value = ''; return }
  archivoNombre.value    = file.name
  errorCarga.value       = ''
  parseandoArchivo.value = true
  try {
    const XLSX    = await import('xlsx')
    const buffer  = await file.arrayBuffer()
    const wb      = XLSX.read(buffer, { cellDates: true })
    const ws      = wb.Sheets[wb.SheetNames[0]]
    const filas   = XLSX.utils.sheet_to_json(ws, { header: 1 }).slice(1)
      .filter(fila => fila.length && fila.some(c => c !== '' && c != null))
      .map(fila => ({
        nombre:            fila[0],
        tipo:              String(fila[1] || '').toLowerCase().trim(),
        conductor_rut:     fila[2] != null ? String(fila[2]).trim() : '',
        fecha_programada:  _celdaFecha(fila[3]),
        hora_programada:   _celdaHora(fila[4]),
        origen_direccion:  fila[5] != null ? String(fila[5]).trim() : '',
        destino_direccion: fila[6] != null ? String(fila[6]).trim() : '',
        notas:             fila[7] || '',
      }))

    if (!filas.length) {
      errorCarga.value = 'El archivo no tiene filas de datos.'
      return
    }

    // Geocodificar las direcciones a coordenadas (Nominatim).
    parseandoArchivo.value = false
    geocodificando.value   = true
    progresoGeoTotal.value = filas.length
    progresoGeo.value      = 0
    validandoCarga.value   = false
    progresoVal.value      = 0
    const procesadas = []
    for (const f of filas) {
      const o = f.origen_direccion  ? await _geocodificar(f.origen_direccion)  : null
      const d = f.destino_direccion ? await _geocodificar(f.destino_direccion) : null
      procesadas.push({
        ...f,
        origen_nombre:  o?.nombre || f.origen_direccion,
        origen_lat:     o ? o.lat : NaN,
        origen_lng:     o ? o.lng : NaN,
        _origen_ok:     !!o,
        destino_nombre: d?.nombre || f.destino_direccion,
        destino_lat:    d ? d.lat : NaN,
        destino_lng:    d ? d.lng : NaN,
        _destino_ok:    !!d,
      })
      progresoGeo.value++
    }
    geocodificando.value = false
    const conValidacion  = procesadas.map(_validarFilaCarga)

    // Validar conductor/vehículo/mantención para cada fila válida con fecha y conductor.
    const filasSujetas = conValidacion.filter(
      f => f.valida && (f.conductor_rut || patenteDeConductor(f.conductor_rut)) && f.fecha_programada
    )
    if (filasSujetas.length) {
      validandoCarga.value   = true
      progresoValTotal.value = filasSujetas.length
      progresoVal.value      = 0
      for (const f of filasSujetas) {
        const cond  = conductores.value.find(c => _normRut(c.rut) === _normRut(f.conductor_rut))
        const veh   = cond?.vehiculo?.id ? vehiculos.value.find(v => v.patente === cond.vehiculo.patente) : null
        try {
          const validarBody = {
              conductor_id:     cond?.id || null,
              vehiculo_id:      veh?.id || null,
              fecha_programada: f.fecha_programada,
            }
          if (esTodas.value && empresaMasivaId.value) validarBody.empresa_id = empresaMasivaId.value
          const res = await apiFetch('/api/empresa/rutas/validar/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(validarBody),
          })
          if (res.ok) {
            const data = await res.json()
            const idx  = conValidacion.findIndex(x => x._fila === f._fila)
            if (idx !== -1) {
              conValidacion[idx]._advertencias = data.advertencias || []
              // Errores duros del backend (vehículo en mantención, conductor bloqueado, etc.)
              // se agregan a los errores de la fila para bloquear la importación.
              if (data.errores?.length) {
                conValidacion[idx].valida  = false
                conValidacion[idx].errores = data.errores.map(e => e.mensaje)
              }
            }
          }
        } catch { /* sin red → ignorar, no bloquea */ }
        progresoVal.value++
      }
      validandoCarga.value = false
    }

    filasParseadas.value = conValidacion
  } catch {
    errorCarga.value     = 'No se pudo leer el archivo. Verifica que sea un .xlsx válido.'
    filasParseadas.value = []
  } finally {
    parseandoArchivo.value = false
    geocodificando.value   = false
    e.target.value = ''
  }
}

function _mensajeError(errData) {
  if (!errData) return 'Error desconocido'
  // El backend puede devolver { error: '...' } o { conductor_id: '...', vehiculo_id: '...' }
  if (errData.error) return errData.error
  const msgs = [errData.conductor_id, errData.vehiculo_id, errData.fecha_programada]
    .filter(Boolean)
  return msgs.length ? msgs[0] : JSON.stringify(errData)
}

async function importarRutas() {
  const validas = filasValidas.value
  if (!validas.length) return
  importando.value     = true
  progresoTotal.value  = validas.length
  progresoActual.value = 0
  let exitosas = 0

  // Copia las filas para anotar el resultado de cada una.
  const resultados = filasParseadas.value.map(f => ({ ...f }))

  for (const ruta of validas) {
    const idx = resultados.findIndex(f => f._fila === ruta._fila)
    let patente = null
    if (ruta.conductor_rut) {
      const cond = conductores.value.find(c => _normRut(c.rut) === _normRut(ruta.conductor_rut))
      if (cond?.vehiculo?.patente) patente = cond.vehiculo.patente
    }
    try {
      const payload = {
          nombre:           ruta.nombre,
          tipo:             ruta.tipo,
          vehiculo_patente: patente,
          conductor_rut:    ruta.conductor_rut || null,
          fecha_programada: ruta.fecha_programada || null,
          hora_programada:  ruta.hora_programada || null,
          notas:            ruta.notas || '',
          paradas: [
            { tipo: 'origen',  orden: 1, nombre: ruta.origen_nombre,  lat: ruta.origen_lat,  lng: ruta.origen_lng },
            { tipo: 'destino', orden: 2, nombre: ruta.destino_nombre, lat: ruta.destino_lat, lng: ruta.destino_lng },
          ],
        }
      if (esTodas.value && empresaMasivaId.value) payload.empresa_id = empresaMasivaId.value
      const res = await apiFetch('/api/empresa/rutas/', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
      })
      if (res.ok) {
        exitosas++
        if (idx !== -1) resultados[idx] = { ...resultados[idx], _importada: true }
      } else {
        const errData = await res.json().catch(() => null)
        const msg = _mensajeError(errData)
        if (idx !== -1) resultados[idx] = { ...resultados[idx], valida: false, errores: [msg], _importada: false }
      }
    } catch {
      if (idx !== -1) resultados[idx] = { ...resultados[idx], valida: false, errores: ['Error de conexión'], _importada: false }
    }
    progresoActual.value++
  }

  importando.value = false
  // Actualiza la tabla del preview con los resultados de importación.
  filasParseadas.value = resultados

  const fallidas = validas.length - exitosas
  toast(exitosas > 0 ? 'exito' : 'error', `${exitosas} rutas importadas${fallidas ? ` · ${fallidas} fallidas` : ''}`)
  if (exitosas > 0) await cargarRutas()
  // No cierra el modal si hubo fallos, para que el usuario vea cuáles y por qué.
  if (exitosas > 0 && fallidas === 0) modalCarga.value = false
}

onMounted(async () => {
  if (esSuperadmin.value) {
    const res = await apiFetchBase('/api/empresas/')
    if (res.ok) {
      const data = await res.json()
      empresas.value = conOpcionTodas(Array.isArray(data) ? data : [])
    }
  }
  await Promise.all([cargarRutas(), cargarVehiculos(), cargarConductores()])
})
</script>

<style scoped>
.panel-enter-active, .panel-leave-active { transition: opacity 0.2s; }
.panel-enter-from, .panel-leave-to { opacity: 0; }
.modal-enter-active, .modal-leave-active { transition: opacity 0.15s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.fade-slide-enter-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.fade-slide-leave-active { transition: opacity 0.15s ease; }
.fade-slide-enter-from { opacity: 0; transform: translateY(-6px); }
.fade-slide-leave-to   { opacity: 0; }
</style>
