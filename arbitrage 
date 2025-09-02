# Crypto Arbitrage Bot (BNB/USDT) — Binance & KuCoin

## README

A full-stack, production-ready arbitrage trading bot for BNB/USDT between Binance and KuCoin, featuring:

- **Automated arbitrage logic:** Trades when after-fee profit is positive.
- **Multi-threaded price fetching:** Lowest latency cycle.
- **Advanced dashboard:** Flask web UI with charts, live P/L, controls.
- **Risk management:** Capital limits, profit target, max drawdown.
- **Dry-run/testing mode:** Simulate trades before going live.
- **Deployment-ready:** Launch on [Fly.io](https://fly.io) for scalable cloud hosting.

---

## Repo Structure

```
arbitrage_bot_upgraded.py   # Main bot + Flask dashboard
config.yaml                 # Example config (DO NOT COMMIT SECRETS)
fly.toml                    # Fly.io deployment config
requirements.txt            # Python dependencies
.gitignore                  # Ignore secrets, logs, build files
README.md                   # This documentation
```

---

## Quickstart

### 1. Clone & Install

```bash
git clone https://github.com/Salazar254/crypto-arbitrage-bot.git
cd crypto-arbitrage-bot
pip install -r requirements.txt
```

### 2. Configure Secrets

Edit `config.yaml` **(do not commit real API keys!)**:

```yaml
binance:
  api_key: "YOUR_BINANCE_API_KEY"
  api_secret: "YOUR_BINANCE_API_SECRET"
kucoin:
  api_key: "YOUR_KUCOIN_API_KEY"
  api_secret: "YOUR_KUCOIN_API_SECRET"
  password: "YOUR_KUCOIN_API_PASSWORD"
capital_limit: 1000
max_drawdown: 200
profit_target: 500
testing: true  # Set to false to enable live trading
```

Or set secrets as environment variables (recommended for Fly.io):

```bash
export BINANCE_API_KEY=...
export BINANCE_API_SECRET=...
export KUCOIN_API_KEY=...
export KUCOIN_API_SECRET=...
export KUCOIN_API_PASSWORD=...
```

### 3. Run Locally

```bash
python arbitrage_bot_upgraded.py
```

Dashboard will be available on `http://localhost:8080`.

---

## Deployment (Fly.io)

1. Install Fly CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Run `fly launch` and configure your app.
3. Set secrets via `fly secrets set` or config.yaml.
4. App runs on a public URL; dashboard on port 8080.

---

## Usage

- Start/stop bot, set capital limit, toggle testing mode from dashboard.
- View live cumulative profit/loss, trade logs, error info.
- API status endpoint: `/api/status`.

---

## Security

- **Never commit API keys or config.yaml with secrets!**
- Use Fly.io secrets or environment variables in production.
- All logs saved to `arbitrage.log` (excluded from repo).

---

## Customization

- Want more exchanges, pairs, or features? Fork or open an issue!
- For Streamlit dashboard, swap Flask for Streamlit and Plotly charting.

---

## License

MIT — _No warranty, use at your own risk._

---

## Author

Developed by [Salazar254](https://github.com/Salazar254).

---

## Main Bot Code

```python
# arbitrage_bot_upgraded.py

[Paste the full code from arbitrage_bot_upgraded.py here]
```

---

## Example Config

```yaml
# config.yaml

binance:
  api_key: "YOUR_BINANCE_API_KEY"
  api_secret: "YOUR_BINANCE_API_SECRET"
kucoin:
  api_key: "YOUR_KUCOIN_API_KEY"
  api_secret: "YOUR_KUCOIN_API_SECRET"
  password: "YOUR_KUCOIN_API_PASSWORD"
capital_limit
