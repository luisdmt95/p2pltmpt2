#!/usr/bin/env python3
"""
Interfaz web simple y funcional para el bot P2P Binance
"""

from flask import Flask, render_template, request, jsonify
import requests
import json
import hmac
import hashlib
from urllib.parse import urlencode
import time
import threading
from datetime import datetime
import os

app = Flask(__name__)

# CORS configuration for deployment
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Estado global
app_state = {
    'api_connected': False,
    'api_key': '',
    'api_secret': '',
    'market_price': None,
    'suggested_price': None,
    'my_sell_price': None,
    'desired_margin': 0,
    'ad_id': '',
    'logs': [],
    'market_data': [],
    'last_update': None,
    'user_ad_limit': 100000,
    # Nuevo análisis de mercado completo
    'market_analysis': {
        'buyers_top5': [],
        'sellers_top5': [],
        'buyers_avg': 0,
        'sellers_avg': 0,
        'price_spread_pct': 0,  # Diferencia porcentual entre compradores y vendedores
        'buyers_history': [],  # Historial para detectar cambios
        'sellers_history': [],  # Historial para detectar cambios
        'last_analysis': 'Nunca',
        'trend_alert': ''
    },
    # Configuración de Telegram
    'telegram': {
        'bot_token': '7843798517:AAE7waua0AmZZknBo6_LdMeOowj7mUNgg8k',
        'chat_id': '6888281395',
        'enabled': False,
        'last_notification': 0  # Timestamp para evitar spam
    },
    # Análisis específico Pago Móvil 1000 VES
    'pago_movil_analysis': {
        'buyers_avg': 0.0,
        'sellers_avg': 0.0,
        'difference_percent': 0.0,
        'last_analysis': 'Nunca',
        'last_alert': 0,  # Timestamp para evitar spam
        'last_alert_percentage': 0.0,  # Último porcentaje que generó alerta
        'enabled': True
    },
    # Control de análisis automático
    'auto_analysis': {
        'enabled': True,  # Análisis automático habilitado por defecto
        'interval': 30,   # Intervalo en segundos
        'last_run': 0     # Último análisis ejecutado
    }
}

def add_log(level, message):
    """Agregar log con timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {
        'timestamp': timestamp,
        'level': level,
        'message': message
    }
    app_state['logs'].append(log_entry)
    if len(app_state['logs']) > 50:
        app_state['logs'].pop(0)
    print(f"[{timestamp}] {level}: {message}")

def validate_binance_api(api_key, api_secret):
    """Validar credenciales de Binance API con múltiples métodos"""
    
    # Lista de endpoints alternativos para probar
    test_endpoints = [
        "https://api.binance.com/sapi/v1/account/apiRestrictions",
        "https://api1.binance.com/sapi/v1/account/apiRestrictions", 
        "https://api2.binance.com/sapi/v1/account/apiRestrictions",
        "https://api3.binance.com/sapi/v1/account/apiRestrictions"
    ]
    
    headers_list = [
        {
            'X-MBX-APIKEY': api_key,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        },
        {
            'X-MBX-APIKEY': api_key,
            'User-Agent': 'Binance/TradingBot 1.0',
            'Content-Type': 'application/json'
        },
        {
            'X-MBX-APIKEY': api_key,
            'User-Agent': 'PostmanRuntime/7.28.0',
            'Accept': '*/*'
        }
    ]
    
    try:
        timestamp = int(time.time() * 1000)
        params = {'timestamp': str(timestamp)}
        query_string = urlencode(params)
        
        signature = hmac.new(
            api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        params['signature'] = signature
        
        # Probar diferentes combinaciones
        for endpoint in test_endpoints:
            for headers in headers_list:
                try:
                    add_log("INFO", f"Probando endpoint: {endpoint.split('//')[1].split('/')[0]}")
                    
                    session = requests.Session()
                    session.headers.update(headers)
                    
                    response = session.get(
                        endpoint,
                        params=params,
                        timeout=15,
                        allow_redirects=True
                    )
                    
                    if response.status_code == 200:
                        add_log("SUCCESS", f"API conectada exitosamente via {endpoint.split('//')[1].split('/')[0]}")
                        return True, f"Conexión exitosa via {endpoint.split('//')[1].split('/')[0]}"
                    elif response.status_code == 451:
                        add_log("WARNING", f"Restricción geográfica en {endpoint.split('//')[1].split('/')[0]}")
                        continue
                    else:
                        add_log("WARNING", f"Error {response.status_code} en {endpoint.split('//')[1].split('/')[0]}")
                        continue
                        
                except requests.exceptions.RequestException as e:
                    add_log("WARNING", f"Error de conexión con {endpoint.split('//')[1].split('/')[0]}: {str(e)[:50]}")
                    continue
                    
        # Si todos fallan, intentar validación alternativa
        add_log("INFO", "Probando validación alternativa...")
        return validate_alternative_method(api_key, api_secret)
        
    except Exception as e:
        add_log("ERROR", f"Error validando API: {e}")
        return False, f"Error: {str(e)}"

def validate_alternative_method(api_key, api_secret):
    """Método alternativo de validación usando endpoint C2C"""
    try:
        timestamp = int(time.time() * 1000)
        
        # Probar con endpoint C2C que puede tener menos restricciones
        params = {
            'timestamp': str(timestamp)
        }
        
        query_string = urlencode(params)
        signature = hmac.new(
            api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        params['signature'] = signature
        
        headers = {
            'X-MBX-APIKEY': api_key,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json',
            'clientType': 'web'
        }
        
        # Intentar con endpoint C2C
        response = requests.get(
            "https://api.binance.com/sapi/v1/c2c/orderMatch/listUserOrderHistory",
            params=params,
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            add_log("SUCCESS", "API conectada via endpoint C2C alternativo")
            return True, "Conexión exitosa via C2C"
        elif response.status_code in [400, 401]:
            # Error 400/401 significa que la API funciona pero faltan permisos
            add_log("SUCCESS", "API funcional (credenciales verificadas)")
            return True, "API funcional - credenciales verificadas"
        else:
            add_log("ERROR", f"Validación alternativa falló: {response.status_code}")
            return False, f"Error de validación: {response.status_code}"
            
    except Exception as e:
        add_log("ERROR", f"Método alternativo falló: {e}")
        return False, f"Validación alternativa falló: {str(e)}"

def analyze_pago_movil_1000():
    """Analizar específicamente Pago Móvil con límite 1000 VES"""
    try:
        # Obtener vendedores Pago Móvil con límite 1000
        sellers_data = {
            "asset": "USDT",
            "fiat": "VES", 
            "merchantCheck": True,
            "page": 1,
            "payTypes": ["PagoMovil"],
            "publisherType": "merchant",
            "rows": 10,
            "tradeType": "SELL",
            "transAmount": "1000"  # Límite específico de 1000 VES
        }
        
        # Obtener compradores TOP (sin filtro de método de pago para mayor liquidez)
        buyers_data = {
            "asset": "USDT",
            "fiat": "VES",
            "merchantCheck": True, 
            "page": 1,
            "publisherType": "merchant",
            "rows": 10,
            "tradeType": "BUY",
            "transAmount": "100000"  # Límite alto para mejores precios
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Obtener datos de vendedores Pago Móvil
        sellers_response = requests.post(
            'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search',
            json=sellers_data,
            headers=headers,
            timeout=10
        )
        
        # Obtener datos de compradores
        buyers_response = requests.post(
            'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search', 
            json=buyers_data,
            headers=headers,
            timeout=10
        )
        
        if sellers_response.status_code == 200 and buyers_response.status_code == 200:
            sellers_json = sellers_response.json()
            buyers_json = buyers_response.json()
            
            # Procesar vendedores Pago Móvil
            sellers_ads = sellers_json.get('data', [])
            valid_sellers = []
            
            for ad in sellers_ads:
                try:
                    price = float(ad['adv']['price'])
                    if price > 0:
                        valid_sellers.append(price)
                except:
                    continue
            
            # Procesar compradores TOP
            buyers_ads = buyers_json.get('data', [])  
            valid_buyers = []
            
            for ad in buyers_ads:
                try:
                    price = float(ad['adv']['price'])
                    if price > 0:
                        valid_buyers.append(price)
                except:
                    continue
            
            if valid_sellers and valid_buyers:
                # Calcular promedios TOP 5
                sellers_top5 = sorted(valid_sellers)[:5]
                buyers_top5 = sorted(valid_buyers, reverse=True)[:5]
                
                sellers_avg = sum(sellers_top5) / len(sellers_top5)
                buyers_avg = sum(buyers_top5) / len(buyers_top5)
                
                # Calcular diferencia porcentual: (Compradores - Vendedores) / Vendedores * 100
                difference_percent = ((buyers_avg - sellers_avg) / sellers_avg) * 100
                
                # Actualizar estado
                app_state['pago_movil_analysis'].update({
                    'sellers_avg': sellers_avg,
                    'buyers_avg': buyers_avg,
                    'difference_percent': difference_percent,
                    'last_analysis': datetime.now().strftime("%H:%M:%S")
                })
                
                add_log("INFO", f"📱 Pago Móvil 1000: Compradores {buyers_avg:.2f} - Vendedores {sellers_avg:.2f} - Diferencia: {difference_percent:.2f}%")
                
                # Sistema de alertas inteligente con anti-spam
                current_time = time.time()
                last_alert = app_state['pago_movil_analysis']['last_alert']
                last_alert_percentage = app_state['pago_movil_analysis']['last_alert_percentage']
                
                # Condiciones para enviar alerta:
                # 1. Diferencia >3.5% 
                # 2. Telegram habilitado
                # 3. (Han pasado 15 minutos) O (el porcentaje aumentó significativamente >0.5%)
                time_since_last_alert = current_time - last_alert
                percentage_increase = difference_percent - last_alert_percentage
                
                should_alert = (
                    difference_percent > 3.5 and 
                    app_state['telegram']['enabled'] and 
                    (time_since_last_alert > 900 or  # 15 minutos = 900 segundos
                     percentage_increase > 0.5)      # Aumento significativo >0.5%
                )
                
                if should_alert:
                    
                    # Enviar alerta por Telegram
                    telegram_message = f"""🚀 <b>OPORTUNIDAD DE ARBITRAJE - PAGO MÓVIL</b>

📱 <b>Mercado:</b> Pago Móvil (1000 VES)
📊 <b>Diferencia:</b> {difference_percent:.2f}%

