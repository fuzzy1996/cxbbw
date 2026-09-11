import requests
import pandas as pd

BYBIT_TICKERS_URL = "https://api.bybit.com/v5/market/tickers"
BYBIT_KLINE_URL   = "https://api.bybit.com/v5/market/kline"

MIN_VOLUME_USD = 1_000_000
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
MAX_KLINE_FETCHES = 60

def _session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Referer': 'https://www.bybit.com/'
    })
    return s

def fetch_tickers(error_out=None):
    try:
        r = _session().get(
            BYBIT_TICKERS_URL,
            params={'category': 'linear', 'limit': 1000},
            timeout=15,
        )
        if error_out is not None:
            error_out.append(f"tickers HTTP {r.status_code}")
        if r.status_code != 200:
            return []
        data = r.json()
        if data.get('retCode') != 0:
            if error_out is not None:
                error_out.append(
                    f"retCode={data.get('retCode')} msg={data.get('retMsg')}"
                )
            return []
        return data['result']['list']
    except Exception as e:
        if error_out is not None:
            error_out.append(f"tickers EXC {type(e).__name__}: {e}")
        return []

def fetch_klines(symbol):
    try:
        r = _session().get(
            BYBIT_KLINE_URL,
            params={
                'category': 'linear',
                'symbol': symbol,
                'interval': '60',
                'limit': TOTAL_CANDLES,
            },
            timeout=15,
        ).json()
        if r.get('retCode') != 0:
            return None
        kl = r['result']['list']
        kl.reverse()
        df = pd.DataFrame(kl, columns=[
            'start', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])
        for c in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
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

def scan_with_stats():
    errors = []
    tickers = fetch_tickers(error_out=errors)
    stats = {
        "tickers": len(tickers),
        "passed_filter": 0,
        "passed_counter": 0,
        "passed_change": 0,
        "final": 0,
        "near_misses": [],
        "last_error": " | ".join(errors) if errors else "(no errors)",
    }
    result = {"24hr": [], "48hr": [], "72hr": []}

    # Cheap pre-filter using ticker data only (no klines)
    prelim = []
    for t in tickers:
        sym = t.get('symbol', '')
        if not sym.endswith('USDT'):
            continue
        try:
            price = float(t.get('lastPrice', 0))
            vol   = float(t.get('turnover24h', 0))
            chg24 = float(t.get('price24hPcnt', 0)) * 100  # Bybit gives decimal
        except Exception:
            continue
        if not (0 < price < MAX_PRICE and vol >= MIN_VOLUME_USD):
            continue
        if chg24 < MIN_CHANGE_PCT:
            continue
        prelim.append((sym, chg24))

    prelim.sort(key=lambda x: x[1], reverse=True)
    prelim = prelim[:MAX_KLINE_FETCHES]

    for sym, _ in prelim:
        stats["passed_filter"] += 1
        coin = sym.replace('USDT', '')
        df = fetch_klines(sym)
        if df is None or len(df) < TOTAL_CANDLES:
            continue
        if _counter(df) != 1:
            continue
        stats["passed_counter"] += 1
        stats["near_misses"].append(coin)
        matched_any = False
        for h in (24, 48, 72):
            if _change(df, h):
                result[f"{h}hr"].append(coin)
                matched_any = True
        if matched_any:
            stats["passed_change"] += 1

    for k in result:
        result[k].sort()
    stats["final"] = len(set(result["24hr"]) | set(result["48hr"]) | set(result["72hr"]))
    stats["near_misses"] = stats["near_misses"][:20]
    return result, stats

def scan():
    data, _ = scan_with_stats()
    return data
