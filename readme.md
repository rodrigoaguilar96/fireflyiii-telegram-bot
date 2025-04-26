# 🤖 Firefly III Telegram Bot

Este bot te permite interactuar con tu instancia de [Firefly III](https://www.firefly-iii.org/) directamente desde Telegram para consultar cuentas, ver movimientos y registrar gastos fácilmente.

---


## 📦 Instalación rápida

### Usando Docker (recomendado)

1. **Pull de la imagen oficial**

```bash
docker pull rja96/fireflyiii-telegram-bot:latest
```

2. **Configurar tu .env**
```bash
cp .env.example .env
```
Completar las variables necesarias:
```env
TELEGRAM_BOT_TOKEN=...
FIREFLY_III_API_URL=http://firefly_iii_core:8080
FIREFLY_III_API_TOKEN=...
HIDE_ACCOUNTS=Cuenta1,Cuenta2
LOG_LEVEL=INFO  # Puede ser DEBUG, INFO, WARNING, ERROR o CRITICAL
```

3. **Levantar el bot**
```bash
docker-compose up -d
```
---
## ✨ Características

- 📋 Menú interactivo con botones en Telegram.
- 💼 `/assets`: Lista cuentas de tipo "asset".
- 💸 `/expense <monto> "<desc>" <origen> <destino>`: Registra un gasto.
- 📈 `/cuenta <nombre> <N>`: Muestra movimientos recientes de una cuenta.
- 🧠 Flujo con botones para crear gastos paso a paso.
- 🔐 Cuentas ocultas personalizables vía `.env`.

---

## ⚙️ Requisitos para desarrollo local

- Python 3.11+
- Docker + Docker Compose
- Cuenta de Telegram con un bot creado en [@BotFather](https://t.me/BotFather)
- Instancia de Firefly III corriendo (idealmente vía Docker)

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
- [x] Release automation vía GitHub Actions
- [ ] Agregar presupuestos, etiquetas y categorías
- [ ] Mejorar validaciones de inputs

---

## 📚 Documentación adicional

- [Changelog](./CHANGELOG.md): Historial completo de versiones y cambios importantes.

---

Hecho con ❤️ por [Rodrigo Aguilar](https://github.com/rodrigoaguilar96)
