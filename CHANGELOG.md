# 📋 Changelog

Todas las versiones publicadas de **Firefly III Telegram Bot**.

Seguimos el esquema [SemVer](https://semver.org/): `MAJOR.MINOR.PATCH`.

---

## [v1.0.3] - 2025-04-26

🚀 **Actualización de flujo de release y despliegue.**

- Corrección definitiva en la propagación de versiones durante releases automáticos.
- Publicación de imágenes multi-arquitectura (`amd64`, `arm64`) correctamente versionadas.
- Actualización automática del tag `latest` al publicar una nueva versión.

🔔 Esta versión no introduce cambios funcionales en el bot.

---

## [v1.0.2] - 2025-04-26

🚀 **Actualización técnica de infraestructura.**

- Soporte completo para multi-arquitectura (`linux/amd64` y `linux/arm64`).
- Automatización total del flujo de releases: Tag + Release + Build + Push.
- Corrección en triggers automáticos de workflows.

🔔 No cambios funcionales en esta versión.

---

## [v1.0.1] - 2025-04-26

🔧 **Corrección inicial de workflows de build y releases.**

- Mejoras en automatización de despliegues de imágenes Docker.
- Ajustes menores en la estructura de CI/CD.

---

## [v1.0.0] - 2025-04-26

🎉 **Primera versión estable del proyecto.**

- Menú interactivo en Telegram para registrar gastos y consultar cuentas (usá /menu para abrirlo).
- Comando `/assets` para listar cuentas de tipo "asset".
- Comando `/expense` para registrar gastos manualmente.
- Flujo de creación de gastos paso a paso con botones.
- Comando `/cuenta` para ver últimos movimientos de una cuenta.
- Configuración segura mediante archivo `.env`.
- Dockerfile optimizado y publicación en DockerHub.

---

# 📅 Formato

- `[vX.Y.Z]` ➔ Indica la versión liberada.
- La fecha corresponde a la fecha de publicación oficial.

---

Hecho con ❤️ por [Rodrigo Aguilar](https://github.com/rodrigoaguilar96)