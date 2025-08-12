# Crypto CEX Arbitrage Bot

## 📌 Overview
This bot performs automated **arbitrage trading** between two centralized cryptocurrency exchanges (CEX).  
It detects profitable price differences for a given trading pair (e.g., BTC/USDT) and executes buy/sell orders to capture the spread.

The bot uses:
- **Exchange APIs** to fetch live order book data.
- **Configurable thresholds** for minimum profit margins.
- **Automated order execution** with error handling and retries.

---

## ⚡ Features
- 🔄 Real-time price monitoring between two CEXs
- 📊 Spread calculation with adjustable profit threshold
- ⚠️ Balance and API error handling
- ⏱ Adjustable polling interval
- 📈 Support for both spot and futures (if exchanges allow)

---

## 🛠 Requirements
Python 3.9+ is recommended.  


Example dependencies (adjust for your code):
