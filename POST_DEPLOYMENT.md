# Guía de Configuración Post-Despliegue

## 1. Verificar el despliegue en Render

En el Dashboard de Render:
- [ ] El servicio `one-api-picoclaw` aparece como **Live**
- [ ] La base de datos `one-api-db` aparece como **Available**
- [ ] No hay errores en la pestaña **Logs** del servicio

## 2. Acceder al panel web de One API

Abre la URL pública de tu servicio en Render:

```
https://one-api-picoclaw.onrender.com
```

(el subdominio exacto aparece en el Dashboard de Render)

## 3. Primer login

- Usa el `INITIAL_ROOT_TOKEN` que configuraste en las variables de entorno
- Ve a **Settings > Change Root Password** y cambia la contraseña por seguridad

## 4. Configurar canales de proveedores de IA

Ve a **Channels > Add Channel** y agrega tus proveedores:

| Proveedor | Tipo en One API | Modelo(s) a configurar |
|---|---|---|
| OpenAI | OpenAI | gpt-4o-mini, gpt-4, gpt-4-turbo |
| Anthropic | Claude | claude-3-opus, claude-3-sonnet |
| Google | Gemini | gemini-pro, gemini-1.5-pro |
| DeepSeek | DeepSeek | deepseek-chat |

### Para activar el balanceo con fallback por rate limit:

Agrega **múltiples API Keys** en un mismo canal (separadas por nueva línea) y configura:

- **Models**: los modelos que soporta este canal
- **Group**: `default`
- **Priority**: `1` (a mayor prioridad, preferencia de ruteo)

Si un proveedor retorna 429 (rate limit), One API redirige automáticamente al siguiente canal disponible.

## 5. Verificar el balanceo automático

Para probar, crea al menos 2 canales del mismo tipo (ej: dos canales OpenAI) con keys diferentes:

```
Channel 1: OpenAI, key=sk-xxx1, models=gpt-4o-mini, priority=1
Channel 2: OpenAI, key=sk-xxx2, models=gpt-4o-mini, priority=1
```

Cuando el primer canal retorne rate limit (429), One API retry automáticamente en el segundo.

## 6. Generar token de acceso para Pico Claw

1. En One API, ve a **Tokens > Add Token**
2. Crea un token con:
   - **Name**: `picoclaw`
   - **Models**: el/los modelos que usarás
   - **Expiration**: sin expiración
3. Copia el token generado
4. En el Dashboard de Render, actualiza las variables:
   - `PICOCLAW_API_KEY` con el token que acabas de generar
   - `PICOCLAW_LAUNCHER_TOKEN` con un token seguro para acceder al WebUI de Pico Claw
5. Ve a **Manual Deploy > Deploy latest commit** para reiniciar con las nuevas keys

## 7. Acceder al dashboard WebUI de Pico Claw

El launcher de Pico Claw está disponible en la ruta `/picoclaw/` de tu servicio:

```
https://one-api-picoclaw.onrender.com/picoclaw/
```

Usa el token `PICOCLAW_LAUNCHER_TOKEN` que configuraste en las variables de entorno para iniciar sesión.

Desde el WebUI puedes:
- Ver y editar la configuración de modelos (todos apuntan a One API por `localhost:3000/v1`)
- Configurar canales (Telegram, Discord, etc.)
- Gestionar skills y herramientas
- Monitorear el estado del agente

## 8. Verificar que Pico Claw consume One API

Revisa los logs en el Dashboard de Render. Deberías ver algo como:

```
[picoclaw-launcher] started on :18800
[picoclaw-launcher] gateway started on :18790
```

Pico Claw Launcher ya incluye el gateway y usa One API automáticamente vía `localhost:3000/v1`. La configuración se gestiona desde el WebUI en `/picoclaw/`.

## 9. Workaround: mantener PostgreSQL activo (90 días)

Render elimina las bases de datos Free Tier tras **90 días sin actividad**. Para evitar esto:

### Opción 1: UptimeRobot (recomendado, gratuito)

1. Crea una cuenta en https://uptimerobot.com
2. Agrega un monitor **HTTP** apuntando a:
   ```
   https://one-api-picoclaw.onrender.com/api/status
   ```
3. Intervalo: **5 minutos**
4. Esto mantiene el web service activo y PostgreSQL recibe consultas periódicamente

### Opción 2: Cron mensual manual

Marca un recordatorio en tu calendario para hacer login a One API al menos una vez al mes.

## 10. Comportamiento del Sleep Mode

Render Free Tier duerme el **web service** tras ~15 minutos de inactividad:

| Evento | ¿Datos Persisten? | Tiempo de wake-up |
|---|---|---|
| Sleep (inactividad 15min) | ✅ Sí (PostgreSQL) | 5-15 segundos |
| Wake-up (nueva petición) | ✅ Sí (PostgreSQL) | 5-15 segundos |
| Redeploy manual | ✅ Sí (PostgreSQL) | 30-60 segundos |
| Crash + restart | ✅ Sí (PostgreSQL) | 10-30 segundos |

La **primera petición** tras un sleep puede tardar unos segundos extra mientras el contenedor despierta. Las peticiones subsiguientes serán normales.

---

## Checklist de Verificación Final

- [ ] One API accesible vía URL pública de Render
- [ ] Login funciona con el token inicial
- [ ] Al menos un canal de IA configurado con una API key válida
- [ ] Token de Pico Claw generado en One API
- [ ] Variable `PICOCLAW_API_KEY` actualizada en Render con el token
- [ ] WebUI de Pico Claw accesible en `/picoclaw/`
- [ ] Token `PICOCLAW_LAUNCHER_TOKEN` configurado y funciona en el WebUI
- [ ] Logs muestran que One API y Pico Claw iniciaron correctamente
- [ ] Health check `/api/status` responde 200
- [ ] PostgreSQL mantiene datos tras un redeploy forzado
