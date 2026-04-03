# 🤖 Firefly III Telegram Bot

Este bot te permite interactuar con tu instancia de [Firefly III](https://www.firefly-iii.org/) directamente desde Telegram para consultar cuentas, ver movimientos y registrar gastos fácilmente con categorías, presupuestos y tags.

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
ALLOWED_USER_IDS=123456789    # Opcional — tu ID de Telegram
TIMEZONE=Europe/Lisbon        # Tu zona horaria
LOG_LEVEL=INFO
```

3. **Levantar el bot**
```bash
docker-compose up -d
```

---

## ✨ Características

- 📋 Menú interactivo con botones en Telegram.
- 💸 **Registro rápido**: `/gasto 20 burgerking tarjeta comida` — registra un gasto en un solo mensaje.
- 🧠 **Flujo paso a paso**: origen → monto/descripción → destino → categoría → presupuesto → tags → confirmación.
- 📂 **Categorías**: seleccioná o asigná categorías a tus gastos.
- 📊 **Presupuestos**: asigná presupuestos a tus gastos.
- 🏷️ **Tags**: agregá tags como `comida, delivery, almuerzo`.
- 🕐 **Destinos recientes**: las cuentas de destino más usadas aparecen primero.
- 💼 `/assets`: Lista cuentas de tipo "asset".
- 📈 `/cuenta <nombre> <N>`: Muestra movimientos recientes de una cuenta.
- 🔐 Cuentas ocultas personalizables vía `.env`.
- 🔒 **Autorización**: restringí el acceso a usuarios específicos con `ALLOWED_USER_IDS`.
- ⚡ **Caché**: las cuentas y categorías se cachean para respuestas más rápidas.

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
/gasto <monto> <desc> <origen> [cat] [dest] → Registro rápido de gasto
/expenseButton    → Registro de gasto paso a paso con botones
/cancel           → Cancela el flujo actual
/refresh          → Refresca el caché de cuentas/categorías
```

### Flujo rápido recomendado (día a día)

La forma más rápida de registrar un gasto es con `/gasto`:

```
/gasto 20 burgerking tarjeta comida
```

Esto registra un gasto de 20 con descripción "burgerking", cuenta de origen "tarjeta" y categoría "comida". El origen es obligatorio y debe ser una cuenta existente. La categoría y el destino son opcionales — si no existen, se omiten.

Ejemplos:
```
/gasto 20 burgerking tarjeta comida
/gasto 13.99 uber tarjeta credito transporte tarjeta
/gasto 5.50 cafe efectivo
```

### Flujo paso a paso (completo)

Usá `/expenseButton` o el botón "💸 Registrar gasto" del menú para:
1. Seleccionar cuenta de origen (recuerda tu última elección)
2. Escribir monto y descripción
3. Seleccionar cuenta de destino (con recientes primero, o crear nueva)
4. Seleccionar categoría
5. Seleccionar presupuesto (opcional)
6. Agregar tags (opcional)
7. Confirmar el gasto

---

## 🚧 Roadmap personal

- [x] Estructura modular escalable
- [x] Registro de gastos y consultas por cuenta
- [x] Docker + `.env` seguro
- [x] Release automation vía GitHub Actions
- [x] Categorías, presupuestos y tags
- [x] Caché de cuentas y categorías
- [x] Confirmación antes de crear gastos
- [x] Destinos recientes
- [x] Autorización por usuario
- [x] Validación de variables de entorno
- [ ] Modo inline (@bot 13.99 hamburguesa)
- [ ] Plantillas de gastos recurrentes
- [ ] Conversión de monedas

---

## 📚 Documentación adicional

- [Changelog](./CHANGELOG.md): Historial completo de versiones y cambios importantes.

---

Hecho con ❤️ por [Rodrigo Aguilar](https://github.com/rodrigoaguilar96)
