# ⚡ State Panel

> Un panel de estado ultraligero, desacoplado y elegante para servicios en VPS (**Hermes, CRM, Outline**) y plataformas Cloud (**Cloud Run, Supabase, BigQuery**), con visualización dual (**CLI Rich en terminal y Web estática en Cloudflare Pages**) y alertas Pub/Sub vía **ntfy**.

---

## 📸 Características

- **Diseño Dark Minimalista**: Inspirado en el status page de Anthropic con línea de tiempo interactiva de 30 días, tooltips detallados y porcentaje de uptime.
- **Doble Interfaz**:
  - **CLI en Terminal**: Tablas con colores, métricas y latencias renderizadas con `rich` y `typer`.
  - **Web Estática**: Interfaz moderna en `Vue 3 + Vite + Tailwind CSS` alojable en **Cloudflare Pages** por $0/mes.
- **Desacoplado y Resiliente**: El panel se aloja en Cloudflare Pages, por lo que sigue accesible incluso si el VPS cae por completo.
- **Alertas Pub/Sub con `ntfy`**: Notificaciones automáticas a topics de `ntfy.sh` (o autoalojado) con soporte para apps móviles (iOS/Android), webhooks o scripts.
- **Gestor de Calidad y Pre-commits**:
  - `commitizen` (Conventional Commits)
  - `ruff v0.16.4` (Linter & Formatter)
  - `ty v0.0.74` (Type Checker ultrarrápido)
  - `detect-secrets` (Seguridad de credenciales)

---

## 🚀 Inicio Rápido

### 1. Instalación de Dependencias (Python & Node)

```bash
# Instalar dependencias de Python con uv
uv sync

# Instalar dependencias del frontend web con pnpm
cd web && pnpm install && cd ..
```

### 2. Configurar Servicios (`services.yaml`)

Edita el archivo `services.yaml` para apuntar a tus servicios reales:

```yaml
settings:
  title: "System Status"
  description: "Live operational status of VPS and Cloud infrastructure"
  history_days: 30
  output_dir: "web/public/data"

ntfy:
  enabled: true
  server: "https://ntfy.sh"
  topic: "my-vps-status-alerts" # Tu topic privado de ntfy
  priority: 4

services:
  - id: "hermes"
    name: "Hermes"
    category: "VPS Core"
    type: "http"
    target: "https://hermes.midominio.com/health"
    expected_status: 200

  - id: "crm"
    name: "CRM"
    category: "VPS Core"
    type: "http"
    target: "https://crm.midominio.com"
    expected_status: 200

  - id: "outline"
    name: "Outline"
    category: "VPS Core"
    type: "http"
    target: "https://outline.midominio.com/api/health"
    expected_status: 200
```

---

## 🖥️ Uso del CLI

```bash
# 1. Ejecutar chequeo instantáneo de servicios
uv run state-panel check

# 2. Ver historial agregado de uptime (últimos 30 días)
uv run state-panel history --days 30

# 3. Iniciar servidor web local con API en tiempo real y UI interactiva
uv run state-panel serve --port 8000

# 4. Generar datos y exportar a web/public/data/status.json para Cloudflare Pages
uv run state-panel export

# 5. Reiniciar base de datos a estado limpio con chequeo real
uv run state-panel reset

# 6. Iniciar daemon en segundo plano (chequeo periódico sin servidor web)
uv run state-panel daemon
```

---

---

## 🌐 Desarrollo y Despliegue en Cloudflare Pages

### 1. Desarrollo Local con Vite y Servidor en Vivo

```bash
# Iniciar backend y API en vivo (puerto 8000)
uv run state-panel serve --port 8000

# En otra terminal: Iniciar frontend Vue con hot-reload (puerto 5173)
cd web && pnpm dev
```

### 2. Despliegue a Cloudflare Pages

El sitio web es **100% estático** y se despliega en **Cloudflare Pages** (`startup-services-health`):

#### Opción A: Despliegue Directo con la CLI de State Panel (Recomendado)
```bash
# Ejecuta chequeos, compila con Bun y despliega a Cloudflare Pages
uv run state-panel deploy --project-name startup-services-health
```

#### Opción B: Despliegue Manual con Bun y Wrangler
```bash
# Exportar datos más recientes
uv run state-panel export

# Compilar frontend con Bun
cd web && bun run build && cd ..

# Desplegar a Cloudflare Pages
bunx wrangler pages deploy web/dist --project-name=startup-services-health
```

---

## 🔐 Seguridad y Gestión de Secretos

- **Variables de Entorno**: El archivo `services.yaml` soporta interpolación dinámica `${VAR:-default}`.
- **Archivo `.env`**: Puedes copiar `.env.example` a `.env` para almacenar endpoints privados o tokens sin subirlos a Git (`.env` está ignorado en `.gitignore`).
- **Auditoría de Seguridad**: El proyecto incluye `detect-secrets` y `pnpm audit` para evitar fuga de credenciales y dependencias vulnerables.

---

## 🔒 Pre-commits y Convención de Commits

```bash
# Instalar hooks de git
uv run pre-commit install --install-hooks

# Ejecutar validación sobre todos los archivos
uv run pre-commit run --all-files

# Realizar un commit guiado con Conventional Commits
uv run cz commit
```
