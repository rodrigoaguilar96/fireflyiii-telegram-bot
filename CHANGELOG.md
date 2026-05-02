# 📋 Changelog

Historial de releases de **Firefly III Telegram Bot**, basado en las releases de GitHub.

Seguimos [SemVer](https://semver.org/): `MAJOR.MINOR.PATCH`.

---

## [v1.2.2] - 2026-05-01

**Corrección menor en el flujo de registro de gastos.**

- Se ordenan alfabéticamente las suscripciones/facturas al momento de seleccionarlas.
- Se evita mostrar opciones en un orden arbitrario.
- Se agregan tests para validar el orden visible y la selección correcta por `id`.
- No hay cambios incompatibles ni impacto en el formato de datos.

---

## [v1.2.1] - 2026-05-01

**Upgrade de `python-telegram-bot` a `22.7`.**

- Se actualizó el pin en `requirements.txt`.
- Se ajustó `bot/main.py` para extraer el registro de handlers y facilitar la validación de arranque.
- Se agregó `tests/test_startup.py` con smoke tests sin red para cubrir:
  - arranque básico;
  - validación de variables de entorno faltantes;
  - registro de handlers;
  - invocación de `run_polling()`.
- No se introdujeron cambios funcionales intencionales.

---

## [v1.2.0] - 2026-05-01

**Transferencias y selección de suscripciones/facturas en gastos.**

### Mejoras funcionales

- Se agregó la opción **🔁 Transferir** en el menú principal.
- Se incorporó un flujo paso a paso para registrar transferencias simples:
  - ingreso de monto;
  - selección de cuenta origen;
  - selección de cuenta destino;
  - confirmación antes de registrar.
- La transferencia se registra con descripción automática: `transferencia cuentaOrigen-cuentaDestino`.
- Las cuentas del flujo de transferencias se muestran en dos columnas.
- Se agregó selección opcional de suscripción/factura (`bill`) en el flujo de registrar gasto.
- Si no hay bills activas utilizables, el flujo continúa sin fricción.

### Mejoras técnicas

- Se agregó cobertura automatizada para el flujo de transferencias.
- Se agregaron tests para callbacks conversacionales, selecciones inválidas y layout de botones.
- Se amplió la cobertura del flujo de gastos para incluir `bill_id` y escenarios sin bills utilizables.
- Se agregó soporte en el cliente para consultar bills desde Firefly III.
- Se registró un `ConversationHandler` dedicado para transferencias.

---

## [v1.1.0] - 2026-04-28

**Mejora del flujo de registro de gastos y red de seguridad automatizada.**

### Mejoras funcionales

- Se agregó el botón **⏭️ Sin tags** en el flujo paso a paso.
- Ya no es necesario escribir `skip` para continuar sin tags.
- Se simplificó el paso de monto/descripción: ahora se ingresan juntos.
- Se eliminó el mensaje incoherente que sugería escribir solo el monto.

### Mejoras técnicas

- Se agregó infraestructura de tests con `pytest` y `pytest-asyncio`.
- Se incorporaron tests automatizados para el flujo crítico de gastos desde menú hasta payload final.
- Se agregaron tests para `/gasto`, menú principal, listado/detalle de cuentas, autorización, caché, cliente Firefly III y helpers.
- El workflow de CI ahora instala dependencias, compila el proyecto y ejecuta tests.
- Suite validada en release: `25 tests`.

---

## [v1.0.9] - 2026-04-26

**Mejoras de layout en selección de cuentas.**

- Las cuentas de origen se muestran en dos columnas durante el flujo paso a paso.
- Las cuentas de destino también se muestran en dos columnas.
- Separadores y acciones especiales se mantienen en fila completa:
  - **🕐 Recientes**;
  - **── Todas las cuentas ──**;
  - **⏭️ Sin cuenta destino**;
  - **➕ Crear nueva cuenta**.
- Se validó que categorías y tags sigan funcionando correctamente.

---

## [v1.0.8] - 2026-04-24

**Corrección del flujo de gasto desde `/menu`.**

- Seleccionar una cuenta de origen desde `/menu` ahora continúa correctamente la conversación.
- Se agregó workflow de compile check para pull requests.
- Se actualizó Docker publish workflow a `docker/build-push-action@v7`.
- Se actualizó `.gitignore` para excluir `.DS_Store` y `plugins/` local.

---

## [v1.0.7] - 2026-04-24

**Correcciones del menú y fallback de cuentas.**

- Se corrigió el flujo de `/menu` en Telegram.
- **Registrar gasto** inicia correctamente el flujo guiado.
- **Ver cuentas** vuelve a mostrar cuentas disponibles aunque la API devuelva vacío al filtrar por tipo.
- **Ver cuenta + movimientos** lleva al selector real de cuentas.
- Se ajustó el routing de callbacks del menú.
- Se agregó fallback local para filtrar cuentas cuando Firefly III no responde bien al filtro remoto.

---

## [v1.0.6] - 2026-04-03

**Mejora grande del flujo de gastos.**

### Nuevas funcionalidades

- Categorías en el flujo paso a paso y soporte en `/gasto`.
- Presupuestos opcionales para gastos.
- Tags separados por coma.
- Confirmación antes de crear el gasto.
- Destinos recientes.
- Caché TTL para cuentas y categorías.
- Autorización por `ALLOWED_USER_IDS`.
- Comando `/refresh`.
- Comando `/gasto`, reemplazando a `/expense`.

### Correcciones

- Timeouts HTTP de 10 segundos para evitar que el bot se congele.
- `/cancel` limpia correctamente `user_data`.
- Configuración de cuentas ocultas consolidada desde `.env`.
- Typo corregido: `/expenseButtom` → `/expenseButton`.
- Validación de variables requeridas al arrancar.
- Reemplazo de `bare except` por excepciones específicas.

### Breaking changes

- `/expense` fue reemplazado por `/gasto` con nueva sintaxis.
- Categoría y destino ya no se auto-crean si no existen; se omiten.
- El origen es obligatorio en `/gasto`.

---

## [v1.0.5] - 2025-05-14

**Corrección de paginación de cuentas.**

- Se corrigió la obtención de cuentas afectada por paginación.

---

## [v1.0.4] - 2025-04-26

**Primera release pública.**

- Menú interactivo en Telegram para registrar gastos y consultar cuentas.
- `/assets` para listar cuentas de tipo `asset`.
- `/expense <monto> "<desc>" <origen> <destino>` para registrar gastos manualmente.
- `/cuenta <nombre> <N>` para mostrar movimientos recientes.
- Flujo asistido por botones para registrar gastos.
- Configuración de cuentas ocultas y logs vía `.env`.
- Dockerfile y `docker-compose.yml` listos para deploy.

---

## Releases draft históricas

Estas releases existen en GitHub como draft y se conservan solo como referencia histórica.

### [v1.0.3] - 2025-04-26

- Soporte multi-arquitectura `linux/amd64` y `linux/arm64`.
- Automatización de releases: tag, release, build y push de imágenes Docker.
- Corrección de triggers automáticos.
- Actualización automática de `latest` con cada versión publicada.
- Sin cambios funcionales.

### [v1.0.2] - 2025-04-26

- Soporte multi-arquitectura `linux/amd64` y `linux/arm64`.
- Automatización de releases: tag, release, build y push de imágenes Docker.
- Corrección de triggers automáticos.
- Actualización automática de `latest` con cada versión publicada.
- Sin cambios funcionales.

### [v1.0.1] - 2025-04-26

- Corrección y mejora de workflows para soporte multi-arquitectura `amd64` y `arm64`.

### [v1.0.0] - 2025-04-26

- Primera versión estable del bot.
- Menú interactivo en Telegram.
- `/assets`, `/expense` y `/cuenta`.
- Flujo de creación de gastos paso a paso.
- Configuración vía `.env`.
- Imagen Docker pública y automatización de builds/releases.

---

Hecho con ❤️ por [Rodrigo Aguilar](https://github.com/rodrigoaguilar96)
