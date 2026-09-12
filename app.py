from flask import Flask, render_template_string, request
from datetime import datetime
import logic

app = Flask(__name__)

PAGE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CXBBW</title>
<style>
  body{font-family:monospace;background:#0d0d0d;color:#eee;
       margin:0;padding:14px;font-size:16px}
  h1{font-size:18px;margin:0 0 6px}
  .ts{color:#666;font-size:12px;margin-bottom:14px}
  h2{color:#aaa;margin:18px 0 6px;font-size:13px;
     text-transform:uppercase;letter-spacing:1px}
  a{display:block;color:#c77dff;text-decoration:none;
    padding:12px 6px;border-bottom:1px solid #1a1a1a}
  a:active{background:#1a1a1a}
  .none{color:#555;padding:6px}
  .debug{background:#1a1a1a;padding:10px;margin-top:20px;
         border-radius:6px;font-size:12px;color:#999}
  .debug b{color:#c77dff}
  .toggle{display:inline-block;padding:6px 12px;background:#333;
          color:#eee;text-decoration:none;border-radius:4px;
          margin-bottom:12px;font-size:12px}
</style>
</head>
<body>
  <h1>CXBBW Crypto Screener</h1>
  <div class="ts">{{ ts }}</div>

  <a class="toggle" href="/?debug={{ 0 if debug else 1 }}">
    {{ "Hide debug" if debug else "Show debug" }}
  </a>

  {% for period in ['24hr','48hr','72hr'] %}
    <h2>[{{ period }}]</h2>
    {% set coins = data[period] %}
    {% if coins %}
      {% for c in coins %}
        <a target="_blank"
           href="https://www.tradingview.com/chart/cq0P5xfh/?symbol=BINANCE%3A{{ c }}USDT.P">
          🟣 {{ c }}
        </a>
      {% endfor %}
    {% else %}
      <div class="none">(none)</div>
    {% endif %}
  {% endfor %}

  {% if debug %}
    <div class="debug">
      <b>Diagnostics</b><br>
      Tickers fetched: {{ stats.tickers }}<br>
      Passed price/volume filter: {{ stats.passed_filter }}<br>
      Passed BBW counter==1: {{ stats.passed_counter }}<br>
      Passed change filter: {{ stats.passed_change }}<br>
      Final matches: {{ stats.final }}<br>
      <br>
      <b>Sample of near-misses (counter==1 but no change filter):</b><br>
      {% if stats.near_misses %}
        {{ stats.near_misses | join(', ') }}
      {% else %}
        (none — means counter filter is killing everything)
      {% endif %}
      <br><br>
      <b>Last error:</b><br>
      {{ stats.last_error }}
    </div>
  {% endif %}
</body>
</html>
"""

@app.route("/")
def index():
    debug = request.args.get("debug") == "1"
    data, stats = logic.scan_with_stats()
    ts = "Scanned " + datetime.now().strftime("%H:%M:%S")
    return render_template_string(PAGE, data=data, ts=ts, debug=debug, stats=stats)

@app.route("/test")
def test():
    import requests
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/ping", timeout=10)
        r2 = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr",
                          params={"symbol": "BTCUSDT"}, timeout=10)
        return (f"ping status={r.status_code}<br>"
                f"ticker status={r2.status_code}<br><br>"
                f"body={r2.text[:600]}")
    except Exception as e:
        return f"EXCEPTION: {type(e).__name__}: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
