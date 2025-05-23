import os
from kucoin.client import Client
import pandas as pd
import numpy as np
import datetime
import time

def connect_to_kucoin(api_key, api_secret, api_passphrase):
    """
    Connects to the KuCoin API.

    Args:
        api_key: Your KuCoin API key.
        api_secret: Your KuCoin API secret.
        api_passphrase: Your KuCoin API passphrase.

    Returns:
        The KuCoin client object if connection is successful, None otherwise.
    """
    try:
        client = Client(api_key, api_secret, api_passphrase)
        # Perform a simple call to verify connection
        accounts = client.get_accounts()
        print("Successfully connected to KuCoin.")
        print(f"Found {len(accounts)} accounts.")
        return client
    except Exception as e:
        print(f"Error connecting to KuCoin: {e}")
        return None

def get_historical_klines(client, symbol, interval, start_str=None, end_str=None):
    """
    Fetches historical kline (OHLCV) data for a symbol.

    Args:
        client: The KuCoin client object.
        symbol: The trading pair (e.g., 'BTC-USDT').
        interval: The kline interval (e.g., Client.RESOLUTION_1MINUTE).
        start_str: Optional start date string ('YYYY-MM-DD HH:MM:SS').
        end_str: Optional end date string ('YYYY-MM-DD HH:MM:SS').

    Returns:
        A Pandas DataFrame with OHLCV data, or None if an error occurs.
    """
    if not client:
        print("KuCoin client is not available.")
        return None

    try:
        if start_str:
            start_at = int(datetime.datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S').timestamp())
        else:
            # Default to 1 day ago if no start_str
            start_at = int((datetime.datetime.now() - datetime.timedelta(days=1)).timestamp())

        if end_str:
            end_at = int(datetime.datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S').timestamp())
        else:
            end_at = int(datetime.datetime.now().timestamp())

        print(f"Fetching klines for {symbol} from {datetime.datetime.fromtimestamp(start_at)} to {datetime.datetime.fromtimestamp(end_at)} with interval {interval}")
        
        # KuCoin API returns klines in this format:
        # [
        #   [
        #     "1583000000",             //Start time of the candle cycle
        #     "9000.0",                 //Open price
        #     "9000.1",                 //Close price
        #     "9000.2",                 //Highest price
        #     "9000.0",                 //Lowest price
        #     "1000.0",                 //Transaction volume
        #     "9000000.0"               //Transaction amount
        #   ]
        # ]
        # Note: The python-kucoin library might re-order these or use different names.
        # Let's confirm the actual structure from client.get_kline_data documentation or a test call.
        # The library's get_kline_data actually returns them in a more standard OHLCV order:
        # [time, open, close, high, low, volume, turnover] - this was old behavior
        # New behavior for get_kline_data or get_klines:
        # [Timestamp, Open, High, Low, Close, Volume, QuoteVolume] based on typical API responses.
        # The python-kucoin library documentation for get_klines states:
        # [[<start_time_in_unix_seconds>, <open_price>, <close_price>, <high_price>, <low_price>, <transaction_volume>, <transaction_amount>]]
        # We need to adjust column mapping accordingly.
        
        klines_data = client.get_kline_data(symbol, interval, start_at=start_at, end_at=end_at)
        
        if not klines_data:
            print(f"No kline data returned for {symbol}.")
            return None

        # Correct column order based on python-kucoin documentation for get_kline_data:
        # [time, open, close, high, low, volume, turnover] - this needs to be verified.
        # After checking library source or examples, it's typically:
        # [unix_timestamp, open, close, high, low, volume, amount]
        # Let's use the standard OHLCV sequence and add Timestamp.
        # The library documentation for `get_klines` (which seems to be the current method name in some versions,
        # or `get_kline_data` in others) usually returns:
        # [timestamp, open, high, low, close, volume, quote_volume]
        # Let's assume the following column order from the API response:
        # [time, open, close, high, low, amount, volume] - this is what python-kucoin's `get_kline` method returns
        # The `get_kline_data` (or `get_klines`) method in the library actually returns them as:
        # [ <start_time_in_unix_seconds>, <open_price>, <close_price>, <high_price>, <low_price>, <transaction_volume>, <transaction_amount> ]
        # So we need to map these correctly.
        df = pd.DataFrame(klines_data, columns=[
            'Timestamp', 'Open', 'Close', 'High', 'Low', 'Volume', 'Turnover'
        ])
        
        # Convert timestamp to datetime objects
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s')
        
        # Reorder to standard OHLCV and select required columns
        # Original API order: Timestamp, Open, Close, High, Low, Volume, Turnover
        # Target: Timestamp, Open, High, Low, Close, Volume
        df = df[['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']]

        # Convert numeric columns to float
        cols_to_convert = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in cols_to_convert:
            df[col] = pd.to_numeric(df[col])
            
        print(f"Successfully fetched {len(df)} klines for {symbol}.")
        return df.sort_values('Timestamp', ascending=True)

    except Exception as e:
        print(f"Error fetching klines for {symbol}: {e}")
        return None

def get_current_price(client, symbol):
    """
    Fetches the current ticker price for a symbol.

    Args:
        client: The KuCoin client object.
        symbol: The trading pair (e.g., 'BTC-USDT').

    Returns:
        The current price (last trade price) as a float, or None if an error occurs.
    """
    if not client:
        print("KuCoin client is not available.")
        return None
        
    try:
        ticker = client.get_ticker(symbol)
        if ticker and 'price' in ticker:
            current_price = float(ticker['price'])
            print(f"Current price for {symbol}: {current_price}")
            return current_price
        else:
            print(f"Could not retrieve price from ticker for {symbol}. Ticker data: {ticker}")
            return None
    except Exception as e:
        print(f"Error fetching current price for {symbol}: {e}")
        return None

if __name__ == "__main__":
    # IMPORTANT: Replace with your actual API credentials or use environment variables
    # For this task, we are using placeholders.
    API_KEY = "YOUR_API_KEY"
    API_SECRET = "YOUR_API_SECRET"
    API_PASSPHRASE = "YOUR_API_PASSPHRASE"

# --- Strategy Parameters ---
TAKE_PROFIT_PERCENTAGE = 0.02  # 2%
STOP_LOSS_PERCENTAGE = 0.01   # 1%

# --- Helper Functions for Strategy ---

def calculate_moving_averages(df, short_window, long_window):
    """
    Calculates short-term and long-term Simple Moving Averages (SMA).

    Args:
        df: Pandas DataFrame with OHLCV data (must have a 'Close' column).
        short_window: The period for the short-term MA.
        long_window: The period for the long-term MA.

    Returns:
        Pandas DataFrame with 'short_ma' and 'long_ma' columns added.
    """
    if 'Close' not in df.columns:
        print("Error: 'Close' column not found in DataFrame.")
        return df # Or raise an error

    df['short_ma'] = df['Close'].rolling(window=short_window, min_periods=1).mean()
    df['long_ma'] = df['Close'].rolling(window=long_window, min_periods=1).mean()
    print(f"Calculated MAs: short_window={short_window}, long_window={long_window}")
    return df

def generate_signals(df):
    """
    Generates trading signals based on MA crossovers.

    Args:
        df: Pandas DataFrame with 'short_ma' and 'long_ma' columns.

    Returns:
        Pandas DataFrame with a 'signal' column added.
        Signal: 1 for Buy, -1 for Sell, 0 for No Signal.
    """
    if 'short_ma' not in df.columns or 'long_ma' not in df.columns:
        print("Error: MA columns ('short_ma', 'long_ma') not found.")
        return df

    df['signal'] = 0
    
    # Buy signal: short_ma crosses above long_ma
    # Condition: short_ma[t-1] < long_ma[t-1] AND short_ma[t] > long_ma[t]
    df.loc[(df['short_ma'].shift(1) < df['long_ma'].shift(1)) & \
           (df['short_ma'] > df['long_ma']), 'signal'] = 1
    
    # Sell signal: short_ma crosses below long_ma
    # Condition: short_ma[t-1] > long_ma[t-1] AND short_ma[t] < long_ma[t]
    df.loc[(df['short_ma'].shift(1) > df['long_ma'].shift(1)) & \
           (df['short_ma'] < df['long_ma']), 'signal'] = -1
           
    print("Generated trading signals.")
    return df

def strategy_decision(df, current_position):
    """
    Makes a trading decision based on the latest signal and current position.

    Args:
        df: Pandas DataFrame with MAs and 'signal' column.
        current_position: String indicating current position ('none', 'long').

    Returns:
        String decision: 'buy', 'sell', or 'hold'.
    """
    if df.empty or 'signal' not in df.columns:
        print("DataFrame is empty or 'signal' column is missing. Holding.")
        return 'hold'
        
    latest_signal = df['signal'].iloc[-1]
    
    decision = 'hold' # Default decision
    
    if latest_signal == 1 and current_position == 'none':
        decision = 'buy'
    elif latest_signal == -1 and current_position == 'long':
        decision = 'sell'
        
    print(f"Strategy Decision: Latest Signal={latest_signal}, Current Position='{current_position}' -> Decision='{decision}'")
    return decision

# --- Order Management Functions ---

def calculate_position_size(client, symbol, available_capital_percentage, last_price, simulated_balance_usdt=1000.0):
    """
    Calculates the amount of base currency to buy/sell.

    Args:
        client: The KuCoin client object.
        symbol: Trading pair (e.g., 'BTC-USDT').
        available_capital_percentage: Percentage of capital to risk (e.g., 0.05 for 5%).
        last_price: Current price of the base currency.
        simulated_balance_usdt: USDT balance to use if client is None.

    Returns:
        Amount of base currency to trade, or None if error.
    """
    balance_usdt = simulated_balance_usdt
    
    if client:
        try:
            # This is a placeholder for actual balance fetching.
            # Real implementation would involve:
            # accounts = client.get_accounts(currency='USDT', account_type='trade') # or 'main'
            # if accounts and len(accounts) > 0:
            #     balance_usdt = float(accounts[0]['balance'])
            # else:
            #     print("Warning: Could not fetch USDT balance or balance is zero. Using simulated balance.")
            #     balance_usdt = simulated_balance_usdt # Fallback if no specific account found
            print("Note: Real client balance fetching not implemented for calculate_position_size. Using simulated balance.")
        except Exception as e:
            print(f"Error fetching balance: {e}. Using simulated balance.")
            # Fallback to simulated if error during real fetch

    if last_price <= 0:
        print("Error: Last price must be positive to calculate position size.")
        return None

    capital_to_use = balance_usdt * available_capital_percentage
    amount_to_trade = capital_to_use / last_price
    
    base_currency = symbol.split('-')[0]
    print(f"Calculated Position Size: Using {capital_to_use:.2f} USDT ({available_capital_percentage*100}%) at price {last_price} for {symbol} -> {amount_to_trade:.8f} {base_currency}")
    # For now, returning raw calculated amount. Refinements for lot size/precision would go here.
    return amount_to_trade

def place_buy_order(client, symbol, amount, order_type='market', price=None):
    """
    Places a buy order.

    Args:
        client: The KuCoin client object.
        symbol: Trading pair.
        amount: Amount of base currency to buy.
        order_type: 'market' or 'limit'.
        price: Price for limit orders.

    Returns:
        Order ID or API response on success, None on failure or simulation.
    """
    if not isinstance(amount, (int, float)) or amount <= 0:
        print(f"Error: Invalid amount '{amount}' for buy order. Must be a positive number.")
        return None

    # KuCoin API expects amount and price as strings for precision
    amount_str = f"{amount:.8f}" # Example precision, adjust based on symbol actual requirements

    if client:
        try:
            if order_type == 'market':
                print(f"Attempting to place REAL market BUY order for {amount_str} of {symbol}...")
                # order = client.create_market_order(symbol=symbol, side=Client.SIDE_BUY, size=amount_str)
                # print(f"REAL Market BUY order placed: {order}")
                # return order.get('orderId') if order else None
                print("REAL client.create_market_order call is COMMENTED OUT for safety.")
                return f"real_buy_order_id_{int(time.time() * 1000)}" # Placeholder
            elif order_type == 'limit':
                if not price or price <= 0:
                    print("Error: Valid positive price required for limit order.")
                    return None
                price_str = f"{price:.8f}" # Example precision
                print(f"Attempting to place REAL limit BUY order for {amount_str} of {symbol} at {price_str}...")
                # order = client.create_limit_order(symbol=symbol, side=Client.SIDE_BUY, price=price_str, size=amount_str)
                # print(f"REAL Limit BUY order placed: {order}")
                # return order.get('orderId') if order else None
                print("REAL client.create_limit_order call is COMMENTED OUT for safety.")
                return f"real_limit_buy_order_id_{int(time.time() * 1000)}" # Placeholder
            else:
                print(f"Error: Unknown order type '{order_type}'")
                return None
        except Exception as e:
            print(f"Error placing REAL buy order: {e}")
            return None
    else:
        # Simulation
        order_id = f"sim_buy_order_{int(time.time() * 1000)}"
        price_info = f"at price {price}" if order_type == 'limit' and price else "at market price"
        print(f"SIMULATION: Placing BUY {order_type} order for {amount_str} of {symbol} {price_info}. Order ID: {order_id}")
        return order_id

def place_sell_order(client, symbol, amount, order_type='market', price=None):
    """
    Places a sell order.

    Args:
        client: The KuCoin client object.
        symbol: Trading pair.
        amount: Amount of base currency to sell.
        order_type: 'market' or 'limit'.
        price: Price for limit orders.

    Returns:
        Order ID or API response on success, None on failure or simulation.
    """
    if not isinstance(amount, (int, float)) or amount <= 0:
        print(f"Error: Invalid amount '{amount}' for sell order. Must be a positive number.")
        return None

    amount_str = f"{amount:.8f}" # Example precision

    if client:
        try:
            if order_type == 'market':
                print(f"Attempting to place REAL market SELL order for {amount_str} of {symbol}...")
                # order = client.create_market_order(symbol=symbol, side=Client.SIDE_SELL, size=amount_str)
                # print(f"REAL Market SELL order placed: {order}")
                # return order.get('orderId') if order else None
                print("REAL client.create_market_order call is COMMENTED OUT for safety.")
                return f"real_sell_order_id_{int(time.time() * 1000)}" # Placeholder
            elif order_type == 'limit':
                if not price or price <= 0:
                    print("Error: Valid positive price required for limit order.")
                    return None
                price_str = f"{price:.8f}" # Example precision
                print(f"Attempting to place REAL limit SELL order for {amount_str} of {symbol} at {price_str}...")
                # order = client.create_limit_order(symbol=symbol, side=Client.SIDE_SELL, price=price_str, size=amount_str)
                # print(f"REAL Limit SELL order placed: {order}")
                # return order.get('orderId') if order else None
                print("REAL client.create_limit_order call is COMMENTED OUT for safety.")
                return f"real_limit_sell_order_id_{int(time.time() * 1000)}" # Placeholder
            else:
                print(f"Error: Unknown order type '{order_type}'")
                return None
        except Exception as e:
            print(f"Error placing REAL sell order: {e}")
            return None
    else:
        # Simulation
        order_id = f"sim_sell_order_{int(time.time() * 1000)}"
        price_info = f"at price {price}" if order_type == 'limit' and price else "at market price"
        print(f"SIMULATION: Placing SELL {order_type} order for {amount_str} of {symbol} {price_info}. Order ID: {order_id}")
        return order_id

def manage_trade(client, symbol, decision, last_price, current_position_details=None, capital_percentage_per_trade=0.1, current_paper_capital=None):
    """
    Manages a trade based on strategy decision, current price, and position status.
    Now includes current_paper_capital for paper trading.

    Args:
        client: The KuCoin client object.
        symbol: Trading pair (e.g., 'BTC-USDT').
        decision: Output from strategy_decision ('buy', 'sell', 'hold').
        last_price: Current market price of the base currency.
        current_position_details: Dict with info about an open position or None.
        capital_percentage_per_trade: Percentage of capital to use for a new trade.
        current_paper_capital: Current capital if paper trading. If None, capital management is skipped.


    Returns:
        A tuple: (updated_position_details_dict, updated_paper_capital)
    """
    # Ensure TAKE_PROFIT_PERCENTAGE and STOP_LOSS_PERCENTAGE are accessible (they are global)
    
    updated_paper_capital_val = current_paper_capital # Use a mutable variable for capital
    
    # If no current position, initialize to None or an empty dict
    if current_position_details is None:
        current_position_details = {} 

    new_position_details = current_position_details.copy() # Work with a copy

    if decision == 'buy' and new_position_details.get('status') != 'open':
        # Use current_paper_capital for simulated_balance_usdt if provided
        balance_for_calc = updated_paper_capital_val if updated_paper_capital_val is not None else 1000 # Default if not paper trading
        amount_to_buy = calculate_position_size(client, symbol, capital_percentage_per_trade, last_price, simulated_balance_usdt=balance_for_calc)
        
        if amount_to_buy and amount_to_buy > 0:
            cost = amount_to_buy * last_price
            
            # Check for sufficient capital only if paper trading
            if updated_paper_capital_val is not None and updated_paper_capital_val < cost:
                print(f"Paper Trading: Insufficient capital ({updated_paper_capital_val:.2f}) to buy {amount_to_buy:.8f} {symbol} at {last_price:.2f} (cost: {cost:.2f}). Skipping buy.")
            else:
                buy_order_id = place_buy_order(client, symbol, amount_to_buy, order_type='market')
                if buy_order_id:
                    if updated_paper_capital_val is not None:
                        updated_paper_capital_val -= cost
                        # print(f"Paper Trading: Deducted {cost:.2f}. Capital now: {updated_paper_capital_val:.2f}") # Optional detailed print
                    entry_price = last_price # Approximated for market order
                    take_profit_price = entry_price * (1 + TAKE_PROFIT_PERCENTAGE)
                    stop_loss_price = entry_price * (1 - STOP_LOSS_PERCENTAGE)
                    
                    new_position_details = {
                        'entry_price': entry_price,
                        'amount': amount_to_buy,
                        'status': 'open',
                        'buy_order_id': buy_order_id,
                        'tp_price': take_profit_price,
                        'sl_price': stop_loss_price,
                        'symbol': symbol,
                        'cost': cost # Store cost for P&L calculation at close
                    }
                    print(f"Posición ABIERTA ({'Paper' if updated_paper_capital_val is not None else 'Real'}): Comprado {amount_to_buy:.8f} de {symbol} a {entry_price:.2f}. "
                          f"TP: {take_profit_price:.2f}, SL: {stop_loss_price:.2f}. Order ID: {buy_order_id}")
                else:
                    print("Failed to place buy order. No position opened.")
        else:
            print("Could not calculate amount to buy or amount is zero. No position opened.")

    elif decision == 'sell' and new_position_details.get('status') == 'open':
        amount_to_sell = new_position_details['amount']
        entry_price_for_pnl = new_position_details.get('entry_price', last_price) # Fallback if entry_price missing
        
        sell_order_id = place_sell_order(client, symbol, amount_to_sell, order_type='market')
        if sell_order_id:
            closed_price = last_price # Approximated for market order
            revenue = amount_to_sell * closed_price
            profit_or_loss = (closed_price - entry_price_for_pnl) * amount_to_sell
            
            if updated_paper_capital_val is not None:
                updated_paper_capital_val += revenue
                # print(f"Paper Trading: Added {revenue:.2f}. Capital now: {updated_paper_capital_val:.2f}")

            print(f"Posición CERRADA ({'Paper' if updated_paper_capital_val is not None else 'Real'} - por señal de estrategia): Vendido {amount_to_sell:.8f} de {symbol} a {closed_price:.2f}. P&L: {profit_or_loss:.2f}. Order ID: {sell_order_id}")
            new_position_details = {'status': 'closed', 'sell_order_id': sell_order_id, 'reason': 'strategy_signal', 'symbol': symbol, 'closed_price': closed_price, 'amount': amount_to_sell, 'entry_price': entry_price_for_pnl, 'pnl': profit_or_loss}
        else:
            print("Failed to place sell order for strategy signal. Position remains open.")
            
    elif new_position_details.get('status') == 'open': # Check for TP/SL only if no other action taken
        pos_tp_price = new_position_details['tp_price']
        pos_sl_price = new_position_details['sl_price']
        pos_amount = new_position_details['amount']
        pos_entry_price = new_position_details.get('entry_price', last_price) # Fallback

        if last_price >= pos_tp_price:
            sell_order_id = place_sell_order(client, symbol, pos_amount, order_type='market')
            if sell_order_id:
                closed_price = last_price # Approximated
                revenue = pos_amount * closed_price
                profit_or_loss = (closed_price - pos_entry_price) * pos_amount
                
                if updated_paper_capital_val is not None:
                    updated_paper_capital_val += revenue
                    # print(f"Paper Trading: Added {revenue:.2f} (TP). Capital now: {updated_paper_capital_val:.2f}")
                
                print(f"Posición CERRADA ({'Paper' if updated_paper_capital_val is not None else 'Real'} - Take Profit): Vendido {pos_amount:.8f} de {symbol} a {closed_price:.2f} (TP era: {pos_tp_price:.2f}). P&L: {profit_or_loss:.2f}. Order ID: {sell_order_id}")
                new_position_details = {'status': 'closed', 'sell_order_id': sell_order_id, 'reason': 'take_profit', 'symbol': symbol, 'closed_price': closed_price, 'amount': pos_amount, 'entry_price': pos_entry_price, 'pnl': profit_or_loss}
            else:
                print("Failed to place sell order for Take Profit. Position remains open.")
        elif last_price <= pos_sl_price:
            sell_order_id = place_sell_order(client, symbol, pos_amount, order_type='market')
            if sell_order_id:
                closed_price = last_price # Approximated
                revenue = pos_amount * closed_price
                profit_or_loss = (closed_price - pos_entry_price) * pos_amount # This will be a loss

                if updated_paper_capital_val is not None:
                    updated_paper_capital_val += revenue
                    # print(f"Paper Trading: Added {revenue:.2f} (SL). Capital now: {updated_paper_capital_val:.2f}")

                print(f"Posición CERRADA ({'Paper' if updated_paper_capital_val is not None else 'Real'} - Stop Loss): Vendido {pos_amount:.8f} de {symbol} a {closed_price:.2f} (SL era: {pos_sl_price:.2f}). P&L: {profit_or_loss:.2f}. Order ID: {sell_order_id}")
                new_position_details = {'status': 'closed', 'sell_order_id': sell_order_id, 'reason': 'stop_loss', 'symbol': symbol, 'closed_price': closed_price, 'amount': pos_amount, 'entry_price': pos_entry_price, 'pnl': profit_or_loss}
            else:
                print("Failed to place sell order for Stop Loss. Position remains open.")
    
    return new_position_details, updated_paper_capital_val

# --- Backtesting Functionality ---

def run_backtest(client, symbol, interval, start_date_str, end_date_str, # interval is used by get_historical_klines
                 short_window, long_window, capital_percentage_per_trade, initial_capital):
    """
    Runs a backtest of the scalping strategy.

    Args:
        client: KuCoin client object (can be None if simulating data).
        symbol: Trading pair (e.g., 'BTC-USDT').
        interval: Kline interval (e.g., Client.RESOLUTION_1HOUR).
        start_date_str: Start date for historical data ('YYYY-MM-DD HH:MM:SS').
        end_date_str: End date for historical data ('YYYY-MM-DD HH:MM:SS').
        short_window: Period for the short-term MA.
        long_window: Period for the long-term MA.
        capital_percentage_per_trade: Percentage of capital to risk per trade.
        initial_capital: Initial capital for the backtest.

    Returns:
        A dictionary containing backtesting metrics.
    """
    print(f"\n--- Starting Backtest ---")
    print(f"Symbol: {symbol}, Interval: {interval}") # Here 'interval' is the string passed for klines
    print(f"Period: {start_date_str} to {end_date_str}")
    print(f"Strategy Params: Short MA={short_window}, Long MA={long_window}")
    print(f"Trading Params: Initial Capital={initial_capital:.2f} USDT, Capital per Trade={capital_percentage_per_trade*100}%")

    # 1. Get Historical Data
    # 'interval' here should be the kline type string, e.g., '1min', '1hour'
    market_data_df = get_historical_klines(client, symbol, interval, start_date_str, end_date_str)

    if market_data_df is None or market_data_df.empty:
        print("No historical data fetched for backtest. Simulating data for backtest demonstration.")
        # Determine frequency string for pd.date_range from interval string
        freq_map = {
            Client.RESOLUTION_1MINUTE: '1min', Client.RESOLUTION_3MINUTE: '3min', Client.RESOLUTION_5MINUTE: '5min',
            Client.RESOLUTION_15MINUTE: '15min', Client.RESOLUTION_30MINUTE: '30min', Client.RESOLUTION_1HOUR: '1H',
            Client.RESOLUTION_2HOUR: '2H', Client.RESOLUTION_4HOUR: '4H', Client.RESOLUTION_6HOUR: '6H',
            Client.RESOLUTION_8HOUR: '8H', Client.RESOLUTION_12HOUR: '12H', Client.RESOLUTION_1DAY: '1D',
            Client.RESOLUTION_1WEEK: '1W'
        }
        # Fallback if interval string is not in map e.g. '1hour' vs Client.RESOLUTION_1HOUR
        data_freq = freq_map.get(interval, '1H') # Default to 1H if not found or direct string like '1hour'
        if isinstance(interval, str) and interval not in freq_map: # e.g. "1min", "1hour" direct strings
             if "min" in interval: data_freq = interval.replace("min","T")
             elif "hour" in interval: data_freq = interval.replace("hour","H")
             elif "day" in interval: data_freq = interval.replace("day","D")
             elif "week" in interval: data_freq = interval.replace("week","W")


        date_rng = pd.date_range(start=start_date_str, end=end_date_str, freq=data_freq)
        sim_data_size = len(date_rng)
        if sim_data_size < long_window + 50: # Ensure enough data for MAs and some trades
             print(f"Simulated date range too short for MA calculation ({sim_data_size} points for freq {data_freq}). Adjusting for simulation.")
             date_rng = pd.date_range(start=start_date_str, periods=long_window + 50, freq=data_freq)
             sim_data_size = len(date_rng)

        market_data_df = pd.DataFrame(date_rng, columns=['Timestamp'])
        # Create some price volatility for signals
        np.random.seed(42) # for reproducibility
        price_movements = np.random.randn(sim_data_size).cumsum() 
        start_price = 10000
        market_data_df['Close'] = start_price + price_movements * 10
        market_data_df['Open'] = market_data_df['Close'] - np.random.rand(sim_data_size) * 5
        market_data_df['High'] = market_data_df['Close'] + np.random.rand(sim_data_size) * 5
        market_data_df['Low'] = market_data_df['Close'] - np.random.rand(sim_data_size) * 5
        market_data_df['Volume'] = np.random.randint(100, 1000, size=sim_data_size)
        print(f"Simulated {len(market_data_df)} data points for {symbol}.")


    if market_data_df.empty or len(market_data_df) < long_window:
        print("Error: Not enough historical data to conduct backtest even after simulation attempt.")
        return {'error': "Not enough data."}

    # 2. Calculate Indicators and Generate Signals
    market_data_df = calculate_moving_averages(market_data_df, short_window, long_window)
    market_data_df = generate_signals(market_data_df) # Generates 'signal' column

    # Drop rows where MAs are not available (NaN)
    # The first (long_window - 1) rows will have NaN for long_ma.
    # Signals also depend on .shift(1), so effectively need long_window data points.
    first_valid_index = long_window 
    if first_valid_index >= len(market_data_df):
        print(f"Error: Not enough data points ({len(market_data_df)}) after MA calculation for window {long_window}.")
        return {'error': "Not enough data after MA calculation."}
    
    backtest_df = market_data_df[first_valid_index:].copy() # Use data from where MAs are valid
    backtest_df.reset_index(drop=True, inplace=True) # Reset index for easier iteration

    if backtest_df.empty:
        print("Error: No data left after MA calculation and NaN filtering for backtest.")
        return {'error': "No data after MA NaN filter."}

    # 3. Initialize Backtest State
    current_capital = initial_capital
    current_position_details = None # Will store dict like {'entry_price', 'amount', 'status', 'tp_price', 'sl_price', 'entry_time'}
    trade_history = []
    
    print(f"Starting iteration over {len(backtest_df)} data points (candles).")

    # 4. Iterate Over Historical Data
    for i in range(len(backtest_df)):
        current_price = backtest_df['Close'][i] # Use close of current candle for decisions & execution
        current_timestamp = backtest_df['Timestamp'][i]
        
        # A. Check for TP/SL if a position is open
        if current_position_details and current_position_details.get('status') == 'open':
            pos_amount = current_position_details['amount']
            pos_entry_price = current_position_details['entry_price']
            closed_by_tp_sl = False

            if current_price >= current_position_details['tp_price']: # Take Profit
                revenue = pos_amount * current_price # TP price is hit or exceeded
                profit = (current_price - pos_entry_price) * pos_amount
                current_capital += revenue
                trade_history.append({
                    'type': 'sell_tp', 'timestamp': current_timestamp, 'price': current_price,
                    'amount': pos_amount, 'entry_price': pos_entry_price, 'profit': profit,
                    'capital_after_trade': current_capital
                })
                print(f"{current_timestamp} - TP Hit: Sold {pos_amount:.4f} at {current_price:.2f}. Profit: {profit:.2f}. Capital: {current_capital:.2f}")
                current_position_details = None
                closed_by_tp_sl = True
            elif current_price <= current_position_details['sl_price']: # Stop Loss
                revenue = pos_amount * current_price # SL price is hit or fallen below
                loss = (current_price - pos_entry_price) * pos_amount # Will be negative
                current_capital += revenue
                trade_history.append({
                    'type': 'sell_sl', 'timestamp': current_timestamp, 'price': current_price,
                    'amount': pos_amount, 'entry_price': pos_entry_price, 'profit': loss, # profit is actually loss here
                    'capital_after_trade': current_capital
                })
                print(f"{current_timestamp} - SL Hit: Sold {pos_amount:.4f} at {current_price:.2f}. Loss: {loss:.2f}. Capital: {current_capital:.2f}")
                current_position_details = None
                closed_by_tp_sl = True
            
            if closed_by_tp_sl:
                continue # Move to next candle, no further strategy decision on this candle

        # B. Make Strategy Decision (using data up to current point)
        # For strategy_decision, pass df up to current candle 'i' from the backtest_df
        # The signal for candle 'i' is already calculated based on MAs of 'i' and 'i-1'.
        # The `strategy_decision` function uses the *latest* signal from the passed df.
        # So, `backtest_df.iloc[:i+1]` provides historical context including current candle's signal.
        
        # Determine position status for strategy_decision
        position_status_for_strategy = 'none'
        if current_position_details and current_position_details.get('status') == 'open':
            position_status_for_strategy = 'long'
            
        decision = strategy_decision(backtest_df.iloc[:i+1], position_status_for_strategy)

        # C. Execute Trade Based on Decision (Simplified manage_trade logic)
        if decision == 'buy' and (not current_position_details or current_position_details.get('status') != 'open'):
            amount_to_buy = calculate_position_size(None, symbol, capital_percentage_per_trade, current_price, simulated_balance_usdt=current_capital)
            if amount_to_buy and amount_to_buy > 0:
                cost = amount_to_buy * current_price
                if current_capital >= cost:
                    current_capital -= cost # Deduct cost of asset
                    entry_price = current_price
                    tp_price = entry_price * (1 + TAKE_PROFIT_PERCENTAGE)
                    sl_price = entry_price * (1 - STOP_LOSS_PERCENTAGE)
                    current_position_details = {
                        'entry_price': entry_price, 'amount': amount_to_buy, 'status': 'open',
                        'tp_price': tp_price, 'sl_price': sl_price, 'entry_time': current_timestamp,
                        'symbol': symbol
                    }
                    trade_history.append({
                        'type': 'buy', 'timestamp': current_timestamp, 'price': entry_price,
                        'amount': amount_to_buy, 'cost': cost, 'capital_after_trade': current_capital
                    })
                    print(f"{current_timestamp} - BUY: {amount_to_buy:.4f} at {entry_price:.2f}. Cost: {cost:.2f}. Capital: {current_capital:.2f}. TP: {tp_price:.2f}, SL: {sl_price:.2f}")
                else:
                    print(f"{current_timestamp} - Buy Signal: Insufficient capital ({current_capital:.2f}) for cost {cost:.2f}")
            else:
                 print(f"{current_timestamp} - Buy Signal: Amount to buy is zero or invalid.")

        elif decision == 'sell' and current_position_details and current_position_details.get('status') == 'open':
            pos_amount = current_position_details['amount']
            pos_entry_price = current_position_details['entry_price']
            revenue = pos_amount * current_price
            profit = (current_price - pos_entry_price) * pos_amount
            current_capital += revenue # Add proceeds from sale
            trade_history.append({
                'type': 'sell_strategy', 'timestamp': current_timestamp, 'price': current_price,
                'amount': pos_amount, 'entry_price': pos_entry_price, 'profit': profit,
                'capital_after_trade': current_capital
            })
            print(f"{current_timestamp} - SELL (Strategy): {pos_amount:.4f} at {current_price:.2f}. Profit: {profit:.2f}. Capital: {current_capital:.2f}")
            current_position_details = None

    # 5. Close any open position at the end of the backtest period
    if current_position_details and current_position_details.get('status') == 'open':
        last_close_price = backtest_df['Close'].iloc[-1]
        pos_amount = current_position_details['amount']
        pos_entry_price = current_position_details['entry_price']
        revenue = pos_amount * last_close_price
        profit = (last_close_price - pos_entry_price) * pos_amount
        current_capital += revenue
        trade_history.append({
            'type': 'sell_eod', 'timestamp': backtest_df['Timestamp'].iloc[-1], 'price': last_close_price,
            'amount': pos_amount, 'entry_price': pos_entry_price, 'profit': profit,
            'capital_after_trade': current_capital
        })
        print(f"End of Backtest - Closing open position: Sold {pos_amount:.4f} at {last_close_price:.2f}. Profit: {profit:.2f}. Capital: {current_capital:.2f}")
        current_position_details = None

    # 6. Calculate Performance Metrics
    final_capital = current_capital
    total_pnl = final_capital - initial_capital
    total_return_percentage = (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0
    
    num_total_trades = sum(1 for trade in trade_history if trade['type'].startswith('sell_')) # Count sell trades
    
    winning_trades = sum(1 for trade in trade_history if trade['type'].startswith('sell_') and trade['profit'] > 0)
    losing_trades = sum(1 for trade in trade_history if trade['type'].startswith('sell_') and trade['profit'] <= 0) # Includes break-even
    
    win_rate = (winning_trades / num_total_trades) * 100 if num_total_trades > 0 else 0

    metrics = {
        "Initial Capital": initial_capital,
        "Final Capital": final_capital,
        "Total P&L (USDT)": total_pnl,
        "Total Return (%)": total_return_percentage,
        "Total Trades": num_total_trades,
        "Winning Trades": winning_trades,
        "Losing Trades": losing_trades,
        "Win Rate (%)": win_rate,
        "Trade History": trade_history # Optional: for detailed review
    }
    
    print("\n--- Backtest Finished ---")
    for key, value in metrics.items():
        if key != "Trade History": # Don't print the whole trade history here
            print(f"{key}: {value:.2f}" if isinstance(value, (int, float)) else f"{key}: {value}")

    return metrics


# --- Paper Trading Loop ---

def paper_trading_loop(client, symbol, interval_str, # Renamed to interval_str to avoid clash
                       short_window, long_window, 
                       capital_percentage_per_trade, initial_paper_capital, 
                       run_duration_minutes, static_data_source=None):
    """
    Simulates paper trading for the bot.

    Args:
        client: KuCoin client object (can be None).
        symbol: Trading pair.
        interval_str: Kline interval string (e.g., '1min', '1hour', or Client.RESOLUTION_*).
        short_window, long_window: MA parameters.
        capital_percentage_per_trade: Capital to risk per trade.
        initial_paper_capital: Starting capital for paper trading.
        run_duration_minutes: How long the loop should run.
        static_data_source: Optional pre-generated DataFrame for simulating market data.
    """
    print(f"\n--- Starting Paper Trading Loop ---")
    print(f"Symbol: {symbol}, Interval: {interval_str}, Duration: {run_duration_minutes} mins")
    print(f"Initial Capital: {initial_paper_capital:.2f} USDT")

    current_paper_capital = initial_paper_capital
    current_position_details = None
    trade_log = []
    
    start_loop_time = datetime.datetime.now()
    end_loop_time = start_loop_time + datetime.timedelta(minutes=run_duration_minutes)

    # For simulating data feed from a larger static source:
    data_idx = 0 
    # Ensure static_data_source has enough data for the loop + initial MA calculation needs
    # We need `long_window` historical points for the first MA calculation.
    # Each iteration consumes one new "candle".
    
    # Determine frequency for time.sleep and data slicing
    # This is a simplified mapping. Real market data arrival is not perfectly timed.
    sleep_duration_seconds = 60 # Default for 1-minute interval
    if isinstance(interval_str, str):
        if "min" in interval_str: sleep_duration_seconds = int(interval_str.split("min")[0]) * 60
        elif "hour" in interval_str: sleep_duration_seconds = int(interval_str.split("hour")[0]) * 3600
        # Add other interval mappings if necessary
    elif interval_str == Client.RESOLUTION_1MINUTE: sleep_duration_seconds = 60
    elif interval_str == Client.RESOLUTION_1HOUR: sleep_duration_seconds = 3600
    # Keep sleep reasonable for testing, e.g., max 60s for this simulation
    effective_sleep = min(sleep_duration_seconds, 10) # Shorten for quick testing
    print(f"Loop will iterate approx. every {effective_sleep} seconds (simulating {interval_str} candles).")


    while datetime.datetime.now() < end_loop_time:
        iter_start_time = datetime.datetime.now()
        print(f"\n--- Paper Trading Iteration: {iter_start_time.strftime('%Y-%m-%d %H:%M:%S')} ---")

        # 1. Get/Simulate Market Data
        current_market_time_for_slice = datetime.datetime.now() # Simulate data up to 'now'
        
        if static_data_source is not None and not static_data_source.empty:
            # Find the portion of static_data_source that ends "now" or just before
            # And is long enough for MA calculation (at least long_window points)
            
            # This simulates fetching the latest `long_window + N` candles up to current time.
            # In a real scenario, `get_historical_klines` would fetch this.
            # For simulation, we take a slice from our static_data_source.
            
            # We need to find the closest timestamp in our static data to "now"
            # This is a simplification. A real feed would be more complex.
            relevant_data_end_idx = static_data_source[static_data_source['Timestamp'] <= current_market_time_for_slice].index.max()
            
            if pd.isna(relevant_data_end_idx) and data_idx < len(static_data_source): # If no data is "before now", advance index
                 relevant_data_end_idx = data_idx + long_window + 5 # Take a chunk from current data_idx
            elif pd.isna(relevant_data_end_idx): # Still no data, maybe at end of source
                 print("Warning: Ran out of static data or issue with time alignment.")
                 time.sleep(effective_sleep)
                 continue


            # Ensure we don't go out of bounds
            relevant_data_end_idx = min(relevant_data_end_idx, len(static_data_source) - 1)
            
            # Start index for the slice to get enough data for MAs
            slice_start_idx = max(0, relevant_data_end_idx - (long_window + 20)) # Get a bit more than long_window
            
            market_df_slice = static_data_source.iloc[slice_start_idx : relevant_data_end_idx + 1].copy()
            data_idx = relevant_data_end_idx + 1 # Move to next candle for next iteration (simplistic)


            if market_df_slice.empty or len(market_df_slice) < long_window:
                print(f"Warning: Not enough data in slice ({len(market_df_slice)} points) for MAs (need {long_window}). Skipping iteration.")
                if datetime.datetime.now() >= end_loop_time: break
                time.sleep(effective_sleep)
                continue
            
            last_price = market_df_slice['Close'].iloc[-1]
            current_sim_timestamp = market_df_slice['Timestamp'].iloc[-1]
            print(f"Simulated Data: Using {len(market_df_slice)} candles up to {current_sim_timestamp}. Last Price: {last_price:.2f}")

        else: # Fallback if no static data source or if client was supposed to be used
            print("Paper Trading: Live client data fetching not implemented in this loop / No static data. Using placeholder values.")
            # This part would need actual client.get_historical_klines or more robust simulation
            # For now, let's make it so it doesn't trade without data.
            last_price = 10000 + np.random.randint(-10,10) # Dummy price
            market_df_slice = pd.DataFrame({'Close': [last_price-10, last_price], 
                                            'Timestamp': [datetime.datetime.now()-datetime.timedelta(minutes=1), datetime.datetime.now()]}) # Dummy DF for functions
            # This dummy DF won't be enough for MAs if long_window > 1. Strategy will likely hold.
            if len(market_df_slice) < long_window:
                 print(f"Placeholder data too short for MA ({long_window}). Strategy will likely hold.")


        # 2. Apply Strategy
        df_with_mas = calculate_moving_averages(market_df_slice, short_window, long_window)
        df_with_signals = generate_signals(df_with_mas)
        
        current_pos_status_for_strategy = 'none'
        if current_position_details and current_position_details.get('status') == 'open':
            current_pos_status_for_strategy = 'long'
        decision = strategy_decision(df_with_signals, current_pos_status_for_strategy)

        # 3. Manage Position (Simulated)
        # `manage_trade` is already set up for simulation if client is None
        # It now also takes and returns current_paper_capital
        updated_position_details, updated_capital = manage_trade(
            None, symbol, decision, last_price, 
            current_position_details, capital_percentage_per_trade, 
            current_paper_capital=current_paper_capital
        )
        
        # Log if a trade happened (position status changed or closed)
        if (current_position_details is None and updated_position_details.get('status') == 'open') or \
           (current_position_details is not None and updated_position_details.get('status') == 'closed'):
            trade_log.append({
                'timestamp': current_sim_timestamp if 'current_sim_timestamp' in locals() else datetime.datetime.now(),
                'decision': decision,
                'price': last_price,
                'old_pos_status': current_position_details.get('status') if current_position_details else 'none',
                'new_pos_status': updated_position_details.get('status'),
                'new_pos_details': updated_position_details.copy(), # Log a copy
                'capital_before': current_paper_capital,
                'capital_after': updated_capital,
                'pnl_on_close': updated_position_details.get('pnl') if updated_position_details.get('status') == 'closed' else 0
            })
        
        current_position_details = updated_position_details
        current_paper_capital = updated_capital

        # 4. Print Status
        print(f"Paper Trading Status: Capital = {current_paper_capital:.2f} USDT")
        if current_position_details and current_position_details.get('status') == 'open':
            print(f"  Open Position: {current_position_details['amount']:.8f} {symbol} at {current_position_details['entry_price']:.2f}. "
                  f"TP: {current_position_details['tp_price']:.2f}, SL: {current_position_details['sl_price']:.2f}")
        else:
            print("  No open position.")
        print(f"  Last Decision: {decision.upper()}")

        # 5. Wait for next iteration
        if datetime.datetime.now() >= end_loop_time:
            print("Paper trading duration reached.")
            break
        
        # Calculate time spent and adjust sleep to roughly match interval
        iter_end_time = datetime.datetime.now()
        time_spent_this_iter = (iter_end_time - iter_start_time).total_seconds()
        sleep_for = max(0, effective_sleep - time_spent_this_iter)
        
        print(f"Iteration took {time_spent_this_iter:.2f}s. Sleeping for {sleep_for:.2f}s...")
        time.sleep(sleep_for)

    # End of loop: Summary
    print("\n--- Paper Trading Loop Finished ---")
    print(f"Final Paper Capital: {current_paper_capital:.2f} USDT")
    initial_pnl = current_paper_capital - initial_paper_capital
    print(f"Total P&L: {initial_pnl:.2f} USDT")
    
    sells = [t for t in trade_log if t.get('new_pos_details',{}).get('status')=='closed']
    buys = [t for t in trade_log if t.get('old_pos_status')=='none' and t.get('new_pos_details',{}).get('status')=='open']

    print(f"Total Buy Operations Logged: {len(buys)}")
    print(f"Total Sell Operations Logged (TP/SL/Strategy): {len(sells)}")
    # For more detailed P&L, sum 'pnl_on_close' from trade_log
    total_pnl_from_trades = sum(t.get('pnl_on_close', 0) for t in trade_log if t.get('pnl_on_close'))
    print(f"Total P&L from closed trades in log: {total_pnl_from_trades:.2f} USDT") # This should match overall P&L if no open positions

    if current_position_details and current_position_details.get('status') == 'open':
        print(f"Warning: Position remains open at end of paper trading: {current_position_details}")


# --- Main Application Logic ---

if __name__ == "__main__":
    # IMPORTANT: Replace with your actual API credentials or use environment variables
    # For this task, we are using placeholders.
    API_KEY = "YOUR_API_KEY"
    API_SECRET = "YOUR_API_SECRET"
    API_PASSPHRASE = "YOUR_API_PASSPHRASE"

    print("Attempting to connect to KuCoin (simulated for defining functions)...")
    # For the purpose of defining and testing the structure of these functions,
    # we don't need a real client if the API calls are not actually made.
    # However, to test the actual API interaction, a client would be needed.
    # For this subtask, we'll proceed as if the client could be None and functions handle it.
    
    kucoin_client = None # Simulate: use connect_to_kucoin(API_KEY, API_SECRET, API_PASSPHRASE) for real connection
    print("Simulating KuCoin connection for development purposes.")
    print(f"Defined Strategy Parameters: TP={TAKE_PROFIT_PERCENTAGE*100}%, SL={STOP_LOSS_PERCENTAGE*100}%")

    # --- Simulate fetching data and applying strategy ---
    print("\n--- Strategy Simulation with Sample Data ---")
    
    # Create a sample DataFrame as get_historical_klines would return None without a client
    # This data simulates a crossover event
    sample_data = {
        'Timestamp': pd.to_datetime(['2023-01-01 09:00', '2023-01-01 09:01', '2023-01-01 09:02', 
                                      '2023-01-01 09:03', '2023-01-01 09:04', '2023-01-01 09:05',
                                      '2023-01-01 09:06', '2023-01-01 09:07', '2023-01-01 09:08']),
        'Open':  [100, 101, 102, 103, 100, 101, 102, 103, 100],
        'High':  [101, 102, 103, 104, 101, 102, 103, 104, 101],
        'Low':   [99,  100, 101, 102, 99,  100, 101, 102, 99 ],
        'Close': [100, 101, 102, 103, 100, 99,  98,  97,  96 ], # Prices for buy, then sell signal
        'Volume':[10,  12,  11,  13,  15, 16,  17,  18,  19 ]
    }
    market_data_df = pd.DataFrame(sample_data)
    
    if market_data_df is not None and not market_data_df.empty:
        print("Sample market data (first 5 rows):")
        print(market_data_df.head())

        # 1. Calculate Moving Averages
        short_window = 3 # Example: 5 periods
        long_window = 6  # Example: 20 periods
        market_data_df = calculate_moving_averages(market_data_df, short_window, long_window)
        
        # 2. Generate Signals
        market_data_df = generate_signals(market_data_df)
        
        print("\nMarket data with MAs and Signals (last 5 rows):")
        print(market_data_df.tail())
        
        # 3. Strategy Decision Simulation
        print("\n--- Strategy Decision Simulation ---")
        
        # Case 1: No current position, buy signal
        # To ensure a buy signal at the end, let's manipulate the last few data points for this test
        # Or, better, use the existing data which should generate a sell signal towards the end.
        # Let's re-evaluate the sample data for signals:
        # Close: [100, 101, 102, 103, 100, 99, 98, 97, 96]
        # Short MA (3): -, 100.5, 101, 101.66, 101, 100, 99, 98, 97 (approx)
        # Long MA (6): -, -, 100.7, 101.16, 101.2, 100.83, 100.5, 100, 99.16 (approx)
        # A buy signal might occur if short MA crosses above long MA.
        # A sell signal will occur as short MA crosses below long MA (e.g. around 09:05 or 09:06).

        print("\nSimulating with a specific scenario for BUY:")
        # Create data that ensures a BUY signal at the last point
        buy_signal_data = {
            'Timestamp': pd.to_datetime(['2023-01-01 10:00', '2023-01-01 10:01', '2023-01-01 10:02', '2023-01-01 10:03']),
            'Close': [100, 99, 100, 103], # short_ma will cross up
            'Open': [100]*4, 'High': [100]*4, 'Low': [99]*4, 'Volume': [10]*4
        }
        buy_df = pd.DataFrame(buy_signal_data)
        buy_df = calculate_moving_averages(buy_df, short_window=2, long_window=3) # Use windows that make sense for small data
        buy_df = generate_signals(buy_df)
        print(buy_df.tail())
        current_pos_none = 'none'
        decision1 = strategy_decision(buy_df, current_pos_none)
        print(f"Decision (Position: {current_pos_none}, Latest Signal: {buy_df['signal'].iloc[-1]}): {decision1}")

        print("\nSimulating with a specific scenario for SELL (using original sample data):")
        # The original market_data_df should have a sell signal at the end
        # market_data_df already calculated and has signals.
        current_pos_long = 'long'
        decision2 = strategy_decision(market_data_df, current_pos_long) # market_data_df's last signal should be -1
        print(f"Decision (Position: {current_pos_long}, Latest Signal: {market_data_df['signal'].iloc[-1]}): {decision2}")

        print("\nSimulating with a specific scenario for HOLD (no clear signal or already in position):")
        # Create data that ensures a HOLD signal (e.g. MAs are close but not crossing, or signal is old)
        hold_signal_data = {
            'Timestamp': pd.to_datetime(['2023-01-01 11:00', '2023-01-01 11:01', '2023-01-01 11:02', '2023-01-01 11:03']),
            'Close': [100, 101, 100, 101], # MAs might be close, no clear cross for last signal
            'Open': [100]*4, 'High': [100]*4, 'Low': [99]*4, 'Volume': [10]*4
        }
        hold_df = pd.DataFrame(hold_signal_data)
        hold_df = calculate_moving_averages(hold_df, short_window=2, long_window=3)
        hold_df['short_ma'] = [100, 100.5, 100.5, 100.5] # Force MAs to not cross at the end
        hold_df['long_ma']  = [100, 100.33, 100.33, 100.33]
        hold_df = generate_signals(hold_df) # This will generate 0 if no cross at the end
        print(hold_df.tail())
        decision3 = strategy_decision(hold_df, 'none') # No signal, no position
        print(f"Decision (Position: 'none', Latest Signal: {hold_df['signal'].iloc[-1]}): {decision3}")
        decision4 = strategy_decision(hold_df, 'long') # No signal, already long
        print(f"Decision (Position: 'long', Latest Signal: {hold_df['signal'].iloc[-1]}): {decision4}")

    else:
        print("Could not simulate strategy as no market data is available (client is None or API error).")

    print("\nNote: The above simulation uses dummy data. For real trading, connect to KuCoin.")
    print("Strategy functions (calculate_moving_averages, generate_signals, strategy_decision) are defined.")
    print("Order management functions (calculate_position_size, place_buy_order, place_sell_order, manage_trade) are defined.")
    print("Backtesting function (run_backtest) is defined.")

    # --- Simulation of manage_trade (kept for individual function testing) ---
    # print("\n--- manage_trade Simulation Scenarios ---")
    test_symbol = 'BTC-USDT'
    # current_pos will store the state of our position
    current_pos = None # Start with no position, explicitly as a dictionary or None

    # Scenario 1: No position, strategy says 'buy'
    print("\nSCENARIO 1: No position, decision 'buy'")
    last_price_sc1 = 100.0
    decision_sc1 = 'buy'
    # Pass current_pos (which is None or empty dict)
    current_pos = manage_trade(kucoin_client, test_symbol, decision_sc1, last_price_sc1, current_pos, capital_percentage_per_trade=0.1)
    print(f"  Resulting position: {current_pos}")
    # Expected: Position is opened. current_pos will hold {'entry_price': 100, 'amount': (0.1 * 1000) / 100 = 1.0 BTC,
    # 'status': 'open', 'tp_price': 102, 'sl_price': 99, ...} based on 1000 USDT simulated balance and 10% capital.

    # Scenario 2: Position open, price hits Take Profit
    print("\nSCENARIO 2: Position open, price hits Take Profit (TP)")
    if current_pos and current_pos.get('status') == 'open':
        # Ensure tp_price exists from previous step
        last_price_sc2 = current_pos['tp_price'] + 0.01 # Price moves slightly above TP
        decision_sc2 = 'hold' # Strategy might say hold, but TP should trigger
        print(f"  Current position before TP check: {current_pos}")
        print(f"  Incoming price {last_price_sc2:.2f} vs TP {current_pos['tp_price']:.2f}")
        current_pos = manage_trade(kucoin_client, test_symbol, decision_sc2, last_price_sc2, current_pos)
        print(f"  Resulting position: {current_pos}")
        # Expected: Position is closed due to TP. current_pos will show {'status': 'closed', 'reason': 'take_profit', ...}
    else:
        print("  Skipping Scenario 2: No open position from Scenario 1 or invalid state.")
    
    # Reset for next independent scenario sequence
    current_pos = None 
    print("\n--- Resetting position for new sequence (Scenarios 3 & 4) ---")

    # Scenario 3: No position, strategy says 'buy' (again for SL test)
    print("\nSCENARIO 3: No position, decision 'buy' (for SL test)")
    last_price_sc3 = 100.0
    decision_sc3 = 'buy'
    current_pos = manage_trade(kucoin_client, test_symbol, decision_sc3, last_price_sc3, current_pos, capital_percentage_per_trade=0.1)
    print(f"  Resulting position: {current_pos}")

    # Scenario 4: Position open, price hits Stop Loss
    print("\nSCENARIO 4: Position open, price hits Stop Loss (SL)")
    if current_pos and current_pos.get('status') == 'open':
        last_price_sc4 = current_pos['sl_price'] - 0.01 # Price moves slightly below SL
        decision_sc4 = 'hold' # Strategy might say hold, but SL should trigger
        print(f"  Current position before SL check: {current_pos}")
        print(f"  Incoming price {last_price_sc4:.2f} vs SL {current_pos['sl_price']:.2f}")
        current_pos = manage_trade(kucoin_client, test_symbol, decision_sc4, last_price_sc4, current_pos)
        print(f"  Resulting position: {current_pos}")
        # Expected: Position is closed due to SL. current_pos will show {'status': 'closed', 'reason': 'stop_loss', ...}
    else:
        print("  Skipping Scenario 4: No open position from Scenario 3 or invalid state.")

    # Reset for next independent scenario sequence
    current_pos = None
    print("\n--- Resetting position for new sequence (Scenario 5) ---")

    # Scenario 5: Position open, strategy says 'sell'
    print("\nSCENARIO 5: Position open, decision 'sell'")
    # First, open a position
    last_price_sc5_open = 100.0
    decision_sc5_open = 'buy'
    current_pos = manage_trade(kucoin_client, test_symbol, decision_sc5_open, last_price_sc5_open, current_pos, capital_percentage_per_trade=0.1)
    print(f"  Position opened: {current_pos}")
    
    # if current_pos and current_pos.get('status') == 'open':
    #     last_price_sc5_sell = 101.0 # Price is somewhere between entry and TP/SL
    #     decision_sc5_sell = 'sell' # Strategy now signals to sell
    #     print(f"  Current position before strategy sell (price {last_price_sc5_sell:.2f}): {current_pos}")
    #     current_pos = manage_trade(kucoin_client, test_symbol, decision_sc5_sell, last_price_sc5_sell, current_pos)
    #     print(f"  Resulting position: {current_pos}")
    #     # Expected: Position is closed due to strategy signal. current_pos will show {'status': 'closed', 'reason': 'strategy_signal', ...}
    # else:
    #     print("  Skipping Scenario 5 execution: Failed to open position first or invalid state.")

    # --- Run Backtest ---
    # print("\n--- Executing Backtest ---") # Commenting out to focus on paper trading loop
    # ... (backtest call and printing logic commented out) ...

    # --- Paper Trading Loop ---
    print("\n--- Starting Paper Trading Simulation ---")
    paper_symbol = 'BTC-USDT'
    paper_interval = Client.RESOLUTION_1MINUTE # Using 1-minute for more frequent (simulated) ticks
    paper_short_window = 5
    paper_long_window = 20 # Shorter windows for more signals in a short run
    paper_capital_percentage = 0.1 # 10%
    paper_initial_capital = 1000.0 # USDT
    paper_run_duration_minutes = 3 # Short duration for testing

    # Prepare a larger static DataFrame for the paper trading loop to slice from
    # This simulates new candles arriving over time.
    sim_start_time_paper = datetime.datetime.now() - datetime.timedelta(minutes=paper_run_duration_minutes + paper_long_window + 60) # Ensure enough past data
    sim_end_time_paper = datetime.datetime.now() + datetime.timedelta(minutes=paper_run_duration_minutes + 5) # Ensure data into the future part of loop
    
    num_candles_paper = (sim_end_time_paper - sim_start_time_paper).total_seconds() / 60 # Assuming 1-min interval
    if paper_interval == Client.RESOLUTION_1HOUR: # Adjust if different interval used
        num_candles_paper = (sim_end_time_paper - sim_start_time_paper).total_seconds() / 3600

    date_rng_paper = pd.date_range(start=sim_start_time_paper, periods=int(num_candles_paper), freq='1min' if paper_interval == Client.RESOLUTION_1MINUTE else '1H')
    
    simulated_market_data_for_paper_loop = pd.DataFrame(date_rng_paper, columns=['Timestamp'])
    np.random.seed(123) # Different seed from backtest
    price_movements_paper = np.random.randn(len(simulated_market_data_for_paper_loop)).cumsum()
    start_price_paper = 10000 + np.random.randint(-500, 500) # Vary start price a bit
    simulated_market_data_for_paper_loop['Close'] = start_price_paper + price_movements_paper * 5 # Smaller movements for 1-min
    simulated_market_data_for_paper_loop['Open'] = simulated_market_data_for_paper_loop['Close'] - np.random.rand(len(simulated_market_data_for_paper_loop)) * 2
    simulated_market_data_for_paper_loop['High'] = simulated_market_data_for_paper_loop['Close'] + np.random.rand(len(simulated_market_data_for_paper_loop)) * 2
    simulated_market_data_for_paper_loop['Low'] = simulated_market_data_for_paper_loop['Close'] - np.random.rand(len(simulated_market_data_for_paper_loop)) * 2
    simulated_market_data_for_paper_loop['Volume'] = np.random.randint(10, 100, size=len(simulated_market_data_for_paper_loop))
    print(f"Prepared {len(simulated_market_data_for_paper_loop)} static candles for paper trading simulation.")


    # Ensure Client.RESOLUTION_1MINUTE is defined or use string '1min'
    # Assuming Client class has these attributes. If not, direct strings are safer.
    # For this example, let's use direct strings for interval if Client.RESOLUTION_* is not guaranteed.
    paper_interval_value = '1min' # Example: Client.RESOLUTION_1MINUTE might be "1min"
    # If Client.RESOLUTION_1MINUTE is an object or not defined, this needs adjustment.
    # Let's assume it's a string constant like '1min', '1hour' etc. that get_historical_klines and run_backtest understand.
    # The provided snippet for run_backtest already maps Client.RESOLUTION strings to pandas freq.
    # We'll use the string '1min' for paper_interval to be safe.

    paper_trading_loop(
        client=kucoin_client, # None for simulation
        symbol=paper_symbol,
        interval_str=paper_interval_value, 
        short_window=paper_short_window,
        long_window=paper_long_window,
        capital_percentage_per_trade=paper_capital_percentage,
        initial_paper_capital=paper_initial_capital,
        run_duration_minutes=paper_run_duration_minutes,
        static_data_source=simulated_market_data_for_paper_loop # Pass the pre-generated data
    )
