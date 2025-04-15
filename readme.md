# Firefly III Telegram Bot

Este bot te permite interactuar con tu instancia de Firefly III directamente desde Telegram para consultar cuentas, ver movimientos y registrar gastos de forma simple y rápida.

## ✨ Características principales

- `/assets`: Lista todas las cuentas de tipo "asset" junto con su balance actual.
- `/expense <monto> "<descripcion>" <cuenta_origen> <cuenta_destino>`: Registra un gasto en Firefly.
  - Ejemplo: `/expense 11.12 "burger King" wise comida`
- `/cuenta <nombre> <N>`: Muestra el balance y los últimos N movimientos de la cuenta indicada.
  - Ejemplo: `/cuenta wise 5`

## 📂 Requisitos

- Python 3.10+
- Cuenta de Telegram con un bot creado en [@BotFather](https://t.me/BotFather)
- Instancia de Firefly III funcionando (puede estar en Docker)

## ♻️ Instalación

1. Cloná el repo:

```bash
git clone https://github.com/rodrigoaguilar96/fireflyiii-telegram-bot.git
cd fireflyiii-telegram-bot
```

2. Copiá y configurá tu archivo `.env`:

```env
TELEGRAM_BOT_TOKEN=tu_token_del_bot
FIREFLY_III_API_URL=http://firefly_iii_core:8080
FIREFLY_III_API_TOKEN=tu_token_personal_de_firefly
```

3. Levantá el bot con Docker:

```bash
docker compose up -d --build
```


## 🔐 Variables de entorno

| Variable               | Descripción                                    |
|------------------------|-----------------------------------------------|
| `TELEGRAM_BOT_TOKEN`   | Token del bot de Telegram                     |
| `FIREFLY_III_API_URL`  | URL de la API de Firefly III (puede ser local) |
| `FIREFLY_III_API_TOKEN`| Token de acceso personal generado en Firefly |


## 📝 Roadmap

- [x] Listar cuentas de tipo asset
- [x] Registrar gastos con descripción y cuentas
- [x] Consultar movimientos por cuenta
- [ ] Agregar botones interactivos (inline buttons)
- [ ] Comandos para ver presupuestos, etiquetas y categorías
- [ ] Exportar movimientos como CSV o PDF

---

Bot creado por [Rodrigo Aguilar](https://github.com/rodrigoaguilar96) con ayuda de ChatGPT.

❤️ Si este proyecto te resulta útil, no dudes en darle una estrella al repo.