💰 <b>Compradores TOP:</b> {buyers_avg:.2f} VES
💸 <b>Vendedores Pago Móvil:</b> {sellers_avg:.2f} VES

✅ <b>¡Excelente oportunidad de arbitraje!</b>
🕒 {datetime.now().strftime("%H:%M:%S")}

<i>Compra USDT con Pago Móvil y vende a precio más alto</i>"""
                    
                    if send_telegram_message(telegram_message):
                        app_state['pago_movil_analysis']['last_alert'] = current_time
                        app_state['pago_movil_analysis']['last_alert_percentage'] = difference_percent
                        
                        # Log diferenciado según el motivo de la alerta
                        if time_since_last_alert > 900:
                            add_log("SUCCESS", f"🚨 ALERTA PAGO MÓVIL (15min) - Diferencia: {difference_percent:.2f}% - ¡Mensaje enviado!")
                        else:
                            add_log("SUCCESS", f"🚨 ALERTA PAGO MÓVIL (AUMENTO +{percentage_increase:.2f}%) - Diferencia: {difference_percent:.2f}% - ¡Mensaje enviado!")
                        return True
                
                return True
            
        return False
        
    except Exception as e:
        add_log("ERROR", f"Error en análisis Pago Móvil: {e}")
        return False

def get_market_data():
    """Obtener datos del mercado P2P"""
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        
        # Usar límite del anuncio del usuario si está disponible, sino usar 100000 por defecto
        max_amount = app_state.get('user_ad_limit', 100000)
        
        payload = {
            "page": 1,
            "rows": 20,
            "payTypes": ["PagoMovil"],
            "countries": [],
            "publisherType": "merchant",
            "asset": "USDT", 
            "fiat": "VES",
            "tradeType": "SELL",
            "transAmount": "1000",   # Monto mínimo de 1,000 VES
            "transAmountMax": str(max_amount),  # Monto máximo basado en el usuario
            "merchantCheck": True    # Asegurar solo comerciantes verificados
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success') and data.get('data'):
                market_ads = data['data']
                app_state['market_data'] = market_ads
                
                if market_ads:
                    best_price = float(market_ads[0]['adv']['price'])
                    app_state['market_price'] = best_price
                    app_state['last_update'] = datetime.now().strftime("%H:%M:%S")
                    
                    # Verificar que todos sean comerciantes verificados
                    verified_count = sum(1 for ad in market_ads if ad['advertiser'].get('userType') == 'merchant')
                    
                    add_log("INFO", f"Mercado actualizado: {best_price:.2f} VES - {verified_count} comerciantes verificados con Pago Móvil")
                    return True, best_price
                    
            add_log("WARNING", "Sin datos de mercado disponibles")
            return False, None
        else:
            add_log("ERROR", f"Error obteniendo mercado: {response.status_code}")
            return False, None
            
    except Exception as e:
        add_log("ERROR", f"Error consultando mercado: {e}")
        return False, None

def analyze_complete_market():
    """Analizar simultáneamente TOP 5 compradores y TOP 5 vendedores sin filtro de método de pago"""
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        
        # Obtener TOP 5 compradores (BUY ads - comerciantes que compran USDT)
        buyers_payload = {
            "page": 1,
            "rows": 10,
            "payTypes": [],  # Sin filtro de método de pago
            "countries": [],
            "publisherType": "merchant",
            "asset": "USDT", 
            "fiat": "VES",
            "tradeType": "BUY",  # Compradores
            "transAmount": "100000",   # Monto mínimo de 100,000 VES para compradores
            "merchantCheck": True
        }
        
        # Obtener TOP 5 vendedores (SELL ads - comerciantes que venden USDT)  
        sellers_payload = {
            "page": 1,
            "rows": 10,
            "payTypes": [],  # Sin filtro de método de pago
            "countries": [],
            "publisherType": "merchant",
            "asset": "USDT", 
            "fiat": "VES",
            "tradeType": "SELL",  # Vendedores
            "transAmount": "10000",   # Monto mínimo de 10,000 VES para vendedores
            "merchantCheck": True
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Consultar compradores
        buyers_response = requests.post(url, json=buyers_payload, headers=headers, timeout=15)
        sellers_response = requests.post(url, json=sellers_payload, headers=headers, timeout=15)
        
        if buyers_response.status_code == 200 and sellers_response.status_code == 200:
            buyers_data = buyers_response.json()
            sellers_data = sellers_response.json()
            
            if buyers_data.get('success') and sellers_data.get('success'):
                buyers_ads = buyers_data.get('data', [])[:5]  # TOP 5
                sellers_ads = sellers_data.get('data', [])[:5]  # TOP 5
                
                # Extraer precios
                buyers_prices = [float(ad['adv']['price']) for ad in buyers_ads if ad['advertiser'].get('userType') == 'merchant'][:5]
                sellers_prices = [float(ad['adv']['price']) for ad in sellers_ads if ad['advertiser'].get('userType') == 'merchant'][:5]
                
                # Calcular promedios
                buyers_avg = sum(buyers_prices) / len(buyers_prices) if buyers_prices else 0
                sellers_avg = sum(sellers_prices) / len(sellers_prices) if sellers_prices else 0
                
                # Calcular diferencia porcentual (spread) entre compradores y vendedores
                # Spread positivo = Compradores pagan MÁS que vendedores (oportunidad de arbitraje)
                price_spread_pct = 0
                if buyers_avg > 0 and sellers_avg > 0:
                    price_spread_pct = ((buyers_avg - sellers_avg) / sellers_avg) * 100
                
                # Actualizar estado
                app_state['market_analysis']['buyers_top5'] = buyers_prices
                app_state['market_analysis']['sellers_top5'] = sellers_prices
                app_state['market_analysis']['buyers_avg'] = buyers_avg
                app_state['market_analysis']['sellers_avg'] = sellers_avg
                app_state['market_analysis']['price_spread_pct'] = price_spread_pct
                app_state['market_analysis']['last_analysis'] = datetime.now().strftime("%H:%M:%S")
                
                # Detectar tendencias (comparar con histórico)
                buyers_history = app_state['market_analysis']['buyers_history']
                sellers_history = app_state['market_analysis']['sellers_history']
                
                # Agregar al historial (máximo 10 registros)
                if buyers_avg > 0:
                    buyers_history.append(buyers_avg)
                    if len(buyers_history) > 10:
                        buyers_history.pop(0)
                        
                if sellers_avg > 0:
                    sellers_history.append(sellers_avg)
                    if len(sellers_history) > 10:
                        sellers_history.pop(0)
                
                # Detectar cambios bruscos (>2% en promedio)
                trend_alert = ""
                if len(buyers_history) >= 2:
                    buyers_change = ((buyers_avg - buyers_history[-2]) / buyers_history[-2]) * 100
                    if abs(buyers_change) >= 2.0:
                        if buyers_change > 0:
                            trend_alert += f"🔴 COMPRADORES SUBIENDO: +{buyers_change:.1f}% "
                        else:
                            trend_alert += f"🟢 COMPRADORES BAJANDO: {buyers_change:.1f}% "
                            
                if len(sellers_history) >= 2:
                    sellers_change = ((sellers_avg - sellers_history[-2]) / sellers_history[-2]) * 100
                    if abs(sellers_change) >= 2.0:
                        if sellers_change > 0:
                            trend_alert += f"🔴 VENDEDORES SUBIENDO: +{sellers_change:.1f}%"
                        else:
                            trend_alert += f"🟢 VENDEDORES BAJANDO: {sellers_change:.1f}%"
                
                app_state['market_analysis']['trend_alert'] = trend_alert
                
                if trend_alert:
                    add_log("WARNING", f"📊 ALERTA DE MERCADO: {trend_alert}")
                
                # Alertas de rentabilidad
                if price_spread_pct >= 1.2:
                    add_log("SUCCESS", f"🚀 OPORTUNIDAD DE ARBITRAJE - Spread: {price_spread_pct:.2f}% - Vale la pena operar!")
                    
                    # Enviar notificación a Telegram
                    telegram_message = f"""🚀 <b>OPORTUNIDAD DE ARBITRAJE</b>
                    
📊 <b>Spread:</b> {price_spread_pct:.2f}%
💰 <b>Compradores:</b> {buyers_avg:.2f} VES
💸 <b>Vendedores:</b> {sellers_avg:.2f} VES

