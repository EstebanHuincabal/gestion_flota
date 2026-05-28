# Mejoras implementadas — v2.5 (Mayo 2026)

## Sistema profesional de manejo de errores

Implementado en Mayo 2026. Ver sección 16 de `docs/documentacion.md` para detalles completos.

### Archivos creados / modificados

| Archivo | Cambio |
|---|---|
| `gestion_backend/g_de_flota/error_helpers.py` | **Nuevo** — `error_response`, `validar_campos`, decorador `vista_segura` |
| `gestion_backend/g_de_flota/middleware.py` | **Modificado** — agrega `ErrorHandlerMiddleware` (captura 500 → JSON) |
| `gestion_backend/gestion_backend/settings.py` | **Modificado** — registra `ErrorHandlerMiddleware` en MIDDLEWARE |
| `gestion-frontend/src/utils/api.js` | **Reescrito** — timeout 15 s, `ApiError`, `safeJsonParse`, sin respuestas no-JSON |
| `gestion-frontend/src/composables/useAsync.js` | **Nuevo** — composable `useAsync` con manejo automático de loading/error |
| `gestion-frontend/src/components/ErrorBoundary.vue` | **Nuevo** — captura errores de renderizado Vue |
| `gestion-frontend/src/App.vue` | **Modificado** — envuelve `<RouterView>` en `<ErrorBoundary>` |
| `gestion-frontend/src/router/index.js` | **Modificado** — guards usan `safeJsonParse` en lugar de `JSON.parse` directo |
| `docs/documentacion.md` | **Modificado** — sección 16 con documentación completa |

### Checklist QA sugerido

**Autenticación:**
- [ ] Acceder a endpoint protegido sin token → debe retornar 401 JSON (no HTML)
- [ ] Acceder con token expirado → el frontend hace logout
- [ ] Acceder con rol incorrecto → 403 JSON

**Validación:**
- [ ] Enviar body vacío a cualquier POST → 400 con mensaje claro
- [ ] Enviar JSON malformado → 400, no 500
- [ ] Enviar campos faltantes → lista qué campos faltan

**Límites del plan:**
- [ ] Crear recurso al límite del plan → 403 con código `LIMITE_PLAN`
- [ ] Acceder a módulo no incluido → 403 con código `MODULO_NO_INCLUIDO`
- [ ] Empresa suspendida → 402 con código `SUSCRIPCION_BLOQUEADA`

**Red:**
- [ ] Desconectar el backend → mensaje de error, no pantalla en blanco
- [ ] Request > 15 segundos → mensaje de timeout
- [ ] Respuesta no-JSON del servidor → no rompe el frontend

**Concurrencia:**
- [ ] Doble click en guardar → no crea registros duplicados
- [ ] Navegar rápido entre páginas mientras carga → sin errores de componente desmontado

**Datos:**
- [ ] Acceder a recurso de otra empresa → 404
- [ ] Eliminar recurso con dependencias → 400 con mensaje explicativo
