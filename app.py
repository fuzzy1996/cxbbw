from flask import Flask, render_template_string
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
</style>
</head>
<body>
  <h1>CXBBW Crypto Screener</h1>
  <div class="ts">{{ ts }}</div>
  {% for period in ['24hr','48hr','72hr'] %}
    <h2>[{{ period }}]</h2>
    {% set coins = data[period] %}
    {% if coins %}
      {% for c in coins %}
        <a target="_blank"
           href="https://www.tradingview.com/chart/cq0P5xfh/?symbol=BYBIT%3A{{ c }}USDT.P">
          🟣 {{ c }}
        </a>
      {% endfor %}
    {% else %}
      <div class="none">(none)</div>
    {% endif %}
  {% endfor %}
</body>
</html>
"""

@app.route("/")
def index():
    data = logic.scan()
    ts = "Scanned " + datetime.now().strftime("%H:%M:%S")
    return render_template_string(PAGE, data=data, ts=ts)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