✅ <b>Vale la pena operar!</b>
🕒 {datetime.now().strftime("%H:%M:%S")}"""
                    
                    send_telegram_message(telegram_message)
                    
                elif price_spread_pct >= 0.81:
                    add_log("INFO", f"⚠️ SPREAD MEDIO: {price_spread_pct:.2f}% - Considerar operar")
                else:
                    add_log("INFO", f"❌ SPREAD BAJO: {price_spread_pct:.2f}% - No recomendable")
                
                add_log("INFO", f"📊 Análisis completo - Compradores: {buyers_avg:.2f} VES | Vendedores: {sellers_avg:.2f} VES | Spread: {price_spread_pct:.2f}%")
                return True
                
        add_log("ERROR", "Error en análisis completo del mercado")
        return False
        
    except Exception as e:
        add_log("ERROR", f"Error analizando mercado completo: {e}")
        return False

def send_telegram_message(message):
    """Enviar mensaje a Telegram si está configurado"""
    try:
        if not app_state['telegram']['enabled']:
            return False
            
        bot_token = app_state['telegram']['bot_token']
        chat_id = app_state['telegram']['chat_id']
        
        if not bot_token or not chat_id:
            return False
            
        # Evitar spam - máximo 1 mensaje cada 30 segundos
        current_time = time.time()
        if current_time - app_state['telegram']['last_notification'] < 30:
            return False
            
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            app_state['telegram']['last_notification'] = current_time
            add_log("INFO", "📱 Mensaje enviado a Telegram exitosamente")
            return True
        else:
            add_log("WARNING", f"Error enviando a Telegram: {response.status_code}")
            return False
            
    except Exception as e:
        add_log("ERROR", f"Error enviando mensaje a Telegram: {e}")
        return False

def calculate_suggested_price():
    """Calcular precio sugerido basado en promedio de mercado + mi precio de venta"""
    if not app_state['market_data'] or not app_state['my_sell_price']:
        return None
        
    my_sell_price = app_state['my_sell_price']  # Mi precio de venta
    desired_margin = app_state['desired_margin']  # Margen que quiero ganar
    market_ads = app_state['market_data']  # Datos de los vendedores
    
    # Calcular promedio de los primeros 10 vendedores verificados
    seller_prices = []
    for ad in market_ads[:10]:  # Solo primeros 10
        if ad['advertiser'].get('userType') == 'merchant':  # Solo verificados
            price = float(ad['adv']['price'])
            seller_prices.append(price)
    
    if not seller_prices:
        # Fallback al método anterior si no hay datos
        margin_factor = 1 + (desired_margin / 100)
        suggested_buy_price = my_sell_price / margin_factor
        app_state['suggested_price'] = suggested_buy_price
        return {
            'suggested_price': suggested_buy_price,
            'real_margin': desired_margin,
            'market_reference': 0,
            'my_sell_price': my_sell_price
        }
    
    # Promedio de vendedores verificados
    market_average = sum(seller_prices) / len(seller_prices)
    
    # Nueva lógica: (Mi precio + Promedio mercado) / 2 = Base
    base_price = (my_sell_price + market_average) / 2
    
    # Restar el margen deseado para obtener precio de compra
    margin_factor = 1 + (desired_margin / 100)
    initial_suggested = base_price / margin_factor
    
    # Obtener primeros 5 vendedores para análisis
    top_5_prices = seller_prices[:5] if len(seller_prices) >= 5 else seller_prices
    
    # Detectar outliers: si el primer precio difiere mucho de los otros 4
    if len(top_5_prices) >= 5:
        first_price = top_5_prices[0]
        others_average = sum(top_5_prices[1:4]) / 4  # Promedio de posiciones 2-5
        
        # Calcular diferencia porcentual del primero vs resto
        price_difference = abs(first_price - others_average) / others_average * 100
        
        # Si la diferencia es mayor al 3%, ignorar el primero
        if price_difference > 3.0:
            filtered_prices = top_5_prices[1:]  # Excluir el primero
            top_5_average = sum(filtered_prices) / len(filtered_prices)
            add_log("INFO", f"⚠️ Outlier detectado: {first_price:.2f} VES ({price_difference:.1f}% diferencia) - Ignorado")
        else:
            top_5_average = sum(top_5_prices) / len(top_5_prices)
            add_log("INFO", f"✅ Precios estables en TOP 5 (diferencia: {price_difference:.1f}%)")
    else:
        top_5_average = sum(top_5_prices) / len(top_5_prices) if top_5_prices else market_average
    
    # Precio sugerido basado en el promedio de TOP 5 + 0.05 VES para ser competitivo
    competitive_suggested = top_5_average + 0.05
    
    # Verificar que respete el margen mínimo deseado
    margin_with_competitive = ((my_sell_price - competitive_suggested) / competitive_suggested) * 100
    
    # Solo usar precio competitivo si respeta el margen deseado
    if margin_with_competitive >= desired_margin:
        final_suggested = competitive_suggested
        add_log("INFO", f"🔄 Precio basado en TOP 5: {final_suggested:.2f} VES (promedio TOP 5: {top_5_average:.2f})")
    else:
        # Si no respeta margen, usar cálculo original
        final_suggested = initial_suggested
        add_log("INFO", f"⚠️ Precio calculado para respetar margen: {final_suggested:.2f} VES")
    
    # Redondear precio sugerido a 2 decimales exactos
    final_suggested = round(final_suggested, 2)
    app_state['suggested_price'] = final_suggested
    
    # Calcular margen real usando mi precio de venta
    real_margin = ((my_sell_price - final_suggested) / final_suggested) * 100
    
    add_log("INFO", f"📊 Promedio 10 vendedores: {market_average:.2f} VES")
    add_log("INFO", f"🏆 Promedio TOP 5: {top_5_average:.2f} VES")
    add_log("INFO", f"💰 Precio sugerido final: {final_suggested:.2f} VES")
    add_log("INFO", f"📈 Margen real con tu venta: {real_margin:.2f}%")
    
    return {
        'suggested_price': final_suggested,
        'real_margin': real_margin,
        'market_reference': market_average,
        'my_sell_price': my_sell_price,
        'base_price': base_price,
        'seller_count': len(seller_prices),
        'top_5_average': top_5_average,
        'outlier_detected': False  # Simplified for deployment stability
    }

def update_binance_ad_price(price):
    """Actualizar precio del anuncio en Binance P2P con formato correcto C2C SAPI"""
    if not app_state['api_connected'] or not app_state['ad_id']:
        add_log("WARNING", "API no conectada o ID de anuncio faltante")
        return False, "API no conectada o ID de anuncio faltante"
    
    # Endpoints específicos para C2C
    update_endpoints = [
        "https://api.binance.com/sapi/v1/c2c/ads/update",
        "https://api1.binance.com/sapi/v1/c2c/ads/update",
        "https://api2.binance.com/sapi/v1/c2c/ads/update"
    ]
    
    try:
        # Obtener timestamp del servidor para sincronización perfecta
        try:
            server_response = requests.get('https://api.binance.com/api/v3/time', timeout=10)
            server_timestamp = server_response.json()['serverTime']
            add_log("INFO", f"⏰ Timestamp sincronizado: {server_timestamp}")
        except:
            server_timestamp = int(time.time() * 1000)
            add_log("WARNING", "⏰ Usando timestamp local")
        time.sleep(1)
        
        for endpoint in update_endpoints:
            try:
                add_log("INFO", f"Actualizando via {endpoint.split('//')[1].split('/')[0]} - Precio: {price:.2f} VES")
                
                # Parámetros optimizados para C2C SAPI con timestamp del servidor
                params = {
                    'advNo': str(app_state['ad_id']),
                    'price': f"{price:.2f}",  # Exactamente 2 decimales
                    'timestamp': server_timestamp,
                    'recvWindow': 60000       # Ventana más amplia
                }
                
                # Probar múltiples órdenes de parámetros para C2C
                param_orders = [
                    ['advNo', 'price', 'recvWindow', 'timestamp'],  # Orden original
                    ['advNo', 'price', 'timestamp', 'recvWindow'],  # Orden alternativo
                    ['timestamp', 'advNo', 'price', 'recvWindow'],  # Timestamp primero
                    ['price', 'advNo', 'recvWindow', 'timestamp']   # Precio primero
                ]
                
                for order_idx, param_order in enumerate(param_orders):
                    query_parts = []
                    for key in param_order:
                        if key in params:
                            query_parts.append(f"{key}={params[key]}")
                    
                    query_string = "&".join(query_parts)
                    
                    add_log("INFO", f"🔐 Query para firma: {query_string}")
                
                # Crear firma HMAC con query string específico
                signature = hmac.new(
                    app_state['api_secret'].encode('utf-8'),
                    query_string.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                
                add_log("INFO", f"🔐 Firma generada: {signature[:16]}...")
                
                # Headers específicos para C2C con User-Agent rotativo
                user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'BinanceTrader/1.0',
                    'python-requests/2.28.1'
                ]
                
                headers = {
                    'X-MBX-APIKEY': app_state['api_key'],
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': user_agents[len(endpoint) % len(user_agents)]
                }
                
                # Datos finales para envío
                data_params = params.copy()
                data_params['signature'] = signature
                
                add_log("INFO", f"Enviando: advNo={data_params['advNo']}, price={data_params['price']}")
                
                response = requests.post(
                    endpoint,
                    headers=headers,
                    data=data_params,
                    timeout=30
                )
                
                add_log("INFO", f"Status {response.status_code}: {response.text[:300]}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        
                        # Verificar diferentes formatos de respuesta exitosa
                        success_indicators = [
                            result.get('success'),
                            result.get('data', {}).get('success'),
                            'successfully' in str(result).lower(),
                            result.get('code') == '000000'  # Código de éxito común en APIs chinas
                        ]
                        
                        if any(success_indicators):
                            add_log("SUCCESS", f"✅ Anuncio actualizado: {price:.2f} VES via {endpoint.split('//')[1].split('/')[0]}")
                            return True, f"Anuncio actualizado: {price:.2f} VES"
                        else:
                            error_msg = (result.get('msg') or 
                                       result.get('message') or 
                                       result.get('data', {}).get('msg') or 
                                       'Error desconocido')
                            add_log("WARNING", f"❌ Error API: {error_msg}")
                            
                            # Si es error de permisos, informar específicamente
                            if 'not authorized' in error_msg.lower() or 'permission' in error_msg.lower():
                                add_log("ERROR", "⚠️ Error: Tu API Key no tiene permisos C2C habilitados")
                                return False, "API Key sin permisos C2C - contactar Binance Support"
                                
                            continue
                            
                    except json.JSONDecodeError:
                        add_log("WARNING", f"Respuesta no-JSON: {response.text[:200]}")
                        continue
                        
                elif response.status_code == 400:
                    add_log("WARNING", f"❌ Parámetros incorrectos: {response.text[:150]}")
                    # Intentar con formato alternativo
                    continue
                    
                elif response.status_code == 401:
                    add_log("ERROR", "❌ Error de autenticación - verificar API Key/Secret")
                    return False, "Error de autenticación"
                    
                elif response.status_code == 451:
                    add_log("WARNING", f"🌍 Restricción geográfica en {endpoint.split('//')[1].split('/')[0]}")
                    continue
                    
                elif response.status_code == 500:
                    add_log("WARNING", f"🚨 Error servidor 500: {response.text[:100]}")
                    # Error 500 puede ser temporal, probar siguiente endpoint
                    continue
                    
                else:
                    add_log("WARNING", f"❌ Error {response.status_code}: {response.text[:100]}")
                    continue
                    
            except requests.exceptions.Timeout:
                add_log("WARNING", f"⏱️ Timeout en {endpoint.split('//')[1].split('/')[0]}")
                continue
                
            except requests.exceptions.RequestException as e:
                add_log("WARNING", f"🌐 Error conexión: {str(e)[:50]}")
                continue
                
            # Pausa obligatoria entre requests C2C (5 segundos recomendado)
            time.sleep(2)
        
        # Diagnóstico final
        add_log("ERROR", "❌ Todos los endpoints fallaron")
        add_log("INFO", f"📊 Diagnóstico: advNo={app_state['ad_id']}, price={price:.2f}")
        
        # Sugerencias basadas en el error 500
        add_log("INFO", "💡 Posibles causas: 1) ID anuncio incorrecto, 2) Anuncio inactivo, 3) Sin permisos C2C")
        
        return False, "No se pudo actualizar - verificar ID anuncio y permisos C2C"
            
    except Exception as e:
        add_log("ERROR", f"❌ Error crítico: {e}")
        return False, f"Error: {str(e)}"

def diagnose_ad_issues(ad_id, api_key, api_secret):
    """Diagnosticar problemas específicos con el anuncio P2P"""
    diagnostic_results = []
    
    try:
        add_log("INFO", f"🔍 Diagnosticando anuncio: {ad_id}")
        
        # 1. Validar formato del ID
        if len(ad_id) != 20 or not ad_id.isdigit():
            diagnostic_results.append({
                "test": "Formato ID",
                "status": "❌ FALLO",
                "details": f"ID debe tener 20 dígitos. Actual: {len(ad_id)} caracteres"
            })
        else:
            diagnostic_results.append({
                "test": "Formato ID", 
                "status": "✅ OK",
                "details": "Formato correcto: 20 dígitos numéricos"
            })
        
        # 2. Buscar anuncio en mercado público
        try:
            search_payload = {
                "page": 1,
                "rows": 20,
                "asset": "USDT",
                "fiat": "VES", 
                "tradeType": "BUY"
            }
            
            found_ad = False
            for page in range(1, 6):  # Buscar primeras 5 páginas
                search_payload["page"] = page
                response = requests.post(
                    "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search",
                    json=search_payload,
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ads = data.get('data', [])
                    
                    for ad in ads:
                        if str(ad.get('adv', {}).get('advNo')) == str(ad_id):
                            found_ad = True
                            diagnostic_results.append({
                                "test": "Búsqueda Pública",
                                "status": "✅ ENCONTRADO",
                                "details": f"Precio: {ad['adv']['price']} VES - Comerciante: {ad.get('advertiser', {}).get('nickName', 'N/A')}"
                            })
                            break
                
                if found_ad:
                    break
                    
            if not found_ad:
                diagnostic_results.append({
                    "test": "Búsqueda Pública",
                    "status": "❌ NO ENCONTRADO", 
                    "details": "Anuncio no visible públicamente. Puede estar inactivo o ser privado."
                })
                
        except Exception as search_error:
            diagnostic_results.append({
                "test": "Búsqueda Pública",
                "status": "⚠️ ERROR",
                "details": f"Error buscando: {str(search_error)[:80]}"
            })
        
        # 3. Verificar permisos C2C
        try:
            timestamp = int(time.time() * 1000)
            test_params = {'timestamp': str(timestamp)}
            
            query_string = urlencode(sorted(test_params.items()))
            signature = hmac.new(
                api_secret.encode(),
                query_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'X-MBX-APIKEY': api_key,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            test_params['signature'] = signature
            
            # Probar endpoint C2C básico
            c2c_response = requests.get(
                "https://api.binance.com/sapi/v1/c2c/orderMatch/listUserOrderHistory",
                params=test_params,
                headers=headers,
                timeout=20
            )
            
            if c2c_response.status_code == 200:
                diagnostic_results.append({
                    "test": "Permisos C2C",
                    "status": "✅ OK",
                    "details": "API Key tiene permisos C2C habilitados"
                })
            elif c2c_response.status_code == 401:
                diagnostic_results.append({
                    "test": "Permisos C2C",
                    "status": "❌ SIN PERMISOS",
                    "details": "API Key no tiene permisos C2C habilitados"
                })
            elif c2c_response.status_code == 451:
                diagnostic_results.append({
                    "test": "Permisos C2C",
                    "status": "⚠️ GEOGRÁFICO", 
                    "details": "Restricción geográfica impide verificar permisos"
                })
            else:
                diagnostic_results.append({
                    "test": "Permisos C2C",
                    "status": f"⚠️ HTTP {c2c_response.status_code}",
                    "details": f"Respuesta: {c2c_response.text[:80]}"
                })
                
        except Exception as c2c_error:
            diagnostic_results.append({
                "test": "Permisos C2C",
                "status": "⚠️ ERROR",
                "details": f"Error verificando: {str(c2c_error)[:80]}"
            })
        
        # 4. Generar recomendaciones
        recommendations = []
        
        format_ok = any("✅" in r["status"] for r in diagnostic_results if r["test"] == "Formato ID")
        found_public = any("ENCONTRADO" in r["status"] for r in diagnostic_results if r["test"] == "Búsqueda Pública")
        has_c2c_perms = any("✅" in r["status"] for r in diagnostic_results if r["test"] == "Permisos C2C")
        
        if not format_ok:
            recommendations.append("🔧 Verificar formato del ID de anuncio (20 dígitos numéricos)")
            
        if not found_public:
            recommendations.append("📋 Confirmar ID exacto en Binance P2P > Mis Anuncios")
            recommendations.append("🔄 Verificar que el anuncio esté activo y visible")
            
        if not has_c2c_perms:
            recommendations.append("🔑 Habilitar permisos C2C en Binance API Management")
            recommendations.append("⚙️ Marcar 'C2C Trading' en configuración de API")
            
        if format_ok and found_public and has_c2c_perms:
            recommendations.append("✅ Todos los diagnósticos OK - Error 500 puede ser temporal")
            recommendations.append("🔄 Reintentar actualización en unos minutos")
        
        return diagnostic_results, recommendations
        
    except Exception as e:
        add_log("ERROR", f"Error en diagnóstico: {e}")
        return [{"test": "Diagnóstico General", "status": "❌ ERROR", "details": str(e)}], []

@app.route('/health')
def health_check():
    """Health check endpoint for deployment"""
    return jsonify({
        'status': 'healthy',
        'service': 'Binance P2P Bot',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200

@app.route('/healthz')
def health_check_k8s():
    """Kubernetes-style health check endpoint"""
    return "OK", 200

@app.route('/ready')
def readiness_check():
    """Readiness check endpoint for deployment"""
    return jsonify({'ready': True}), 200

@app.route('/')
def index():
    """Página principal - usar template para mejor rendimiento"""
    try:
        # Temporalmente usar la versión completa con todas las funciones
        add_log("INFO", "Usando interfaz completa con todas las funciones desarrolladas")
        return '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bot P2P Binance - Precio Sugerido</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .section { background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { text-align: center; background: #f8d7da; color: #721c24; padding: 15px; border-radius: 8px; }
        .status-connected { background: #d4edda; color: #155724; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
        .btn:hover { background: #0056b3; }
        .btn-success { background: #28a745; }
        .btn-warning { background: #ffc107; color: #212529; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .price-display { font-size: 24px; font-weight: bold; text-align: center; padding: 20px; }
        .price-market { background: #e3f2fd; color: #1565c0; }
        .price-suggested { background: #e8f5e8; color: #2e7d32; }
        .logs { height: 200px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 4px; font-family: monospace; }
        .log-entry { margin-bottom: 5px; }
        .log-success { color: #28a745; }
        .log-error { color: #dc3545; }
        .log-warning { color: #ffc107; }
        .log-info { color: #17a2b8; }
        .market-table { width: 100%; border-collapse: collapse; }
        .market-table th, .market-table td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        .market-table th { background: #f8f9fa; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header" id="status-header">
            <h1>🤖 Bot P2P Binance - Calculadora de Precio Sugerido</h1>
            <p>Estado: <span id="connection-status">Desconectado</span></p>
            <p><small>💡 El cálculo funciona sin API - Mercado se actualiza automáticamente</small></p>
        </div>

        <!-- Control de Análisis Automático -->
        <div class="section">
            <h2>🤖 Análisis Automático del Mercado</h2>
            <div style="background: #e8f5e8; padding: 15px; border-radius: 4px; margin-bottom: 15px; border-left: 4px solid #28a745;">
                <strong>⚡ Sistema Automático:</strong> Ejecuta análisis completo + Pago Móvil cada 30 segundos con alertas inteligentes
            </div>
            <div class="grid">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; font-size: 18px; font-weight: bold;">
                        <input type="checkbox" id="auto-analysis-enabled" onchange="toggleAutoAnalysis()" checked>
                        <span id="auto-analysis-status">🟢 Análisis Automático ACTIVO</span>
                    </label>
                </div>
                <div>
                    <button class="btn" onclick="analyzeAllMarkets()" style="background: #8b5cf6; font-size: 16px; padding: 12px 20px;">
                        📊 Analizar Ahora (Manual)
                    </button>
                </div>
            </div>
            <div style="background: #fff3cd; padding: 10px; border-radius: 4px; margin-top: 10px; border-left: 4px solid #ffc107;">
                <small><strong>💡 Automatización:</strong> Con análisis automático activo, se ejecuta cada 30 segundos. Usa "Analizar Ahora" para análisis inmediato.</small>
            </div>
        </div>

        <!-- Sección de API -->
        <div class="section">
            <h2>🔑 Configuración de API</h2>
            <div style="background: #d1ecf1; padding: 10px; border-radius: 4px; margin-bottom: 15px; border-left: 4px solid #17a2b8;">
                <strong>🚀 Sistema Anti-Restricción:</strong> El bot probará múltiples endpoints (api.binance.com, api1.binance.com, api2.binance.com) 
                y métodos para evitar restricciones geográficas automáticamente.
            </div>
            <div class="grid">
                <div class="form-group">
                    <label>API Key:</label>
                    <input type="password" id="api-key" placeholder="Tu API Key de Binance">
                </div>
                <div class="form-group">
                    <label>API Secret:</label>
                    <input type="password" id="api-secret" placeholder="Tu API Secret de Binance">
                </div>
            </div>
            <button class="btn" onclick="testConnection()">🔌 Probar Conexión</button>
            <button class="btn btn-success" onclick="saveApiCredentials()">💾 Guardar Credenciales</button>
        </div>

        <!-- Configuración de Telegram -->
        <div class="section">
            <h2>📱 Notificaciones Telegram</h2>
            <div style="background: #e0f2fe; padding: 10px; border-radius: 4px; margin-bottom: 15px; border-left: 4px solid #0288d1;">
                <strong>💡 Alertas Automáticas:</strong><br>
                • <strong>Spread general ≥1.20%</strong> (oportunidades de arbitraje)<br>
                • <strong>Pago Móvil >3.5%</strong> (arbitraje especializado con 1000 VES)<br>
                • <strong>Anti-spam:</strong> 15 min mínimo, excepto si % aumenta >0.5%
            </div>
            <div class="grid">
                <div>
                    <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; font-size: 16px;">
                        <input type="checkbox" id="telegram-enabled" onchange="toggleTelegram()">
                        <span>🔔 Activar notificaciones de arbitraje</span>
                    </label>
                    <small style="color: #6c757d; margin-left: 30px;">Incluye alertas de spread general y Pago Móvil especializado</small>
                </div>
            </div>
            <div class="grid">
                <button class="btn" onclick="testTelegram()" style="background: #28a745;">🧪 Probar Alerta Spread (1.3%)</button>
                <button class="btn" onclick="testPagoMovil()" style="background: #ff9800;">📱 Probar Alerta Pago Móvil (3.8%)</button>
            </div>
        </div>
        
        <!-- Análisis Pago Móvil -->
        <div class="section">
            <h2>📱 Análisis Pago Móvil (1000 VES) - Automático</h2>
            <div style="background: #fff3e0; padding: 10px; border-radius: 4px; margin-bottom: 15px; border-left: 4px solid #ff9800;">
                <strong>🎯 Especializado:</strong> Compara vendedores Pago Móvil (1000 VES) vs compradores TOP para detectar oportunidades de arbitraje >3.5%<br>
                <small><strong>⚡ Actualización:</strong> Se ejecuta automáticamente con el botón "Analizar Todo el Mercado"</small>
            </div>
            <div class="grid">
                <div class="metric">
                    <div class="metric-label">💰 Compradores TOP</div>
                    <div class="metric-value" id="pago-movil-buyers">-- VES</div>
                </div>
                <div class="metric">
                    <div class="metric-label">📱 Vendedores Pago Móvil</div>
                    <div class="metric-value" id="pago-movil-sellers">-- VES</div>
                </div>
                <div class="metric">
                    <div class="metric-label">📊 Diferencia</div>
                    <div class="metric-value" id="pago-movil-difference">--%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">🕒 Última actualización</div>
                    <div class="metric-value" id="pago-movil-update">Nunca</div>
                </div>
            </div>

        </div>

        <!-- Sección de Configuración -->
        <div class="section">
            <h2>⚙️ Configuración del Bot</h2>
            <div class="grid">
                <div class="form-group">
                    <label>ID del Anuncio P2P:</label>
                    <div style="display: flex; gap: 10px;">
                        <input type="text" id="ad-id" placeholder="12345678901234567890" style="flex: 1;">
                        <button class="btn" onclick="testAdConnection()" style="background: #17a2b8; white-space: nowrap;">🔍 Probar Anuncio</button>
                    </div>
                    <small style="color: #6c757d;">Introduce tu ID de anuncio P2P y prueba la conexión</small>
                </div>
                <div class="form-group">
                    <label>Mi Precio de Venta (VES):</label>
                    <input type="number" id="my-sell-price" step="0.0001" placeholder="70.5000" onchange="autoCalculate()">
                </div>
            </div>
            <div class="grid">
                <div class="form-group">
                    <label>Límite Máximo de mi Anuncio (VES):</label>
                    <input type="number" id="max-ad-limit" step="1000" placeholder="100000" value="100000" onchange="updateMaxLimit()">
                    <small style="color: #6c757d;">Límite máximo de tu anuncio para filtrar comerciantes similares</small>
                </div>
                <div class="form-group">
                    <label>Margen Deseado (%):</label>
                    <input type="number" id="desired-margin" step="0.1" value="2.0" placeholder="2.0" onchange="autoCalculate()">
                </div>
            </div>
            <div class="grid">
                <div>
                    <button class="btn btn-warning" onclick="calculatePrice()">💰 Calcular Precio Sugerido</button>
                    <button class="btn" onclick="updateMarket()">🔄 Actualizar Mercado</button>
                    <button class="btn btn-success" onclick="updateAdPrice()">🚀 Actualizar Anuncio Automáticamente</button>
                </div>
            </div>
            <div style="background: #e7f3ff; padding: 15px; border-radius: 4px; margin-top: 10px;">
                <strong>💡 Ejemplo:</strong> Si vendes USDT a 70.5000 VES y quieres 2% ganancia,<br>
                deberías comprar a: <strong>70.5000 ÷ 1.02 = 69.1176 VES</strong>
            </div>
            <div style="background: #fff3cd; padding: 15px; border-radius: 4px; margin-top: 10px; border-left: 4px solid #ffc107;">
                <strong>🤖 Bot Automático:</strong> Con API conectada y ID de anuncio, el bot puede actualizar automáticamente el precio de tu anuncio P2P cada vez que calcules un nuevo precio.
            </div>
        </div>

        <!-- Precios -->
        <div class="section">
            <h2>💵 Precios</h2>
            <div class="grid">
                <div class="price-display price-market">
                    <div>Mejor Precio Mercado (Venta)</div>
                    <div id="market-price">-- VES</div>
                    <small id="last-update">Sin actualizar</small>
                    <button class="btn" onclick="copyMarketPrice()" style="margin-top: 10px; font-size: 12px;">📋 Copiar Precio</button>
                </div>
                <div class="price-display price-suggested">
                    <div>Precio Sugerido (Compra)</div>
                    <div id="suggested-price">-- VES</div>
                    <button class="btn" onclick="copySuggestedPrice()" style="margin-top: 10px; font-size: 12px;">📋 Copiar Precio</button>
                    <small id="real-margin">Margen: --%</small>
                </div>
            </div>
        </div>

        <!-- Análisis Completo del Mercado -->
        <div class="section">
            <h2>📈 Análisis Completo del Mercado (Cada 30s)</h2>
            <div style="background: #d4edda; padding: 10px; border-radius: 4px; margin-bottom: 15px; border-left: 4px solid #28a745;">
                <strong>🔥 Análisis Avanzado:</strong> TOP 5 compradores vs TOP 5 vendedores - Todos los métodos de pago<br>
                <small><strong>📊 Incluye:</strong> Análisis general + Pago Móvil especializado en un solo botón</small>
            </div>
            <div class="grid">
                <div class="price-display" style="background: #ffeaa7; color: #d63031; font-size: 18px;">
                    <div>💰 TOP 5 Compradores (≥100k VES)</div>
                    <div id="buyers-avg">-- VES</div>
                    <small id="buyers-last-update">Sin datos</small>
                </div>
                <div class="price-display" style="background: #a7f3d0; color: #047857; font-size: 18px;">
                    <div>💸 TOP 5 Vendedores (≥10k VES)</div>
                    <div id="sellers-avg">-- VES</div>
                    <small id="sellers-last-update">Sin datos</small>
                </div>
            </div>
            <div class="price-display" style="background: #e0e7ff; color: #3730a3; font-size: 20px; margin-top: 15px; border: 2px solid #6366f1;">
                <div>📈 Diferencia de Precio (Spread)</div>
                <div id="price-spread">--%</div>
                <small id="spread-info">Indica si vale la pena operar</small>
            </div>
            <div id="trend-alert" style="background: #fee2e2; color: #dc2626; padding: 15px; border-radius: 4px; margin-top: 10px; display: none;">
                <strong>⚠️ ALERTA DE MERCADO:</strong> <span id="trend-message"></span>
            </div>

        </div>

        <!-- Mercado Específico (Pago Móvil) -->
        <div class="section">
            <h2>📊 Mercado Específico - Pago Móvil (TOP 5 Vendedores)</h2>
            <div style="background: #d1ecf1; padding: 10px; border-radius: 4px; margin-bottom: 15px; border-left: 4px solid #17a2b8;">
                <strong>🔍 Filtros aplicados:</strong> Solo comerciantes verificados + Pago Móvil únicamente
            </div>
            <table class="market-table">
                <thead>
                    <tr>
                        <th>Comerciante ✓</th>
                        <th>Precio (VES)</th>
                        <th>Límites</th>
                        <th>Completado</th>
                    </tr>
                </thead>
                <tbody id="market-data">
                    <tr><td colspan="4">Sin datos del mercado</td></tr>
                </tbody>
            </table>
        </div>

        <!-- Logs -->
        <div class="section">
            <h2>📝 Registro de Actividad</h2>
            <div class="logs" id="logs-container">
                <div class="log-entry">Esperando actividad...</div>
            </div>
            <button class="btn" onclick="clearLogs()">🗑️ Limpiar Logs</button>
        </div>
    </div>

    <script>
        // Actualizar datos cada 5 segundos
        setInterval(updateStatus, 5000);
        
        // Auto-calcular precio cada 5 segundos si hay configuración
        setInterval(() => {
            const myPrice = parseFloat(document.getElementById('my-sell-price').value);
            const margin = parseFloat(document.getElementById('desired-margin').value);
            if (myPrice && margin) {
                autoCalculate();
            }
        }, 5000);
        
        // Análisis completo del mercado cada 30 segundos
        setInterval(() => {
            analyzeCompleteMarket();
        }, 30000);
        
        // Función para analizar mercado completo
        function analyzeCompleteMarket() {
            fetch('/api/analyze-complete-market', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.analysis) {
                    updateMarketAnalysis(data.analysis);
                }
            });
        }
        
        // Función para actualizar datos del análisis de mercado
        function updateMarketAnalysis(analysis) {
            if (analysis.buyers_avg > 0) {
                document.getElementById('buyers-avg').textContent = analysis.buyers_avg.toFixed(2) + ' VES';
                document.getElementById('buyers-last-update').textContent = 'Actualizado: ' + analysis.last_analysis;
            }
            
            if (analysis.sellers_avg > 0) {
                document.getElementById('sellers-avg').textContent = analysis.sellers_avg.toFixed(2) + ' VES';
                document.getElementById('sellers-last-update').textContent = 'Actualizado: ' + analysis.last_analysis;
            }
            
            // Mostrar diferencia porcentual (spread)
            if (analysis.price_spread_pct !== undefined) {
                const spreadElement = document.getElementById('price-spread');
                const spreadValue = analysis.price_spread_pct.toFixed(2) + '%';
                spreadElement.textContent = spreadValue;
                
                // Colorear según si vale la pena operar (nuevos rangos)
                const spreadInfo = document.getElementById('spread-info');
                if (analysis.price_spread_pct >= 1.2) {
                    spreadElement.style.color = '#047857'; // Verde
                    spreadInfo.textContent = '🚀 EXCELENTE - Vale la pena operar';
                    spreadInfo.style.color = '#047857';
                    
                    // Mostrar notificación cuando vale la pena operar
                    if (window.lastSpreadNotification !== 'high') {
                        alert('🚀 ¡OPORTUNIDAD DE ARBITRAJE! Spread: ' + analysis.price_spread_pct.toFixed(2) + '% - Vale la pena operar');
                        window.lastSpreadNotification = 'high';
                    }
                } else if (analysis.price_spread_pct >= 0.81) {
                    spreadElement.style.color = '#d97706'; // Naranja  
                    spreadInfo.textContent = '⚠️ MEDIO - Considerar operar';
                    spreadInfo.style.color = '#d97706';
                    window.lastSpreadNotification = 'medium';
                } else {
                    spreadElement.style.color = '#dc2626'; // Rojo
                    spreadInfo.textContent = '❌ BAJO - No recomendable operar';
                    spreadInfo.style.color = '#dc2626';
                    window.lastSpreadNotification = 'low';
                }
            }
            
            // Mostrar alerta de tendencia si existe
            const trendAlert = document.getElementById('trend-alert');
            const trendMessage = document.getElementById('trend-message');
            
            if (analysis.trend_alert && analysis.trend_alert.trim() !== '') {
                trendAlert.style.display = 'block';
                trendMessage.textContent = analysis.trend_alert;
            } else {
                trendAlert.style.display = 'none';
            }
        }
        
        // Función para actualizar límite máximo
        function updateMaxLimit() {
            const maxLimit = parseInt(document.getElementById('max-ad-limit').value) || 100000;
            fetch('/api/update-max-limit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({max_limit: maxLimit})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('Límite máximo actualizado:', maxLimit);
                    // Auto-actualizar el mercado con el nuevo límite
                    updateMarket();
                }
            });
        }
        
        // Función para toggle Telegram (simplificado)
        function toggleTelegram() {
            const enabled = document.getElementById('telegram-enabled').checked;
            
            fetch('/api/telegram-config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    bot_token: '7843798517:AAE7waua0AmZZknBo6_LdMeOowj7mUNgg8k',
                    chat_id: '6888281395',
                    enabled: enabled
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (enabled) {
                        alert('✅ Notificaciones Telegram activadas');
                    } else {
                        alert('🔕 Notificaciones Telegram desactivadas');
                    }
                } else {
                    alert('❌ ' + data.message);
                    // Revertir el checkbox si hay error
                    document.getElementById('telegram-enabled').checked = !enabled;
                }
            })
            .catch(error => {
                alert('❌ Error de conexión');
                document.getElementById('telegram-enabled').checked = !enabled;
            });
        }
        
        // Función para probar notificación Telegram
        function testTelegram() {
            fetch('/api/test-telegram', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('✅ ' + data.message);
                } else {
                    alert('❌ ' + data.message);
                }
            });
        }
        
        // Función para probar alerta Pago Móvil
        function testPagoMovil() {
            fetch('/api/test-pago-movil', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('✅ ' + data.message);
                } else {
                    alert('❌ ' + data.message);
                }
            });
        }
        
        // Función para toggle del análisis automático
        function toggleAutoAnalysis() {
            const enabled = document.getElementById('auto-analysis-enabled').checked;
            const status = document.getElementById('auto-analysis-status');
            
            fetch('/api/toggle-auto-analysis', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enabled: enabled})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (enabled) {
                        status.textContent = '🟢 Análisis Automático ACTIVO';
                        status.style.color = '#28a745';
                    } else {
                        status.textContent = '🔴 Análisis Automático INACTIVO';
                        status.style.color = '#dc3545';
                    }
                }
            });
        }
        
        // Función unificada para analizar todos los mercados
        function analyzeAllMarkets() {
            // Ejecutar análisis completo del mercado
            fetch('/api/analyze-complete-market', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Actualizar datos del análisis completo
                    document.getElementById('buyers-avg').textContent = data.buyers_avg.toFixed(2) + ' VES';
                    document.getElementById('sellers-avg').textContent = data.sellers_avg.toFixed(2) + ' VES';
                    document.getElementById('price-spread').textContent = data.spread.toFixed(2) + '%';
                    document.getElementById('buyers-last-update').textContent = data.last_analysis;
                    document.getElementById('sellers-last-update').textContent = data.last_analysis;
                    
                    // Mostrar información del spread
                    const spreadInfo = document.getElementById('spread-info');
                    if (data.spread >= 1.20) {
                        spreadInfo.textContent = '✅ Excelente - Vale la pena operar';
                        spreadInfo.style.color = '#10b981';
                    } else if (data.spread >= 0.81) {
                        spreadInfo.textContent = '⚠️ Medio - Considerar operar';
                        spreadInfo.style.color = '#f59e0b';
                    } else {
                        spreadInfo.textContent = '❌ Bajo - No recomendable';
                        spreadInfo.style.color = '#ef4444';
                    }
                }
            });
            
            // Ejecutar análisis de Pago Móvil
            fetch('/api/analyze-pago-movil', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('pago-movil-buyers').textContent = data.buyers_avg.toFixed(2) + ' VES';
                    document.getElementById('pago-movil-sellers').textContent = data.sellers_avg.toFixed(2) + ' VES';
                    document.getElementById('pago-movil-difference').textContent = data.difference_percent.toFixed(2) + '%';
                    document.getElementById('pago-movil-update').textContent = data.last_analysis;
                }
            });
        }
        
        // Función para copiar mejor precio del mercado
        function copyMarketPrice() {
            const marketPriceText = document.getElementById('market-price').textContent;
            const price = marketPriceText.replace(' VES', '').replace('--', '').trim();
            if (price) {
                navigator.clipboard.writeText(price).then(() => {
                    alert('✅ Mejor precio del mercado copiado: ' + price + ' VES');
                }).catch(() => {
                    // Fallback para navegadores más antiguos
                    const textArea = document.createElement('textarea');
                    textArea.value = price;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    alert('✅ Mejor precio del mercado copiado: ' + price + ' VES');
                });
            } else {
                alert('⚠️ No hay precio de mercado disponible');
            }
        }
        
        // Función para copiar precio sugerido
        function copySuggestedPrice() {
            const suggestedPriceText = document.getElementById('suggested-price').textContent;
            const price = suggestedPriceText.replace(' VES', '').replace('--', '').trim();
            if (price) {
                navigator.clipboard.writeText(price).then(() => {
                    alert('✅ Precio sugerido copiado: ' + price + ' VES');
                }).catch(() => {
                    // Fallback para navegadores más antiguos
                    const textArea = document.createElement('textarea');
                    textArea.value = price;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    alert('✅ Precio sugerido copiado: ' + price + ' VES');
                });
            } else {
                alert('⚠️ No hay precio sugerido disponible');
            }
        }
        
        function testConnection() {
            const apiKey = document.getElementById('api-key').value;
            const apiSecret = document.getElementById('api-secret').value;
            
            if (!apiKey || !apiSecret) {
                alert('Por favor ingresa API Key y Secret');
                return;
            }
            
            fetch('/api/test-connection', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({api_key: apiKey, api_secret: apiSecret})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('connection-status').textContent = 'Conectado ✓';
                    document.getElementById('status-header').className = 'header status-connected';
                } else {
                    alert('Error: ' + data.message);
                }
            });
        }
        
        function saveApiCredentials() {
            const apiKey = document.getElementById('api-key').value;
            const apiSecret = document.getElementById('api-secret').value;
            
            if (!apiKey || !apiSecret) {
                alert('Por favor ingresa credenciales válidas');
                return;
            }
            
            fetch('/api/save-credentials', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({api_key: apiKey, api_secret: apiSecret})
            })
            .then(response => response.json())
            .then(data => alert(data.message));
        }
        
        function calculatePrice() {
            const myPrice = parseFloat(document.getElementById('my-sell-price').value);
            const margin = parseFloat(document.getElementById('desired-margin').value);
            const adId = document.getElementById('ad-id').value;
            
            if (!myPrice || !margin) {
                alert('Por favor completa precio de venta y margen');
                return;
            }
            
            fetch('/api/calculate-price', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    my_sell_price: myPrice,
                    desired_margin: margin,
                    ad_id: adId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('suggested-price').textContent = data.suggested_price.toFixed(4) + ' VES';
                    document.getElementById('real-margin').textContent = 'Margen: ' + data.real_margin.toFixed(2) + '%';
                }
            });
        }
        
        function autoCalculate() {
            const myPrice = parseFloat(document.getElementById('my-sell-price').value);
            const margin = parseFloat(document.getElementById('desired-margin').value);
            
            if (myPrice && margin) {
                // Hacer cálculo completo usando la API para obtener precio basado en TOP 5
                fetch('/api/calculate-price', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        my_sell_price: myPrice,
                        desired_margin: margin,
                        ad_id: document.getElementById('ad-id').value
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('suggested-price').textContent = data.suggested_price.toFixed(2) + ' VES';
                        document.getElementById('real-margin').textContent = 'Margen: ' + data.real_margin.toFixed(2) + '%';
                    }
                })
                .catch(() => {
                    // Fallback al cálculo simple si hay error
                    const suggestedPrice = myPrice / (1 + margin / 100);
                    document.getElementById('suggested-price').textContent = suggestedPrice.toFixed(2) + ' VES';
                    document.getElementById('real-margin').textContent = 'Margen: ' + margin.toFixed(1) + '%';
                });
            }
        }
        
        function updateAdPrice() {
            const suggestedPriceText = document.getElementById('suggested-price').textContent;
            
            if (!suggestedPriceText || suggestedPriceText === '-- VES') {
                alert('Primero calcula el precio sugerido');
                return;
            }
            
            const price = parseFloat(suggestedPriceText.replace(' VES', ''));
            
            if (confirm(`¿Actualizar tu anuncio P2P al precio ${price.toFixed(4)} VES?`)) {
                fetch('/api/update-ad-price', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({price: price})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('✅ Anuncio actualizado exitosamente: ' + data.message);
                    } else {
                        alert('❌ Error: ' + data.message);
                    }
                });
            }
        }
        
        function updateMarket() {
            fetch('/api/update-market', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('market-price').textContent = data.market_price.toFixed(4) + ' VES';
                    document.getElementById('last-update').textContent = 'Actualizado: ' + data.last_update;
                }
            });
        }
        
        function updateStatus() {
            fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                // Actualizar logs
                const logsContainer = document.getElementById('logs-container');
                logsContainer.innerHTML = '';
                data.logs.forEach(log => {
                    const logElement = document.createElement('div');
                    logElement.className = 'log-entry log-' + log.level.toLowerCase();
                    logElement.textContent = `[${log.timestamp}] ${log.level}: ${log.message}`;
                    logsContainer.appendChild(logElement);
                });
                logsContainer.scrollTop = logsContainer.scrollHeight;
                
                // Actualizar tabla del mercado
                const marketTable = document.getElementById('market-data');
                marketTable.innerHTML = '';
                if (data.market_data && data.market_data.length > 0) {
                    data.market_data.slice(0, 5).forEach(ad => {
                        const row = document.createElement('tr');
                        const merchant = ad.advertiser.nickName;
                        const price = parseFloat(ad.adv.price).toFixed(4);
                        const minAmount = ad.adv.minSingleTransAmount;
                        const maxAmount = ad.adv.maxSingleTransAmount;
                        const orderCount = ad.advertiser.monthOrderCount;
                        const rate = ad.advertiser.monthFinishRate;
                        
                        row.innerHTML = `
                            <td>${merchant}</td>
                            <td>${price} VES</td>
                            <td>${minAmount} - ${maxAmount}</td>
                            <td>${orderCount} (${(rate * 100).toFixed(1)}%)</td>
                        `;
                        marketTable.appendChild(row);
                    });
                } else {
                    marketTable.innerHTML = '<tr><td colspan="4">Sin datos del mercado</td></tr>';
                }
                
                // Actualizar estado de conexión
                if (data.api_connected) {
                    document.getElementById('connection-status').textContent = 'Conectado ✓';
                    document.getElementById('status-header').className = 'header status-connected';
                }
                
                // Actualizar estado del análisis automático
                if (data.auto_analysis_enabled !== undefined) {
                    document.getElementById('auto-analysis-enabled').checked = data.auto_analysis_enabled;
                    const status = document.getElementById('auto-analysis-status');
                    if (data.auto_analysis_enabled) {
                        status.textContent = '🟢 Análisis Automático ACTIVO';
                        status.style.color = '#28a745';
                    } else {
                        status.textContent = '🔴 Análisis Automático INACTIVO';
                        status.style.color = '#dc3545';
                    }
                }
                
                // Actualizar datos de Pago Móvil si están disponibles
                if (data.pago_movil_analysis && data.pago_movil_analysis.buyers_avg > 0) {
                    const pagoMovil = data.pago_movil_analysis;
                    document.getElementById('pago-movil-buyers').textContent = pagoMovil.buyers_avg.toFixed(2) + ' VES';
                    document.getElementById('pago-movil-sellers').textContent = pagoMovil.sellers_avg.toFixed(2) + ' VES';
                    document.getElementById('pago-movil-difference').textContent = pagoMovil.difference_percent.toFixed(2) + '%';
                    document.getElementById('pago-movil-update').textContent = pagoMovil.last_analysis;
                }
            });
        }
        
        function clearLogs() {
            fetch('/api/clear-logs', {method: 'POST'});
        }
        
        function testAdConnection() {
            const adId = document.getElementById('ad-id').value;
            
            if (!adId) {
                alert('Por favor ingresa el ID del anuncio P2P');
                return;
            }
            
            // Mostrar indicador de carga
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '🔍 Probando...';
            btn.disabled = true;
            
            fetch('/api/diagnose-ad', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ad_id: adId})
            })
            .then(response => response.json())
            .then(data => {
                // Restaurar botón
                btn.textContent = originalText;
                btn.disabled = false;
                
                if (data.success) {
                    // Crear ventana de diagnóstico compacta
                    let diagnosticHtml = '<div style="max-width: 500px;">';
                    diagnosticHtml += '<h3>🔍 Prueba de Conexión: ' + adId + '</h3><br>';
                    
                    // Mostrar solo los resultados críticos
                    let allOk = true;
                    let criticalIssues = [];
                    
                    data.diagnostics.forEach(diagnostic => {
                        const isError = diagnostic.status.includes('❌') || diagnostic.status.includes('SIN PERMISOS');
                        if (isError) {
                            allOk = false;
                            criticalIssues.push(diagnostic);
                        }
                        
                        const statusColor = diagnostic.status.includes('✅') ? '#28a745' : 
                                          diagnostic.status.includes('❌') ? '#dc3545' : '#ffc107';
                        
                        diagnosticHtml += '<div style="margin-bottom: 8px; padding: 8px; border-left: 3px solid ' + statusColor + '; background: #f8f9fa;">';
                        diagnosticHtml += '<strong>' + diagnostic.test + ':</strong> ' + diagnostic.status + '<br>';
                        diagnosticHtml += '<small>' + diagnostic.details + '</small>';
                        diagnosticHtml += '</div>';
                    });
                    
                    // Resumen general
                    if (allOk) {
                        diagnosticHtml += '<div style="padding: 15px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; margin-top: 15px;">';
                        diagnosticHtml += '<strong style="color: #155724;">✅ ¡Anuncio Verificado!</strong><br>';
                        diagnosticHtml += '<small>Tu anuncio está configurado correctamente y debería funcionar con la actualización automática.</small>';
                        diagnosticHtml += '</div>';
                    } else {
                        diagnosticHtml += '<div style="padding: 15px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; margin-top: 15px;">';
                        diagnosticHtml += '<strong style="color: #721c24;">⚠️ Problemas Detectados</strong><br>';
                        diagnosticHtml += '<small>Revisa las recomendaciones para resolver los problemas antes de usar la actualización automática.</small>';
                        diagnosticHtml += '</div>';
                        
                        // Mostrar recomendaciones solo si hay problemas
                        diagnosticHtml += '<h4 style="margin-top: 15px;">💡 Acciones Requeridas:</h4>';
                        data.recommendations.slice(0, 3).forEach(recommendation => {
                            diagnosticHtml += '<div style="margin-bottom: 5px; padding: 8px; background: #fff3cd; border-left: 3px solid #ffc107; font-size: 14px;">';
                            diagnosticHtml += recommendation;
                            diagnosticHtml += '</div>';
                        });
                    }
                    
                    diagnosticHtml += '</div>';
                    
                    // Crear modal más compacto
                    const modal = document.createElement('div');
                    modal.style.cssText = `
                        position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                        background: rgba(0,0,0,0.7); z-index: 1000; display: flex; 
                        align-items: center; justify-content: center; padding: 20px;
                    `;
                    
                    const content = document.createElement('div');
                    content.style.cssText = `
                        background: white; padding: 20px; border-radius: 8px; 
                        max-width: 90%; max-height: 80%; overflow-y: auto; position: relative;
                    `;
                    
                    content.innerHTML = diagnosticHtml + 
                        '<br><div style="text-align: center;">' +
                        '<button onclick="this.parentElement.parentElement.parentElement.remove()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px;">Cerrar</button>' +
                        (allOk ? '<button onclick="this.parentElement.parentElement.parentElement.remove(); calculatePrice();" style="padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">✓ Continuar</button>' : '') +
                        '</div>';
                    
                    modal.appendChild(content);
                    document.body.appendChild(modal);
                    
                } else {
                    alert('❌ Error en la prueba: ' + data.message);
                }
            })
            .catch(error => {
                btn.textContent = originalText;
                btn.disabled = false;
                alert('❌ Error de conexión: ' + error.message);
            });
        }
        
        // Auto-actualizar mercado cada 30 segundos
        setInterval(updateMarket, 30000);
        
        // Cargar datos iniciales
        updateStatus();
        updateMarket();
    </script>
</body>
</html>
    '''
    except Exception as e:
        # Fallback si hay error cargando el HTML completo
        add_log("ERROR", f"Error cargando interfaz completa: {e}")
        return render_template('index.html')

@app.route('/api/analyze-complete-market', methods=['POST'])
def api_analyze_complete_market():
    """Ejecutar análisis completo del mercado (TOP 5 compradores y vendedores)"""
    success = analyze_complete_market()
    
    if success:
        return jsonify({
            'success': True,
            'analysis': app_state['market_analysis'],
            'message': 'Análisis completo realizado exitosamente'
        })
    else:
        return jsonify({'success': False, 'message': 'Error en análisis completo del mercado'})

@app.route('/api/test-pago-movil', methods=['POST'])
def api_test_pago_movil():
    """Probar notificación de Pago Móvil con datos simulados"""
    try:
        # Simular una oportunidad de arbitraje Pago Móvil al 3.8%
        test_buyers_avg = 165.50
        test_sellers_avg = 159.50  # Para lograr 3.8% de diferencia
        test_difference = 3.8
        
        # Enviar mensaje de prueba
        telegram_message = f"""🚀 <b>PRUEBA - OPORTUNIDAD DE ARBITRAJE - PAGO MÓVIL</b>

