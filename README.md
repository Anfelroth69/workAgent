# WorkAgent

**Agente autónomo de scraping de ofertas laborales con IA, balanceo de APIs gratuitas y despliegue serverless.**

---

## ¿Qué hace?

WorkAgent es un agente basado en [Pico Claw](https://github.com/sipeed/picoclaw) que busca, clasifica y extrae ofertas de trabajo desde múltiples fuentes (portales de empleo, redes sociales, sitios corporativos). El agente utiliza modelos de lenguaje (LLMs) para:

- Navegar y extraer ofertas estructuradas
- Clasificar por seniority, tecnología, ubicación y salario
- Detectar duplicados y filtrar irrelevantes
- Entregar resultados consolidados vía Telegram, Discord o API REST

## Arquitectura

```
                    ┌──────────────┐
                    │  PostgreSQL  │
                    │  (Free Tier) │
                    └──────┬───────┘
                           │
┌── Internet ──▶  nginx ───┤
                   :3000   │
                    │      │
         ┌──────────┼──────┼──────────┐
         │          │      │          │
         ▼          ▼      │          ▼
   ┌──────────┐ ┌────────┐│   ┌──────────────┐
   │ One API  │ │ One API││   │ Pico Claw     │
   │ Admin UI │ │  REST  ││   │ Launcher      │
   │  :3001   │ │ :3001  ││   │   :18800      │
   └──────────┘ └───┬────┘│   └──────┬───────┘
                    │     │          │
                    ▼     │          │
           ┌──────────────────┐      │
           │   One API Core   │      │
           │  (balanceador)   │──────┘
           └────────┬─────────┘
                    │
          ┌─────────┼──────────┐
          ▼         ▼          ▼
     ┌────────┐ ┌────────┐ ┌────────┐
     │ OpenAI │ │DeepSeek│ │ Gemini │
     │ (gratis)│ │(gratis)│ │(gratis)│
     └────────┘ └────────┘ └────────┘
```

## Stack

| Componente | Propósito |
|---|---|
| **Pico Claw + Launcher** | Framework de agente con WebUI, gateway y gestión de skills |
| **One API** | Proxy unificado de LLMs con balanceo de carga y failover |
| **PostgreSQL** | Persistencia de datos (ofertas, configuraciones, logs) |
| **nginx** | Reverse proxy para enrutar tráfico entre servicios |
| **supervisord** | Orquestación de procesos dentro del contenedor |
| **Alpine Linux** | Imagen base mínima (~30 MB) |
| **Render** | Hosting serverless con Free Tier |

## Balanceo de APIs Gratuitas

One API administra múltiples claves de API gratuitas de distintos proveedores, rotando automáticamente cuando se excede la cuota:

```
┌────────────────────────────────────────────┐
│  Petición del agente                       │
│  └─▶ One API elige canal disponible        │
│      ├─▶ OpenAI (key1) → 429 rate limit?   │
│      │   └─▶ OpenAI (key2) → ¡ok!          │
│      ├─▶ DeepSeek (gratis) → cuota vacía?  │
│      │   └─▶ DeepSeek (key2) → ¡ok!        │
│      └─▶ Gemini (gratis) → ¡ok!            │
└────────────────────────────────────────────┘
```

One API soporta múltiples estrategias de balanceo: por prioridad, peso aleatorio, o failover automático ante errores HTTP 429/503.

## Despliegue

### Requisitos

- Cuenta en [Render](https://render.com) (Plan Free)
- Repositorio de GitHub conectado a Render
- Al menos una API key de algún proveedor de LLM

### 1-Click Deploy

Render detecta automáticamente el archivo [`render.yaml`](render.yaml) y provisiona:

1. Base de datos PostgreSQL (Free Tier)
2. Servicio Docker con la aplicación completa

### Variables de Entorno

| Variable | Descripción |
|---|---|
| `SQL_DSN` | Connection string de PostgreSQL (se asigna automáticamente) |
| `SESSION_SECRET` | Secreto de sesión para One API |
| `INITIAL_ROOT_TOKEN` | Token de administrador para primer login |
| `PICOCLAW_API_KEY` | Token de acceso para Pico Claw (se genera en One API) |
| `PICOCLAW_LAUNCHER_TOKEN` | Token para el WebUI del Launcher |
| `PORT` | Puerto público del contenedor (3000) |

### Desarrollo Local

```bash
docker compose up --build
```

Esto levanta PostgreSQL + la aplicación. Accede a `http://localhost:3000`.

## Post-Despliegue

1. Abrir `https://<tu-servicio>.onrender.com` e iniciar sesión con `INITIAL_ROOT_TOKEN`
2. En One API, ir a **Channels → Add Channel** y agregar APIs de LLM (OpenAI, DeepSeek, Gemini, etc.)
3. Ir a **Tokens → Add Token** y crear un token para Pico Claw
4. Actualizar `PICOCLAW_API_KEY` en las variables de entorno de Render
5. Re-desplegar
6. Acceder al WebUI de Pico Claw en `/picoclaw/` y configurar los agentes

## Comportamiento en Free Tier

Render Free Tier tiene las siguientes características:

- **Sleep**: el contenedor web duerme tras ~15 minutos sin actividad
- **Wake-up**: la primera petición después del sleep tarda 5-15 segundos
- **PostgreSQL**: los datos persisten incluso durante el sleep
- **PostgreSQL 90 días**: la base de datos gratuita se elimina si no recibe consultas en 90 días. Se recomienda [UptimeRobot](https://uptimerobot.com) para mantener actividad periódica.

## Licencia

MIT
