# 🤖 Bot P2P Binance - Versión Completa de Despliegue

## 📋 Descripción
Bot de arbitraje para el mercado P2P de Binance con interfaz web completa, análisis automático cada 30 segundos, notificaciones de Telegram y monitoreo especializado de Pago Móvil.

## ✨ Características Principales

### 🔄 Análisis Automático
- **Análisis cada 30 segundos** del mercado completo
- **Detección de oportunidades** de arbitraje ≥1.20%
- **Monitor de spread** en tiempo real con alertas inteligentes

### 📱 Notificaciones Telegram
- **Alertas automáticas** cuando spread ≥1.20%
- **Sistema anti-spam** (15 min mínimo entre alertas)
- **Alertas por aumento** si porcentaje sube >0.5%

### 💰 Análisis Pago Móvil Especializado
- **Monitor específico** para transacciones de 1000 VES
- **Comparación inteligente** vendedores Pago Móvil vs compradores TOP
- **Alertas cuando diferencia >3.5%** (arbitraje especializado)

### 🖥️ Interfaz Web Completa
- **Dashboard en tiempo real** con métricas actualizadas
- **Calculadora de precios** con márgenes configurables
- **Monitor de mercado** con datos de 20+ comerciantes verificados
- **Logs en tiempo real** con código de colores

## 📦 Instalación

### Requisitos
```bash
pip install flask requests
```

### Ejecución Local
```bash
python web_interface_simple.py
```

### Acceso
- **Local**: http://localhost:5000
- **Producción**: Configurado para 0.0.0.0:5000

## 🚀 Despliegue

### Archivos de Despliegue Incluidos
- `Procfile` - Configuración para Heroku/Railway
- `runtime.txt` - Versión de Python
- `app.yaml` - Configuración para Google Cloud Run
- `pyproject.toml` - Dependencias del proyecto

### Health Check Endpoints
- `/health` - Estado general del servicio
- `/healthz` - Check estilo Kubernetes
- `/ready` - Verificación de disponibilidad
- `/api/logs` - Logs del sistema

## ⚙️ Configuración

### API de Binance
1. Ingresa tu **API Key** y **API Secret** en la interfaz web
2. El bot probará múltiples endpoints automáticamente
3. Función "Probar Conexión" incluida

### Bot de Telegram
1. Crea un bot con @BotFather
2. Obtén el **Bot Token** y **Chat ID**
3. Configura en la sección "Notificaciones Telegram"

## 📊 Datos en Tiempo Real

### Métricas Actuales
- **Spread promedio**: ~0.85% (considerar operar)
- **Precio sugerido**: ~160.20 VES
- **Margen real**: ~3.00%
- **Diferencia Pago Móvil**: ~2.55%

### Análisis Completo
- **Compradores TOP**: ~165.69 VES
- **Vendedores promedio**: ~164.30 VES
- **20+ comerciantes** verificados monitoreados

## 🛡️ Características de Seguridad
- **Sistema anti-restricción geográfica**
- **Múltiples endpoints** para evadir bloqueos
- **Credenciales encriptadas** (no se muestran en logs)
- **Rate limiting** automático

## 📈 Sistema de Alertas

### Niveles de Spread
- 🔴 **<0.80%**: No recomendable operar
- 🟠 **0.81%-1.19%**: Considerar operar
- 🟢 **≥1.20%**: Excelente oportunidad + Alerta automática

### Pago Móvil
- 🚨 **>3.5%**: Oportunidad de arbitraje especializado
- 📱 **1000 VES**: Límite específico para análisis

## 🔧 Estructura del Proyecto
```
BinanceP2PBot_Final_Deployment/
├── web_interface_simple.py    # Aplicación principal
├── templates/
│   └── index.html            # Template de la interfaz
├── Procfile                  # Config de despliegue
├── runtime.txt              # Versión Python
├── app.yaml                 # Config Cloud Run
├── pyproject.toml           # Dependencias
└── README.md               # Este archivo
```

## 🎯 Estado del Proyecto
✅ **LISTO PARA DESPLIEGUE**
- Interfaz completa funcionando
- Análisis automático operativo
- Sistema de alertas configurado
- Health checks pasando
- Documentación completa

---
**Versión**: Final de Despliegue - 22 Julio 2025
**Estado**: ✅ Totalmente funcional y listo para producción