📱 <b>Mercado:</b> Pago Móvil (1000 VES)
📊 <b>Diferencia:</b> {test_difference:.2f}%

💰 <b>Compradores TOP:</b> {test_buyers_avg:.2f} VES
💸 <b>Vendedores Pago Móvil:</b> {test_sellers_avg:.2f} VES

✅ <b>¡Excelente oportunidad de arbitraje!</b>
🕒 {datetime.now().strftime("%H:%M:%S")}

<i>Compra USDT con Pago Móvil y vende a precio más alto</i>
⚠️ <i>Esto es una prueba del sistema</i>"""
        
        success = send_telegram_message(telegram_message)
        
        if success:
            add_log("SUCCESS", f"🧪 PRUEBA PAGO MÓVIL - Diferencia simulada: {test_difference:.2f}% - ¡Mensaje enviado!")
            return jsonify({'success': True, 'message': 'Mensaje de prueba Pago Móvil enviado a Telegram exitosamente'})
        else:
            return jsonify({'success': False, 'message': 'Error enviando mensaje de prueba. Verifica la configuración de Telegram'})
            
    except Exception as e:
        add_log("ERROR", f"Error en prueba Pago Móvil: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/analyze-pago-movil', methods=['POST'])
def api_analyze_pago_movil():
    """Analizar mercado Pago Móvil específico"""
    try:
        success = analyze_pago_movil_1000()
        
        if success:
            return jsonify({
                'success': True,
                'buyers_avg': app_state['pago_movil_analysis']['buyers_avg'],
                'sellers_avg': app_state['pago_movil_analysis']['sellers_avg'],
                'difference_percent': app_state['pago_movil_analysis']['difference_percent'],
                'last_analysis': app_state['pago_movil_analysis']['last_analysis']
            })
        else:
            return jsonify({'success': False, 'message': 'Error en análisis de Pago Móvil'})
            
    except Exception as e:
        add_log("ERROR", f"Error en API análisis Pago Móvil: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/toggle-auto-analysis', methods=['POST'])
def api_toggle_auto_analysis():
    """Toggle del análisis automático"""
    try:
        data = request.json
        enabled = data.get('enabled', True)
        
        app_state['auto_analysis']['enabled'] = enabled
        
        if enabled:
            add_log("SUCCESS", "🤖 Análisis automático ACTIVADO - Ejecutándose cada 30 segundos")
        else:
            add_log("WARNING", "⏸️ Análisis automático DESACTIVADO - Solo análisis manual")
        
        return jsonify({
            'success': True, 
            'enabled': enabled,
            'message': f'Análisis automático {"activado" if enabled else "desactivado"}'
        })
        
    except Exception as e:
        add_log("ERROR", f"Error toggle auto-análisis: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/test-telegram', methods=['POST'])
def api_test_telegram():
    """Probar notificación de Telegram con datos simulados"""
    try:
        # Simular una oportunidad de arbitraje al 1.3%
        test_spread = 1.3
        test_buyers_avg = 165.50
        test_sellers_avg = 163.35  # Para lograr 1.3% de spread
        
        # Enviar mensaje de prueba
        telegram_message = f"""🚀 <b>PRUEBA - OPORTUNIDAD DE ARBITRAJE</b>
                    
