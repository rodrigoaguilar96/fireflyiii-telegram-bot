# 🚀 Releasing a New Version

Este documento explica cómo crear una nueva versión del proyecto **Firefly III Telegram Bot** usando GitHub Actions de forma segura y profesional.

---

## 🛠️ ¿Qué hace el proceso de release?

- Crea un Git Tag (`vX.Y.Z`) en el repositorio.
- Crea automáticamente un GitHub Release con notas descriptivas.
- Dispara el workflow de build y push de DockerHub:
  - Se genera una nueva imagen Docker taggeada con la versión (`v1.0.0`, `v1.1.0`, etc.).

---

## 🎯 Requisitos previos

- Estar en la rama `main`.
- Todo el código debe estar ya mergeado y probado.
- Los workflows de GitHub Actions deben estar configurados.

---

## 🧪 Proceso paso a paso

### 1. Ir a la pestaña **Actions** en GitHub.

### 2. Buscar el workflow llamado **Release Version**.

### 3. Click en **Run Workflow**.

### 4. Completar los siguientes campos:

| Campo | Descripción |
|:------|:------------|
| **Version to release** | Número de versión, siguiendo [SemVer](https://semver.org/). Ej: `v1.0.0` |
| **Release notes (changelog)** | Breve resumen de cambios o mejoras introducidas en esta versión. Ej: `Primera versión estable: agrega registro de gastos y visualización de cuentas.` |

### 5. Confirmar la ejecución.

---

## 📦 Resultado

- Un nuevo **Git Tag** creado (`vX.Y.Z`).
- Un nuevo **GitHub Release** visible en la pestaña **Releases** del repositorio.
- Una nueva **imagen Docker** publicada en DockerHub:
  - Nombre: `rja96/fireflyiii-telegram-bot:vX.Y.Z`

---

## 🛡️ Buenas prácticas para releases

Utilizamos [SemVer (Semantic Versioning)](https://semver.org/) para numerar las versiones de este proyecto:

| Parte | Qué indica | Ejemplo práctico |
|:------|:-----------|:-----------------|
| **MAJOR** (X.0.0) | Cambios incompatibles o que rompen el uso existente del bot. | Cambiar completamente el flujo de comandos `/expense`. |
| **MINOR** (0.X.0) | Nuevas funcionalidades compatibles con versiones anteriores. | Agregar un nuevo comando como `/budget` para presupuestos. |
| **PATCH** (0.0.X) | Correcciones de errores o mejoras menores que no cambian funcionalidades. | Arreglar un bug en la validación del monto de `/expense`. |

### Regla rápida:

- Si **rompés** compatibilidad: subí el **MAJOR**.
- Si **agregás** funciones compatibles: subí el **MINOR**.
- Si **corregís** bugs o detalles: subí el **PATCH**.


---

# 🎉 ¡Listo!

Con este proceso, el proyecto queda versionado, documentado y con entregables automáticos tanto en GitHub como en DockerHub.