# bot.py
import os
import asyncio
import logging
from datetime import datetime, timedelta
from aiohttp import web
import ccxt.async_support as ccxt
import math
import json
import signal

# === CONFIG (via env vars / Fly secrets) ===
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY", "")
KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET", "")
PAPER = os.getenv("PAPER", "true").lower() in ("1", "true", "yes")
SYMBOL = os.getenv("SYMBOL", "BNB/USDT")
BASE_ASSET, QUOTE_ASSET = SYMBOL.split("/")
CYCLE_DELAY = float(os.getenv("CYCLE_DELAY", "0.5"))  # seconds between cycles
MIN_PROFIT_USDT = float(os.getenv("MIN_PROFIT_USDT", "0.5"))  # min expected profit
TRADE_SIZE_USDT = float(os.getenv("TRADE_SIZE_USDT", "10"))  # per-trade capital
MAX_CYCLES_PER_DAY = int(os.getenv("MAX_CYCLES_PER_DAY", "1000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# === logging ===
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("arb-bot")

# === Global runtime control ===
_running = False
_cycles_today = 0
_day_start = datetime.utcnow().date()

# === Create exchange clients ===
def create_exchanges():
    binance = ccxt.binance({
        "apiKey": BINANCE_API_KEY,
        "secret": BINANCE_API_SECRET,
        "enableRateLimit": True,
        "options": {"defaultType": "spot"}
    })
    kucoin = ccxt.kucoin({
        "apiKey": KUCOIN_API_KEY,
        "secret": KUCOIN_API_SECRET,
        "enableRateLimit": True,
    })
    return binance, kucoin

async def fetch_ticker_safe(exchange, symbol):
    try:
        return await exchange.fetch_ticker(symbol)
    except Exception as e:
        logger.warning("Ticker fetch failed for %s on %s: %s", symbol, getattr(exchange, 'id', 'ex'), e)
        return None

def estimate_profit(buy_price, sell_price, size, buy_fee_pct, sell_fee_pct):
    base_amount = size / buy_price  # amount of base asset we buy
    cost = size  # USDT spent
    fee_buy = cost * buy_fee_pct
    sale_proceeds = base_amount * sell_price
    fee_sell = sale_proceeds * sell_fee_pct
    net = sale_proceeds - fee_buy - fee_sell - cost
    return net

async def attempt_trade(binance, kucoin, direction, size_usdt):
    """
    direction: "binance->kucoin" means buy on Binance, sell on KuCoin
    We'll do a conservative simulation then place market orders if not in PAPER.
    """
    # fetch fees and tickers
    t_b = await fetch_ticker_safe(binance, SYMBOL)
    t_k = await fetch_ticker_safe(kucoin, SYMBOL)
    if not t_b or not t_k:
        return False, "ticker-missing"

    # prices
    b_ask = t_b.get("ask") or t_b.get("last")
    b_bid = t_b.get("bid") or t_b.get("last")
    k_ask = t_k.get("ask") or t_k.get("last")
    k_bid = t_k.get("bid") or t_k.get("last")
    if not all([b_ask, b_bid, k_ask, k_bid]):
        return False, "bad-prices"

    # approximate fees (exchange fee rates can be fetched from API in production)
    fee_pct_binance = 0.001  # 0.1% default
    fee_pct_kucoin = 0.001   # 0.1% default

    # direction logic: if direction == binance->kucoin, we buy at binance ask and sell at kucoin bid
    if direction == "binance->kucoin":
        buy_price = b_ask
        sell_price = k_bid
        buy_exchange = binance; sell_exchange = kucoin
    else:
        buy_price = k_ask
        sell_price = b_bid
        buy_exchange = kucoin; sell_exchange = binance

    estimated = estimate_profit(buy_price, sell_price, size_usdt, fee_pct_binance, fee_pct_kucoin)
    logger.debug("Estimated profit %s USDT for direction %s (buy @%.6f sell @%.6f) on size %s",
                 estimated, direction, buy_price, sell_price, size_usdt)

    if estimated < MIN_PROFIT_USDT:
        return False, f"profit-too-small ({estimated:.4f})"

    if PAPER:
        # simulate
        logger.info("[PAPER] Would execute: %s -- estimated profit: %s USDT", direction, estimated)
        return True, {"paper": True, "estimated": estimated, "buy_price": buy_price, "sell_price": sell_price}

    # === REAL TRADE - conservative approach ===
    try:
        # compute base amount to buy
        base_amount = (size_usdt / buy_price)
        precision = 6  # change per exchange requirements
        base_amount = float(ccxt.Exchange.prototype.amountToPrecision(ccxt.Exchange(), SYMBOL, base_amount)) if hasattr(ccxt.Exchange.prototype, 'amountToPrecision') else round(base_amount, 6)

        # Place buy market order (or use limit for more control)
        logger.info("Placing BUY on %s: amount=%s @ market", buy_exchange.id, base_amount)
        buy_order = await buy_exchange.create_market_buy_order(SYMBOL, base_amount)
        logger.debug("Buy order result: %s", buy_order)

        # Place sell market order on other exchange
        logger.info("Placing SELL on %s: amount=%s @ market", sell_exchange.id, base_amount)
        sell_order = await sell_exchange.create_market_sell_order(SYMBOL, base_amount)
        logger.debug("Sell order result: %s", sell_order)

        # NOTE: no cross-exchange settlement handling here! In production, you'd need asset routing,
        # funding checks, or use same-asset balance across exchanges OR atomic settlement solutions.

        return True, {"buy_order": buy_order, "sell_order": sell_order, "estimated": estimated}
    except Exception as e:
        logger.exception("Error executing trades: %s", e)
        return False, str(e)

async def arb_loop():
    global _running, _cycles_today, _day_start
    binance, kucoin = create_exchanges()
    try:
        while _running:
            now = datetime.utcnow()
            if now.date() != _day_start:
                _cycles_today = 0
                _day_start = now.date()

            if _cycles_today >= MAX_CYCLES_PER_DAY:
                logger.info("Reached max cycles per day (%s). Sleeping until tomorrow.", MAX_CYCLES_PER_DAY)
                await asyncio.sleep(60 * 60)  # sleep an hour
                continue

            t_b = await fetch_ticker_safe(binance, SYMBOL)
            t_k = await fetch_ticker_safe(kucoin, SYMBOL)
            if t_b and t_k:
                # compute simple spreads both ways
                b_ask = t_b.get("ask") or t_b.get("last")
                b_bid = t_b.get("bid") or t_b.get("last")
                k_ask = t_k.get("ask") or t_k.get("last")
                k_bid = t_k.get("bid") or t_k.get("last")

                # if buy on binance and sell on kucoin:
                profit1 = estimate_profit(b_ask, k_bid, TRADE_SIZE_USDT, 0.001, 0.001)
                # opposite direction
                profit2 = estimate_profit(k_ask, b_bid, TRADE_SIZE_USDT, 0.001, 0.001)

                if profit1 >= MIN_PROFIT_USDT:
                    ok, info = await attempt_trade(binance, kucoin, "binance->kucoin", TRADE_SIZE_USDT)
                    _cycles_today += 1
                    logger.info("Cycle %s result: %s %s", _cycles_today, ok, info)
                elif profit2 >= MIN_PROFIT_USDT:
                    ok, info = await attempt_trade(binance, kucoin, "kucoin->binance", TRADE_SIZE_USDT)
                    _cycles_today += 1
                    logger.info("Cycle %s result: %s %s", _cycles_today, ok, info)
                else:
                    logger.debug("No profitable spread found (p1=%.6f p2=%.6f).", profit1, profit2)
            else:
                logger.debug("Skipping cycle due to missing tickers.")

            await asyncio.sleep(CYCLE_DELAY)
    finally:
        await binance.close()
        await kucoin.close()
        logger.info("Exchanges closed.")

# === HTTP control API (Flask-like using aiohttp) ===
routes = web.RouteTableDef()

@routes.get("/start")
async def http_start(request):
    global _running, arb_task
    if _running:
        return web.json_response({"status":"already-running"})
    _running = True
    arb_task = asyncio.create_task(arb_loop())
    return web.json_response({"status":"started"})

@routes.get("/stop")
async def http_stop(request):
    global _running, arb_task
    if not _running:
        return web.json_response({"status":"already-stopped"})
    _running = False
    # wait for task to finish gracefully
    try:
        await asyncio.wait_for(arb_task, timeout=5)
    except Exception:
        pass
    return web.json_response({"status":"stopped"})

@routes.get("/status")
async def http_status(request):
    return web.json_response({
        "running": _running,
        "cycles_today": _cycles_today,
        "day_start": str(_day_start),
        "paper_mode": PAPER,
        "symbol": SYMBOL,
    })

async def on_shutdown(app):
    global _running
    _running = False
    logger.info("Shutting down...")

def main():
    app = web.Application()
    app.add_routes(routes)
    app.on_shutdown.append(on_shutdown)

    runner = web.AppRunner(app)
    loop = asyncio.get_event_loop()

    async def start_web():
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", "8080")))
        await site.start()
        logger.info("Control API started on port %s", os.getenv("PORT", "8080"))

    loop.run_until_complete(start_web())

    # handle signals for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.ensure_future(runner.cleanup()))

    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(runner.cleanup())

if __name__ == "__main__":
    main()