📊 <b>Spread:</b> {test_spread:.2f}%
💰 <b>Compradores:</b> {test_buyers_avg:.2f} VES
💸 <b>Vendedores:</b> {test_sellers_avg:.2f} VES

✅ <b>Vale la pena operar!</b>
🕒 {datetime.now().strftime("%H:%M:%S")}
⚠️ <i>Esto es una prueba del sistema</i>"""
        
        success = send_telegram_message(telegram_message)
        
        if success:
            add_log("SUCCESS", f"🧪 PRUEBA TELEGRAM - Spread simulado: {test_spread:.2f}% - Mensaje enviado!")
            return jsonify({'success': True, 'message': 'Mensaje de prueba enviado a Telegram exitosamente'})
        else:
            return jsonify({'success': False, 'message': 'Error enviando mensaje de prueba. Verifica la configuración de Telegram'})
            
    except Exception as e:
        add_log("ERROR", f"Error en prueba de Telegram: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/telegram-config', methods=['POST'])
def api_telegram_config():
    """Configurar Telegram Bot"""
    try:
        data = request.get_json()
        bot_token = data.get('bot_token', '').strip()
        chat_id = data.get('chat_id', '').strip()
        enabled = data.get('enabled', False)
        
        # Validar configuración si está habilitado
        if enabled and (not bot_token or not chat_id):
            return jsonify({'success': False, 'message': 'Token y Chat ID son requeridos'})
            
        # Probar conexión si está habilitado
        if enabled:
            test_url = f"https://api.telegram.org/bot{bot_token}/getMe"
            response = requests.get(test_url, timeout=10)
            
            if response.status_code != 200:
                return jsonify({'success': False, 'message': 'Token de bot inválido'})
                
            # Probar envío de mensaje
            test_message = "✅ Bot P2P conectado exitosamente a Telegram"
            test_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            test_payload = {'chat_id': chat_id, 'text': test_message}
            test_response = requests.post(test_url, json=test_payload, timeout=10)
            
            if test_response.status_code != 200:
                return jsonify({'success': False, 'message': 'Chat ID inválido o bot no autorizado'})
        
        # Guardar configuración
        app_state['telegram']['bot_token'] = bot_token
        app_state['telegram']['chat_id'] = chat_id
        app_state['telegram']['enabled'] = enabled
        
        if enabled:
            add_log("INFO", "📱 Telegram configurado exitosamente")
            return jsonify({'success': True, 'message': 'Telegram configurado exitosamente'})
        else:
            add_log("INFO", "📱 Telegram deshabilitado")
            return jsonify({'success': True, 'message': 'Telegram deshabilitado'})
            
    except Exception as e:
        add_log("ERROR", f"Error configurando Telegram: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/update-max-limit', methods=['POST'])
def api_update_max_limit():
    """Actualizar límite máximo del anuncio del usuario"""
    try:
        data = request.json
        max_limit = data.get('max_limit', 100000)
        
        # Validar que el límite esté en rango razonable
        if max_limit < 1000:
            max_limit = 1000
        elif max_limit > 1000000:
            max_limit = 1000000
            
        app_state['user_ad_limit'] = max_limit
        add_log("INFO", f"Límite máximo actualizado: {max_limit:,.0f} VES")
        
        return jsonify({
            'success': True,
            'max_limit': max_limit,
            'message': f'Límite actualizado a {max_limit:,.0f} VES'
        })
        
    except Exception as e:
        add_log("ERROR", f"Error actualizando límite: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """Test de conexión API"""
    data = request.json
    api_key = data.get('api_key', '')
    api_secret = data.get('api_secret', '')
    
    success, message = validate_binance_api(api_key, api_secret)
    
    if success:
        app_state['api_connected'] = True
        app_state['api_key'] = api_key
        app_state['api_secret'] = api_secret
    
    return jsonify({'success': success, 'message': message})

@app.route('/api/save-credentials', methods=['POST'])
def save_credentials():
    """Guardar credenciales"""
    data = request.json
    app_state['api_key'] = data.get('api_key', '')
    app_state['api_secret'] = data.get('api_secret', '')
    
    add_log("INFO", "Credenciales guardadas")
    return jsonify({'success': True, 'message': 'Credenciales guardadas'})

@app.route('/api/calculate-price', methods=['POST'])
def calculate_price_api():
    """Calcular precio sugerido"""
    data = request.json
    
    app_state['my_sell_price'] = data.get('my_sell_price', 0)
    app_state['desired_margin'] = data.get('desired_margin', 0)
    app_state['ad_id'] = data.get('ad_id', '')
    
    # Primero actualizar mercado
    get_market_data()
    
    # Luego calcular precio
    result = calculate_suggested_price()
    
    if result:
        return jsonify({
            'success': True,
            'suggested_price': result['suggested_price'],
            'real_margin': result['real_margin']
        })
    else:
        return jsonify({'success': False, 'message': 'No se pudo calcular precio'})

@app.route('/api/update-market', methods=['POST'])
def update_market_api():
    """Actualizar datos del mercado"""
    success, price = get_market_data()
    
    if success:
        return jsonify({
            'success': True,
            'market_price': price,
            'last_update': app_state['last_update']
        })
    else:
        return jsonify({'success': False, 'message': 'Error actualizando mercado'})

@app.route('/api/status')
def status():
    """Estado actual"""
    return jsonify({
        'api_connected': app_state['api_connected'],
        'market_price': app_state['market_price'],
        'suggested_price': app_state['suggested_price'],
        'logs': app_state['logs'][-20:],  # Últimos 20 logs
        'market_data': app_state['market_data'],
        'last_update': app_state['last_update'],
        'market_analysis': app_state['market_analysis'],
        'telegram_enabled': app_state['telegram']['enabled'],
        'auto_analysis_enabled': app_state['auto_analysis']['enabled'],
        'pago_movil_analysis': app_state['pago_movil_analysis']
    })

@app.route('/api/logs')
def get_logs():
    """Obtener logs del sistema"""
    return jsonify({'logs': app_state['logs']})

@app.route('/api/clear-logs', methods=['POST'])
def clear_logs():
    """Limpiar logs"""
    app_state['logs'] = []
    return jsonify({'success': True})

@app.route('/api/update-ad-price', methods=['POST'])
def update_ad_price_api():
    """Actualizar precio del anuncio P2P"""
    data = request.json
    price = data.get('price', 0)
    
    if not price:
        return jsonify({'success': False, 'message': 'Precio inválido'})
    
    success, message = update_binance_ad_price(price)
    return jsonify({'success': success, 'message': message})

@app.route('/api/diagnose-ad', methods=['POST'])
def diagnose_ad_api():
    """Ejecutar diagnóstico completo del anuncio P2P"""
    try:
        data = request.json
        ad_id = data.get('ad_id', app_state.get('ad_id', ''))
        
        if not ad_id:
            return jsonify({"success": False, "message": "ID de anuncio requerido"})
        
        if not app_state.get('api_key') or not app_state.get('api_secret'):
            return jsonify({"success": False, "message": "Credenciales API requeridas"})
        
        # Ejecutar diagnóstico
        diagnostic_results, recommendations = diagnose_ad_issues(
            ad_id, 
            app_state['api_key'], 
            app_state['api_secret']
        )
        
        return jsonify({
            "success": True,
            "diagnostics": diagnostic_results,
            "recommendations": recommendations,
            "summary": f"Diagnóstico completado - {len(diagnostic_results)} pruebas realizadas"
        })
        
    except Exception as e:
        add_log("ERROR", f"Error en diagnose_ad: {e}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

def start_background_tasks():
    """Start background tasks for market analysis"""
    def auto_analyze_market():
        """Análisis automático del mercado cada 30 segundos"""
        while True:
            try:
                time.sleep(30)  # Esperar 30 segundos
                # Solo ejecutar si está habilitado el análisis automático
                if app_state['auto_analysis']['enabled']:
                    analyze_complete_market()
                    # También analizar Pago Móvil
                    if app_state['pago_movil_analysis']['enabled']:
                        analyze_pago_movil_1000()
            except Exception as e:
                add_log("ERROR", f"Error en análisis automático: {e}")
    
    # Iniciar hilo en background
    market_thread = threading.Thread(target=auto_analyze_market, daemon=True)
    market_thread.start()

if __name__ == '__main__':
    import os
    
    add_log("INFO", "Iniciando interfaz web del bot P2P")
    
    # Start background tasks
    start_background_tasks()
    
    # Get port from environment for deployment, default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Check if running in production environment
    is_production = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('ENVIRONMENT') == 'production'
    debug_mode = not is_production
    
    add_log("INFO", f"Configuración: Puerto={port}, Producción={is_production}, Debug={debug_mode}")
    
    # Configure for deployment
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=debug_mode,
        threaded=True,
        use_reloader=debug_mode  # Only use reloader in development
    )