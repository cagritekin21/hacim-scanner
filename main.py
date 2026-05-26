import requests
import time
from datetime import datetime

TELEGRAM_TOKEN = "8769168818:AAE8_Jwn24O6O4-G_McNMLce0gR0ze5guNo"
TELEGRAM_CHAT_ID = "1216988618"

BINANCE_BASE = "https://fapi.binance.com"
INTERVAL = "5m"
HACIM_CARPAN = 2
TARAMA_SURESI = 300

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Telegram hatası: {e}")

def get_all_usdt_symbols():
    url = f"{BINANCE_BASE}/fapi/v1/exchangeInfo"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        return [s['symbol'] for s in data['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
    except:
        return []

def get_klines(symbol):
    url = f"{BINANCE_BASE}/fapi/v1/klines"
    params = {"symbol": symbol, "interval": INTERVAL, "limit": 11}
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except:
        return []

def get_funding_rate(symbol):
    url = f"{BINANCE_BASE}/fapi/v1/fundingRate"
    params = {"symbol": symbol, "limit": 1}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data:
            return float(data[-1]['fundingRate']) * 100
    except:
        pass
    return None

def get_open_interest_history(symbol):
    url = f"{BINANCE_BASE}/futures/data/openInterestHist"
    params = {"symbol": symbol, "period": "5m", "limit": 2}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if len(data) >= 2:
            onceki = float(data[0]['sumOpenInterest'])
            simdi = float(data[1]['sumOpenInterest'])
            return round(((simdi - onceki) / onceki) * 100, 2)
    except:
        pass
    return None

def get_price_change(symbol):
    url = f"{BINANCE_BASE}/fapi/v1/klines"
    params = {"symbol": symbol, "interval": "15m", "limit": 2}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if len(data) >= 2:
            acilis = float(data[-1][1])
            kapanis = float(data[-1][4])
            return round(((kapanis - acilis) / acilis) * 100, 2)
    except:
        pass
    return None

def analyze_signal(kat, funding, oi_degisim, fiyat_degisim):
    guc = 0
    yon = None
    mesajlar = []
    if kat >= HACIM_CARPAN:
        guc += 1
        mesajlar.append(f"📊 Hacim: {kat}x patlama ✅")
    if funding is not None:
        if funding > 0.1:
            guc += 1
            yon = "SHORT"
            mesajlar.append(f"💰 Funding: %{funding:.3f} (Yüksek → Short baskısı) ⚠️")
        elif funding < -0.1:
            guc += 1
            yon = "LONG"
            mesajlar.append(f"💰 Funding: %{funding:.3f} (Düşük → Long baskısı) ⚠️")
        else:
            mesajlar.append(f"💰 Funding: %{funding:.3f} (Normal)")
    if oi_degisim is not None:
        if oi_degisim > 0.5:
            guc += 1
            mesajlar.append(f"📈 OI: +%{oi_degisim} artıyor ✅")
        elif oi_degisim < -0.5:
            mesajlar.append(f"📉 OI: %{oi_degisim} düşüyor ⚠️")
        else:
            mesajlar.append(f"📊 OI: %{oi_degisim} (Sabit)")
    if fiyat_degisim is not None:
        if abs(fiyat_degisim) > 1:
            guc += 1
            if fiyat_degisim > 0:
                mesajlar.append(f"🟢 Fiyat: +%{fiyat_degisim} yukarı ✅")
                if not yon:
                    yon = "LONG"
            else:
                mesajlar.append(f"🔴 Fiyat: %{fiyat_degisim} aşağı ✅")
                if not yon:
                    yon = "SHORT"
        else:
            mesajlar.append(f"➡️ Fiyat: %{fiyat_degisim} (Küçük hareket)")
    return guc, yon, mesajlar

def check_coin(symbol):
    klines = get_klines(symbol)
    if not klines or len(klines) < 11:
        return None
    son_hacim = float(klines[-1][5])
    onceki = [float(k[5]) for k in klines[-11:-1]]
    ortalama = sum(onceki) / len(onceki)
    if ortalama == 0:
        return None
    kat = son_hacim / ortalama
    if kat < HACIM_CARPAN:
        return None
    funding = get_funding_rate(symbol)
    oi_degisim = get_open_interest_history(symbol)
    fiyat_degisim = get_price_change(symbol)
    fiyat = float(klines[-1][4])
    guc, yon, mesajlar = analyze_signal(round(kat, 2), funding, oi_degisim, fiyat_degisim)
    return {"symbol": symbol, "fiyat": fiyat, "kat": round(kat, 2), "guc": guc, "yon": yon, "mesajlar": mesajlar}

def format_message(sonuc, now):
    guc = sonuc['guc']
    yon = sonuc['yon']
    if guc >= 4:
        guc_emoji = "🔥🔥🔥 ÇOK GÜÇLÜ"
    elif guc == 3:
        guc_emoji = "🔥🔥 GÜÇLÜ"
    elif guc == 2:
        guc_emoji = "🔥 ORTA"
    else:
        guc_emoji = "⚡ ZAYIF"
    if yon == "LONG":
        yon_text = "🟢 LONG düşünülebilir"
    elif yon == "SHORT":
        yon_text = "🔴 SHORT düşünülebilir"
    else:
        yon_text = "❓ Yön belirsiz, grafiğe bak"
