# 🤖 Firefly III Telegram Bot

Este bot te permite interactuar con tu instancia de [Firefly III](https://www.firefly-iii.org/) directamente desde Telegram para consultar cuentas, ver movimientos y registrar gastos fácilmente.

---

## ✨ Características

- 📋 Menú interactivo con botones en Telegram.
- 💼 `/assets`: Lista cuentas de tipo "asset".
- 💸 `/expense <monto> "<desc>" <origen> <destino>`: Registra un gasto.
- 📈 `/cuenta <nombre> <N>`: Muestra movimientos recientes de una cuenta.
- 🧠 Flujo con botones para crear gastos paso a paso.
- 🔐 Cuentas ocultas personalizables vía `.env`.

---

## 📁 Estructura del proyecto

```
fireflyiii_telegram_bot/
├── bot/                   # Código fuente del bot
│   ├── handlers/          # Handlers organizados por comando
│   ├── client.py          # Cliente Firefly III
│   ├── config.py          # Variables de entorno
│   ├── constants.py       # Constantes del bot
│   └── main.py            # Punto de entrada de la app
├── run.py                 # Ejecuta el bot
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── readme.md
```

---

## ⚙️ Requisitos

- Python 3.11+
- Docker + Docker Compose
- Cuenta de Telegram con un bot creado en [@BotFather](https://t.me/BotFather)
- Instancia de Firefly III corriendo (idealmente vía Docker)

---

## 🛠️ Instalación

1. **Cloná el repo**

```bash
git clone https://github.com/rodrigoaguilar96/fireflyiii-telegram-bot.git
cd fireflyiii-telegram-bot
```

2. **Creá tu archivo `.env`**

```bash
cp .env.example .env
```

Editá las variables necesarias con tus propios valores:

```env
TELEGRAM_BOT_TOKEN=...
FIREFLY_III_API_URL=http://firefly_iii_core:8080
FIREFLY_III_API_TOKEN=...
HIDE_ACCOUNTS=Cuenta1,Cuenta2
LOG_LEVEL=INFO  # Puede ser DEBUG, INFO, WARNING, ERROR o CRITICAL
```

3. **Levantá el bot**

```bash
docker-compose build
docker-compose up -d
```

---

## 🧪 Comandos disponibles

```
/start            → Muestra el menú principal
/menu             → Reabre el menú
/assets           → Lista cuentas de tipo asset
/cuenta <nombre> <N> → Muestra los últimos N movimientos de una cuenta
/expense ...      → Registra un gasto (manual)
/expenseButtom    → Registra gasto paso a paso con botones
/cancel           → Cancela el flujo actual
```

---

## 🚧 Roadmap personal

- [x] Estructura modular escalable
- [x] Registro de gastos y consultas por cuenta
- [x] Docker + `.env` seguro
- [ ] Agregar presupuestos, etiquetas y categorías

---

Hecho con ❤️ por [Rodrigo Aguilar](https://github.com/rodrigoaguilar96)
