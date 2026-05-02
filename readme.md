# 🤖 Firefly III Telegram Bot

Bot de Telegram para operar una instancia de [Firefly III](https://www.firefly-iii.org/) desde el celular: consultar cuentas, ver movimientos, registrar gastos y crear transferencias sin entrar al panel web.

El foco del proyecto es uso personal y rápido. NO apunta a ser un cliente completo de Firefly III ni a replicar toda su UI dentro de Telegram.

---

## ✨ Funcionalidades actuales

- 📋 Menú interactivo con botones en Telegram (`/menu`).
- 💸 Registro rápido de gastos con `/gasto`.
- 🧠 Registro guiado de gastos paso a paso con botones.
- 🔁 Transferencias entre cuentas de activo.
- 💼 Consulta de cuentas de activo.
- 📈 Consulta de saldo y movimientos recientes por cuenta.
- 📂 Categorías en gastos.
- 📊 Presupuestos en gastos.
- 🧾 Suscripciones/facturas existentes de Firefly III en gastos.
- 🏷️ Tags en gastos.
- ➕ Creación de nuevas cuentas de destino tipo `expense` desde el flujo guiado.
- 🔐 Ocultamiento de cuentas vía `.env`.
- ⚡ Caché de cuentas, categorías, presupuestos y suscripciones/facturas.
- 🐳 Imagen Docker multi-arquitectura (`amd64`, `arm64`).

---

## 📦 Instalación rápida con Docker

1. **Descargá la imagen**

```bash
docker pull rja96/fireflyiii-telegram-bot:latest
```

2. **Configurá el entorno**

```bash
cp .env.example .env
```

Variables principales:

```env
TELEGRAM_BOT_TOKEN=...
FIREFLY_III_API_URL=http://firefly_iii_core:8080
FIREFLY_III_API_TOKEN=...
HIDE_ACCOUNTS=Cuenta1,Cuenta2
ALLOWED_USER_IDS=123456789
TIMEZONE=Europe/Lisbon
LOG_LEVEL=INFO
```

> Si `ALLOWED_USER_IDS` queda vacío, el bot queda abierto a cualquiera que lo encuentre. Para uso real, conviene configurarlo.

3. **Levantá el bot**

```bash
docker-compose up -d
```

El `docker-compose.yml` asume que Firefly III corre en la red Docker externa `fireflyiii_firefly_iii`.

---

## 🧪 Comandos disponibles

```text
/start                  → Muestra el menú principal
/menu                   → Reabre el menú
/assets                 → Lista cuentas de tipo asset
/cuenta <nombre> [N]    → Muestra saldo y últimos N movimientos de una cuenta
/gasto                  → Muestra ayuda del registro rápido
/gasto <monto> <desc> <origen> [categoría] [destino]
                        → Registra un gasto rápido
/expenseButton          → Inicia el registro guiado de gasto
/transferencia          → Inicia una transferencia entre cuentas
/refresh                → Limpia el caché de datos de Firefly III
/cancel                 → Cancela el flujo actual
```

---

## 💸 Registro rápido de gastos

La forma más directa para el día a día es `/gasto`:

```text
/gasto 20 burgerking tarjeta comida
```

Formato:

```text
/gasto <monto> <descripción> <origen> [categoría] [destino]
```

Reglas importantes:

- `<origen>` es obligatorio y debe ser una cuenta existente.
- `[categoría]` es opcional; si no existe, se omite.
- `[destino]` es opcional; si no existe, se omite.
- Los nombres no distinguen mayúsculas/minúsculas.

Ejemplos:

```text
/gasto 20 burgerking tarjeta comida
/gasto 13.99 uber transporte tarjeta credito
/gasto 5.50 cafe efectivo
```

---

## 🧠 Registro guiado de gastos

Usá `/expenseButton` o el botón **💸 Registrar gasto** del menú.

El flujo guía por:

1. Cuenta de origen.
2. Monto y descripción.
3. Cuenta de destino, sin destino o creación de una nueva.
4. Categoría opcional.
5. Presupuesto opcional.
6. Suscripción/factura opcional.
7. Tags opcionales.
8. Confirmación antes de crear el gasto.

Esto es más lento que `/gasto`, pero más seguro cuando querés clasificar bien la transacción.

---

## 🔁 Transferencias

Usá `/transferencia` o el botón **🔁 Transferir** del menú para mover dinero entre cuentas de activo.

El flujo pide:

1. Monto.
2. Cuenta de origen.
3. Cuenta de destino.
4. Confirmación.

La descripción se genera automáticamente como:

```text
transferencia <origen>-<destino>
```

---

## ⚙️ Desarrollo local

Requisitos:

- Python 3.11+
- Docker + Docker Compose
- Bot de Telegram creado con [@BotFather](https://t.me/BotFather)
- Instancia de Firefly III accesible desde el bot

Instalación básica:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Tests:

```bash
pytest
```

---

## 📚 Documentación adicional

- [Changelog](./CHANGELOG.md): historial de versiones publicadas.
- [Releasing](./RELEASING.md): proceso de release.

---

Hecho con ❤️ por [Rodrigo Aguilar](https://github.com/rodrigoaguilar96)
