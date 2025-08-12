from ast import Global
import requests
import time
import hmac
import hashlib
import threading
from urllib.parse import urlencode
import sys
import logging


FIRST_API_KEY = "xxx"
# second sex is mexc
SECOND_API_KEY = "xxx"
SECOND_API_SECRET = "xxx"

NobitexPair = "BTCUSDT"
SecondPair = "BTCUSDC"
# Track side positions
OpenPosition = False

counter = 0
#global catch error
logging.basicConfig(filename="bot_log.txt", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def global_exception_handler(exctype, value, tb):
    logging.error("Uncaught Exception:", exc_info=(exctype, value, tb))
    print("An unexpected error occurred! Check bot_log.txt for details.")

sys.excepthook = global_exception_handler

def get_mexc_server_time():
    try:
        response = requests.get("https://api.mexc.com/api/v3/time", timeout=5)
        return response.json().get("serverTime", int(time.time() * 1000))
    except requests.RequestException as e:
        logging.error(f"MEXC server time fetch failed: {e}")
        return int(time.time() * 1000)


# Function to fetch price from Nobitex
def get_nobitex_price():
    try:
        url = f"https://api.nobitex.ir/v3/orderbook/{NobitexPair}"
        headers = {"Authorization": f"Token {FIRST_API_KEY}"}
        response = requests.get(url, headers=headers)
        data = response.json()
        return float(data["bids"][0][0]), float(data["asks"][0][0])
    except requests.exceptions.Timeout:
        print("Timeout error: nobitex API took too long to respond.")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    return None, None  # Return None if request fails

def get_second_price():
    url = f"https://api.mexc.com/api/v3/depth?symbol={SecondPair}&limit=1"
    try:
        response = requests.get(url, timeout=5)  # Timeout set to 5 seconds
        response.raise_for_status()  # Raises an error for HTTP codes 4xx/5xx
        data = response.json()
        if not data.get("bids") or not data.get("asks"):
            logging.error("Empty order book received.")
            return None, None
        best_bid = float(data['bids'][0][0])  # Highest buy price
        best_ask = float(data['asks'][0][0])  # Lowest sell price
        return best_bid, best_ask
    except requests.exceptions.Timeout:
        print("Timeout error: second cex API took too long to respond.")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    return None, None  # Return None if request fails

# Function to fetch Nobitex account balances
def get_nobitex_balance():
    url = "https://api.nobitex.ir/users/wallets/list"
    headers = {"Authorization": f"Token {FIRST_API_KEY}"}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        balances = {wallet['currency']: float(wallet['balance']) for wallet in data['wallets']}
        return balances.get('usdt', 0), balances.get('btc', 0)
    except requests.exceptions.Timeout:
        print("Timeout error: nobitex get balance API took too long to respond.")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    return None, None  # Return None if request fails
# Function to fetch second account balances
def get_second_balance():
    url = "https://api.mexc.com/api/v3/account"

    params = {  
        "timestamp": get_mexc_server_time()
    }
    
    query_string = urlencode(params)
    signature = hmac.new(SECOND_API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    
    params["signature"] = signature  # Add signature to params
    headers = {
        "X-MEXC-APIKEY": SECOND_API_KEY,  # Ensure correct API Key header
        "Content-Type": "application/json"
    }    
    try:
        response = requests.get(url, headers=headers, params=params)  # Send as params, not JSON
        response.raise_for_status() 
        #print("MEXC response:", response.status_code, response.text)
        data = response.json()
        balances = {asset['asset']: float(asset['free']) for asset in data['balances']}
        return balances.get('USDC', 0), balances.get('BTC', 0) 
    except requests.exceptions.Timeout:
            print("Timeout error: second get balance API took too long to respond.")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    return None, None  # Return None if request fails
  

# Function to execute trade on Nobitex
def place_nobitex_order(type, price, quantity):
    url = "https://api.nobitex.ir/market/orders/add"
    headers = {"Authorization": f"Token {FIRST_API_KEY}", "content-type": "application/json"}
    data = {
        "execution": "limit",
        "srcCurrency": "btc",
        "dstCurrency": "usdt",
        "type": type,
        "amount": quantity,
        "price": price,
        "clientOrderId": "order1"
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()

# Function to place an order on Kucoin
def place_second_order(symbol, side, price, quantity):
    url = "https://api.mexc.com/api/v3/order"
    timestamp = str(int(time.time() * 1000))
    params = {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "quantity": quantity,
        "price": price,
        "timeInForce": "GTC",
        "timestamp": get_mexc_server_time(),
        "recvWindow": 5000  # Increase recvWindow (default is 500ms)
    }
    
    query_string = urlencode(params)
    signature = hmac.new(SECOND_API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    
    params["signature"] = signature  # Add signature to params
    headers = {
        "X-MEXC-APIKEY": SECOND_API_KEY  # Ensure correct API Key header
    }
    
    try:
        response = requests.post(url, headers=headers, params=params)  # Send as params, not JSON
        response.raise_for_status() 
        #print("MEXC response:", response.status_code, response.text)
        return response
    except Exception as e:
      logging.error(f"MEXC order failed: {e}")
      return response

def fetch_prices():
    prices = {}
    thread1 = threading.Thread(target=lambda: prices.update({"nobitex": get_nobitex_price()}))
    thread2 = threading.Thread(target=lambda: prices.update({"second": get_second_price()}))
    thread1.start()
    thread2.start()
    thread1.join(timeout=10)
    thread2.join(timeout=10)
    
    # Debugging log
    if prices.get("nobitex") is None or prices.get("second") is None:
        print("API fetch failed! Nobitex:", prices.get("nobitex"), "SECOND:", prices.get("second"))

    return prices

# Function to check arbitrage opportunity
def check_arbitrage():   
    global OpenPosition

    prices = fetch_prices()  
    
    if "nobitex" not in prices or "second" not in prices:
        print("Skipping arbitrage check due to API failure.")
        return
    
    nobitex_bid, nobitex_ask = prices["nobitex"]
    second_bid, second_ask = prices["second"]
    
    if nobitex_bid is None or nobitex_ask is None:
       print("Skipping arbitrage check due to Nobitex API failure.")
       return
    
    if second_bid is None or second_ask is None:
       print("Skipping arbitrage check due to SECOND API failure.")
       return
   
 

    if ((nobitex_ask < (second_bid * 0.994)) and  OpenPosition == False):  # Consider fees (~0.6% target difference)
        print(f"BUY on Nobitex at {nobitex_ask}, SELL on SECOND at {second_bid}  PTOFIT:{round(second_bid-nobitex_ask,2)}")
        global counter
        counter += 1
        nobitex_usdt_balance, nobitex_btc_balance = get_nobitex_balance()
        second_usdc_balance, second_btc_balance = get_second_balance()
        btc_quantity = 0.0005        
        max_btc_to_buy = nobitex_usdt_balance / nobitex_ask
        if(second_usdc_balance == None or  nobitex_usdt_balance == None):
            print("Skipping arbitrage due to balance failure.")
            return
        n_response = place_nobitex_order("buy", nobitex_ask, max_btc_to_buy )
        m_response = place_second_order("BTCUSDC", "SELL", second_bid, second_btc_balance)
        if n_response.get("status") != "ok":
           print("nobitex trade failed")
        if m_response.status_code != 200:
           print("second trade failed")
        if(m_response.status_code == 200 and n_response.get("status") == "ok"):
           OpenPosition = True
        
       
    elif((second_ask < (nobitex_bid * 1.001 )) and  OpenPosition == True):  # Consider fees (~0.6% target difference)
        print(f"closed position, BUY on Second at {second_ask}, SELL on Nobitex at {nobitex_bid}")
        nobitex_usdt_balance, nobitex_btc_balance = get_nobitex_balance()
        second_usdc_balance, second_btc_balance = get_second_balance()
        btc_quantity = 0.0005
        max_btc_to_buy = second_usdc_balance / second_ask
        if(second_usdc_balance == None or  nobitex_usdt_balance == None):
            print("Skipping arbitrage due to balance failure.")
            return
        n_response = place_nobitex_order("sell", nobitex_bid, nobitex_btc_balance )
        m_response = place_second_order("BTCUSDC", "BUY", second_ask, max_btc_to_buy)
        if n_response.get("status") != "ok":
            print("nobitex trade failed")
        if m_response.status_code != 200:
            print("second trade failed")
        if(m_response.status_code == 200 and n_response.get("status") == "ok"):
            OpenPosition = False
        
       
    else:
            profit_1 = round(second_bid - nobitex_ask,0)
            profit_2 = round(nobitex_bid - second_ask,0)
            print(f"waiting   ({OpenPosition}).  diff: {profit_1} and {profit_2}  counter:{counter}")

 
        
# grid strategy
# Grid Trading Parameters
PAIR = "ETHUSDC"
ORDER_SIZE = 3  # USD value per order
SellOrders ={}
BuyOrders ={}
base_spacing = 5
        
def sign_request(params, secret_key):
    """ Generate HMAC SHA256 signature """
    query_string = "&".join([f"{key}={params[key]}" for key in sorted(params)])
    signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

def get_open_orders():
    url = "https://api.mexc.com/api/v3/openOrders"
    
    timestamp = int(time.time() * 1000)  # Current timestamp in milliseconds
    params = {
        "symbol": PAIR,
        "timestamp": timestamp
    }
    
    params["signature"] = sign_request(params,SECOND_API_SECRET)

    headers = {
        "X-KUCOIN-APIKEY": SECOND_API_KEY
    }
    try:
     response = requests.get(url, params=params, headers=headers)
     data = response.json() 
    except:
     data = {}
    return data

# Run the arbitrage checker in a loop
while True:
    check_arbitrage()     
    time.sleep(10)

