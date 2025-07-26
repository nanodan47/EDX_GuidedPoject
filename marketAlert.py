import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from win10toast import ToastNotifier
import webbrowser
import yfinance as yf

# API Key de noticias
FINNHUB_API_KEY = "d17lhp9r01qtc1t94r4gd17lhp9r01qtc1t94r50"

# Configuración de correo
EMAIL_FROM = "nanodan47@gmail.com"
EMAIL_TO = "djaramillorosero@gmail.com"
EMAIL_SUBJECT = "🚨 Alerta de Movimiento de Acción"
EMAIL_APP_PASSWORD = "ywpj waxg cadu ochg"  # ← Cambia esto por tu clave real

# Watchlist
watchlist = ["PLTR", "NVDA", "AMD", "TSLA",
             "MSFT", "AMZN", "META", "GOOGL", "BAC",
             "C", "DIS", "INTC", "MU", "ORCL"]

# Parámetros
PRICE_CHANGE_THRESHOLD = 1.0
VOLUME_SPIKE_THRESHOLD = 3.0
CHECK_INTERVAL = 60

def send_email(subject, body):
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
            server.send_message(msg)
        print("📧 Correo enviado correctamente.")
    except Exception as e:
        print(f"❌ Error al enviar correo: {e}")

def get_unusual_movement():
    unusual_stocks = []
    for symbol in watchlist:
        try:
            data = yf.download(symbol, period="1d", interval="1m", auto_adjust=False, progress=False)
            if len(data) < 10:
                continue

            recent_change_pct = ((data['Close'].iloc[-1] - data['Close'].iloc[-5]) / data['Close'].iloc[-5]) * 100
            if isinstance(recent_change_pct, pd.Series):
                recent_change_pct = recent_change_pct.squeeze()

            avg_volume = yf.download(symbol, period="10d", interval="1d", auto_adjust=False, progress=False)['Volume'].mean() / 390
            if isinstance(avg_volume, pd.Series):
                avg_volume = avg_volume.squeeze()

            current_volume = data['Volume'].iloc[-5:].mean()
            if isinstance(current_volume, pd.Series):
                current_volume = current_volume.squeeze()

            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0


            if (abs(recent_change_pct) > PRICE_CHANGE_THRESHOLD or volume_ratio > VOLUME_SPIKE_THRESHOLD):
                direction = "🔴 DOWN" if recent_change_pct < 0 else "🟢 UP"
                unusual_stocks.append({
                    'symbol': symbol,
                    'change_pct': recent_change_pct,
                    'volume_ratio': volume_ratio,
                    'direction': direction
                })
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
    return unusual_stocks

def get_latest_news(symbol):
    url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={datetime.now().strftime('%Y-%m-%d')}&to={datetime.now().strftime('%Y-%m-%d')}&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url)
        news = response.json()
        if news and len(news) > 0:
            sorted_news = sorted(news, key=lambda x: x['datetime'], reverse=True)
            return sorted_news[:3]
        return []
    except Exception as e:
        print(f"Error getting news for {symbol}: {e}")
        return []

def send_alert(stock_info, news_items):
    symbol = stock_info['symbol']
    direction = stock_info['direction']
    change = round(stock_info['change_pct'], 2)
    volume = round(stock_info['volume_ratio'], 1)

    title = f"{symbol} {direction} {change}% | Vol: {volume}x"

    if news_items:
        news_text = "\n".join([f"• {item['headline']}" for item in news_items[:2]])
        message = f"Possible catalyst:\n{news_text}"
        url = news_items[0].get('url')
    else:
        message = "No recent news found. Check for market-wide movements or unreported news."
        url = f"https://finance.yahoo.com/quote/{symbol}"

    # Notificación en escritorio
    notifier = ToastNotifier()
    try:
        result = notifier.show_toast(title, message, duration=10, threaded=False)
        if result is None:
            result = 0  # evitar el NoneType crash en WNDPROC
        time.sleep(1)
    except Exception as e:
        print(f"❌ Error en notificación: {e}")

    # Correo
    send_email(subject=EMAIL_SUBJECT + f" - {symbol}", body=f"{title}\n\n{message}\n\n{url if url else ''}")

    # Navegador (opcional: comentar si no lo deseas)
    #if url:
    #    webbrowser.open(url)

    # Consola
    print(f"\n{'='*50}")
    print(f"{datetime.now().strftime('%H:%M:%S')} | {title}")
    print(f"{message}")
    if url:
        print(f"🔗 {url}")
    print(f"{'='*50}\n")

def monitor_market_movers():
    print(f"Starting Market Mover Monitor at {datetime.now().strftime('%H:%M:%S')}")
    print(f"Monitoring {len(watchlist)} stocks for unusual movements...")
    print(f"Alert thresholds: {PRICE_CHANGE_THRESHOLD}% price change or {VOLUME_SPIKE_THRESHOLD}x volume spike")
    
    alerted_stocks = set()
    
    while True:
        try:
            # Reinicio cada 30 min
            current_minute = datetime.now().minute
            if current_minute % 30 == 0:
                alerted_stocks = set()
                print(f"Reset alert tracking at {datetime.now().strftime('%H:%M:%S')}")

            unusual_stocks = get_unusual_movement()

            for stock in unusual_stocks:
                symbol = stock['symbol']
                if symbol in alerted_stocks:
                    continue
                news = get_latest_news(symbol)
                send_alert(stock, news)
                alerted_stocks.add(symbol)

            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor_market_movers()
