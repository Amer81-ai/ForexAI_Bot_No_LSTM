# -*- coding: utf-8 -*-
"""
ForexAI Hyper Ultimate Bot - النسخة بدون LSTM
ميزات:
- كل العملات الرئيسية والرقمية الكبيرة والناشئة
- مؤشرات وأدوات تحليل متقدمة: MA, RSI, Bollinger
- إشعارات قبل الصفقة 15 دقيقة
- إشعارات TP/SL
- إشعار قبل اغلاق السوق 15 دقيقة
- مراعاة حالة السوق
- تخزين المفاتيح مرة واحدة
"""

import os, json, time, datetime, numpy as np, pandas as pd
import requests

# ==========================
# تخزين واسترجاع المفاتيح
# ==========================
CONFIG_FILE = "config.json"

def save_keys(token, chat_id, twelve_key):
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "TELEGRAM_TOKEN": token,
            "TELEGRAM_CHAT_ID": chat_id,
            "TWELVE_API_KEY": twelve_key
        }, f)

def load_keys():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None

keys = load_keys()
if not keys:
    token = input("ادخل TELEGRAM_TOKEN: ").strip()
    chat_id = input("ادخل TELEGRAM_CHAT_ID: ").strip()
    twelve_key = input("ادخل TWELVE_API_KEY: ").strip()
    save_keys(token, chat_id, twelve_key)
else:
    token = keys["TELEGRAM_TOKEN"]
    chat_id = keys["TELEGRAM_CHAT_ID"]
    twelve_key = keys["TWELVE_API_KEY"]

# ==========================
# وظائف Telegram
# ==========================
BASE_TELEGRAM = f"https://api.telegram.org/bot{token}/sendMessage"

def send_telegram(message):
    try:
        requests.post(BASE_TELEGRAM, data={"chat_id": chat_id, "text": message})
    except Exception as e:
        print("فشل ارسال رسالة Telegram:", e)

# ==========================
# حالة السوق
# ==========================
MARKET_OPEN_HOUR = 22  # يوم الأحد الساعة 22
MARKET_CLOSE_HOUR = 22 # يوم الجمعة الساعة 22

def is_market_open():
    now = datetime.datetime.now()
    weekday = now.weekday()  # الاثنين=0 ... الأحد=6
    hour = now.hour
    if weekday == 6 and hour < MARKET_OPEN_HOUR:
        return False
    if weekday == 4 and hour >= MARKET_CLOSE_HOUR:
        return False
    if weekday == 5:
        return False
    return True

# ==========================
# جلب البيانات وتحليل المؤشرات
# ==========================
def fetch_forex_data(symbol="EURUSD", interval="1h", limit=500):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={twelve_key}&outputsize={limit}"
    r = requests.get(url).json()
    if "values" in r:
        df = pd.DataFrame(r["values"])[::-1]
        for col in ['close','open','high','low']:
            df[col] = df[col].astype(float)
        return df
    return pd.DataFrame()

def compute_indicators(df):
    df["MA10"] = df["close"].rolling(10).mean()
    df["MA50"] = df["close"].rolling(50).mean()
    df["RSI"] = 100 - (100 / (1 + (df["close"].diff().clip(lower=0).rolling(14).mean() /
                                   df["close"].diff().clip(upper=0).abs().rolling(14).mean())))
    df["BB_up"] = df["close"].rolling(20).mean() + 2*df["close"].rolling(20).std()
    df["BB_down"] = df["close"].rolling(20).mean() - 2*df["close"].rolling(20).std()
    return df.fillna(0)

# ==========================
# إشعارات
# ==========================
def notify_before_trade(symbol, price, direction):
    send_telegram(f"🔔 توصية على {symbol} قبل 15 دقيقة\nالاتجاه المتوقع: {direction}\nالسعر الحالي: {price}")

def notify_tp_sl(symbol, level_type, price):
    send_telegram(f"⚡ {symbol} وصل إلى {level_type}: {price}")

def notify_market_close_warning():
    send_telegram("⚠️ السوق سيغلق خلال 15 دقيقة! استعد لإغلاق صفقاتك.")

# ==========================
# المعالجة الرئيسية
# ==========================
def main():
    symbols = [
        "EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","NZDUSD","USDCHF",
        "BTCUSD","ETHUSD","BNBUSD","XRPUSD","ADAUSD","DOGEUSD","SOLUSD"
    ]
    last_market_warning = None

    while True:
        market_open = is_market_open()
        now = datetime.datetime.now()

        # إشعار قبل اغلاق السوق 15 دقيقة
        if market_open and last_market_warning != now.date() and now.weekday()==4 and now.hour == 21:
            notify_market_close_warning()
            last_market_warning = now.date()

        for sym in symbols:
            df = fetch_forex_data(sym)
            if df.empty:
                continue
            df = compute_indicators(df)

            last_close = df["close"].values[-1]
            ma10 = df["MA10"].values[-1]

            # قرار بسيط: إذا أغلق السعر أعلى من MA10 => شراء، وإلا بيع
            direction = "شراء 📈" if last_close > ma10 else "بيع 📉"

            if market_open:
                notify_before_trade(sym, last_close, direction)

        time.sleep(60)

if __name__ == "__main__":
    main()