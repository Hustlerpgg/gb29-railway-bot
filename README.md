# GB29 Railway Bot

Webhook-Testserver für TradingView-Alerts der GB29-Strategie.

Der Bot läuft auf Railway, empfängt JSON-Signale von TradingView, prüft ein Secret, blockiert doppelte Alerts und simuliert Positionen im PAPER-Modus.

## Dateien

```text
main.py
requirements.txt
Dockerfile
railway.json
start.sh
Procfile
.env.example
README.md
```

## Railway Variables

In Railway unter `Variables` eintragen:

```text
BOT_SECRET=test123
EXECUTION_MODE=PAPER
ALLOW_LIVE=false
MAX_POSITION=1
DUPLICATE_TTL_SECONDS=60
```

Wichtig: Echte API-Keys und Secrets niemals in GitHub speichern. Nur in Railway Variables eintragen.

## Railway Deploy

1. GitHub-Repo mit diesen Dateien erstellen.
2. Railway öffnen.
3. `New Project` → `Deploy from GitHub repo`.
4. Repo auswählen.
5. Variables setzen.
6. Deploy/Redeploy starten.
7. Unter `Networking` eine Domain generieren.

## Health Check

Nach dem Deploy im Browser öffnen:

```text
https://DEINE-RAILWAY-URL/health
```

Erwartete Antwort:

```json
{
  "ok": true,
  "mode": "PAPER"
}
```

## Webhook URL

Diese URL später in TradingView verwenden:

```text
https://DEINE-RAILWAY-URL/webhook
```

## TradingView Alert

Alert-Einstellung:

```text
Condition: deine Strategie
Event: Strategy order fills
Message: {{strategy.order.alert_message}}
Webhook URL: https://DEINE-RAILWAY-URL/webhook
```

## Beispiel JSON Long

```json
{
  "secret": "test123",
  "strategy": "GB29",
  "broker": "paper",
  "account": "SIM",
  "symbol": "BTCUSD",
  "action": "BUY",
  "qty": 1,
  "order_type": "MKT",
  "reason": "gb_entry_long"
}
```

## Beispiel JSON Short

```json
{
  "secret": "test123",
  "strategy": "GB29",
  "broker": "paper",
  "account": "SIM",
  "symbol": "BTCUSD",
  "action": "SELL",
  "qty": 1,
  "order_type": "MKT",
  "reason": "gb_entry_short"
}
```

## Beispiel JSON Long schließen

```json
{
  "secret": "test123",
  "strategy": "GB29",
  "broker": "paper",
  "account": "SIM",
  "symbol": "BTCUSD",
  "action": "CLOSE_LONG",
  "qty": 1,
  "reason": "target_time"
}
```

## Beispiel JSON Short schließen

```json
{
  "secret": "test123",
  "strategy": "GB29",
  "broker": "paper",
  "account": "SIM",
  "symbol": "BTCUSD",
  "action": "CLOSE_SHORT",
  "qty": 1,
  "reason": "target_time"
}
```

## Lokaler Test optional

Nur nötig, wenn lokal getestet werden soll:

```bash
pip install -r requirements.txt
BOT_SECRET=test123 EXECUTION_MODE=PAPER uvicorn main:app --host 0.0.0.0 --port 8000
```

Dann öffnen:

```text
http://127.0.0.1:8000/health
```

## Status

Aktueller Modus: PAPER.

LIVE-Ausführung ist im Bot noch bewusst deaktiviert. Erst nach stabilem Paper-Test Tradovate/cTrader/MT5-Anbindung einbauen.
