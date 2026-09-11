import requests
import pandas as pd

BYBIT_TICKERS_URL = "https://api.bybit.com/v5/market/tickers"
BYBIT_KLINE_URL   = "https://api.bybit.com/v5/market/kline"

MIN_VOLUME_USD = 15_000_000
MAX_PRICE = 10.0
MIN_CHANGE_PCT = 10.0

BBW_LENGTH = 20
BBW_MULT = 2.0
BBW_MA_LENGTH = 5
BBW_EXPANSION_LENGTH = 125
BBW_CONTRACTION_LENGTH = 125
BBW_MID_RATIO = 0.5
SMA80_LENGTH = 80
TOTAL_CANDLES = 300

def _session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Referer': 'https://www.bybit.com/'
    })
    return s

def fetch_tickers():
    try:
        r = _session().get(BYBIT_TICKERS_URL,
                           params={'category': 'linear', 'limit': 1000},
                           timeout=20).json()
        return r['result']['list'] if r.get('retCode') == 0 else []
    except Exception:
        return []

def fetch_klines(symbol):
    try:
        r = _session().get(BYBIT_KLINE_URL,
                           params={'category': 'linear', 'symbol': symbol,
                                   'interval': '60', 'limit': TOTAL_CANDLES},
                           timeout=20).json()
        if r.get('retCode') != 0:
            return None
        kl = r['result']['list']
        kl.reverse()
        df = pd.DataFrame(kl, columns=['start','open','high','low','close','volume','turnover'])
        for c in ['open','high','low','close','volume','turnover']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.dropna()
    except Exception:
        return None

def _counter(df):
    if len(df) < TOTAL_CANDLES:
        return 0
    close, high, low = df['close'], df['high'], df['low']
    basis = close.rolling(BBW_LENGTH).mean()
    dev = BBW_MULT * close.rolling(BBW_LENGTH).std()
    bbw = ((basis + dev) - (basis - dev)) / basis * 100
    highest_exp = bbw.rolling(BBW_EXPANSION_LENGTH).max()
    lowest_con  = bbw.rolling(BBW_CONTRACTION_LENGTH).min()
    mid_line = lowest_con + (highest_exp - lowest_con) * BBW_MID_RATIO
    sma80 = close.rolling(SMA80_LENGTH).mean()

    counter = 0
    for i in range(len(df)):
        if i >= SMA80_LENGTH - 1:
            v = sma80.iloc[i]
            if pd.notna(v) and low.iloc[i] <= v <= high.iloc[i]:
                counter = 0
        if i >= BBW_EXPANSION_LENGTH - 1:
            b, e = bbw.iloc[i], highest_exp.iloc[i]
            if pd.notna(b) and pd.notna(e) and b >= e:
                counter = 4
        if i >= BBW_CONTRACTION_LENGTH - 1:
            b, m = bbw.iloc[i], mid_line.iloc[i]
            if pd.notna(b) and pd.notna(m) and i > 0:
                bp, mp = bbw.iloc[i-1], mid_line.iloc[i-1]
                if pd.notna(bp) and pd.notna(mp):
                    if ((bp < mp and b >= m) or (bp > mp and b <= m)
                            or abs(b - m) < 0.0001):
                        counter //= 2
    return counter

def _change(df, hours):
    if len(df) <= hours:
        return False
    cur, ago = df['close'].iloc[-1], df['close'].iloc[-(hours+1)]
    if ago <= 0:
        return False
    return ((cur - ago) / ago) * 100 > MIN_CHANGE_PCT

def scan():
    tickers = fetch_tickers()
    result = {"24hr": [], "48hr": [], "72hr": []}
    for t in tickers:
        sym = t.get('symbol', '')
        if not sym.endswith('USDT'):
            continue
        try:
            price = float(t.get('lastPrice', 0))
            vol = float(t.get('turnover24h', 0))
        except Exception:
            continue
        if not (0 < price < MAX_PRICE and vol >= MIN_VOLUME_USD):
            continue
        coin = sym.replace('USDT', '')
        df = fetch_klines(sym)
        if df is None or len(df) < TOTAL_CANDLES:
            continue
        if _counter(df) != 1:
            continue
        for h in (24, 48, 72):
            if _change(df, h):
                result[f"{h}hr"].append(coin)
    for k in result:
        result[k].sort()
    return result
