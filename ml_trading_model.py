import os
import pandas as pd
import numpy as np
import datetime
import logging
# from kucoin.client import Client # Assuming this might be needed if real client used

# Technical Analysis library
import ta
from ta.utils import dropna
from ta.volatility import BollingerBands
from ta.trend import MACD, SMAIndicator
from ta.momentum import RSIIndicator

# Model Training and Evaluation
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import (
    accuracy_score, 
    precision_score, 
    recall_score, 
    f1_score, 
    classification_report, 
    confusion_matrix,
    roc_curve, 
    auc        
)
import joblib

# --- Global Logger ---
# Will be initialized in if __name__ == "__main__" after setup.
logger = None

# --- Logging Setup Function ---
def setup_ml_logging():
    """
    Configures logging for the application.

    Sets up a logger that writes to both a file (`ml_model_activity.log`) and the console.
    The logging level is set to INFO. Duplicate logging is prevented if this function
    is called multiple times by clearing existing handlers.

    Returns:
        logging.Logger: Configured logger instance.
    """
    global logger # Use the global logger variable
    logger = logging.getLogger('MLTradingModel')
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler('ml_model_activity.log', mode='a')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    logger.info("ML Model Logging setup complete.")
    return logger

# --- KuCoin Client and Data Fetching Functions (Adapted - assumed to be working) ---

def connect_to_kucoin(api_key, api_secret, api_passphrase):
    """
    Simulates connecting to the KuCoin API.
    For this ML script, we primarily rely on simulated or cached data,
    so this function can be a placeholder.

    Args:
        api_key (str): The user's KuCoin API key.
        api_secret (str): The user's KuCoin API secret.
        api_passphrase (str): The user's KuCoin API passphrase.

    Returns:
        None: As we are not focusing on live API connection here.
               Or, could return a dummy client if parts of get_historical_klines use it.
    """
    global logger
    if not logger: logger = logging.getLogger('MLTradingModel') 

    logger.info("Attempting to connect to KuCoin API (simulated for ML context)...")
    if api_key and api_secret and api_passphrase:
        logger.info("Simulated KuCoin connection: Would connect if real credentials and Client library were active.")
        return "simulated_client_object" # Placeholder if needed by get_historical_klines structure
    logger.warning("Simulated KuCoin connection: API credentials not provided. No client created.")
    return None


def get_historical_klines(client, symbol, interval, start_date_str, end_date_str):
    """
    Fetches historical kline data. If client is None or fetching fails,
    generates simulated OHLCV data for BTC/USDT (1-hour) covering the requested range.

    Args:
        client: KuCoin client object (can be None).
        symbol (str): Trading pair (e.g., 'BTC-USDT').
        interval (str): Kline interval (e.g., '1hour', '1day').
        start_date_str (str): Start date string ('YYYY-MM-DD HH:MM:SS').
        end_date_str (str): End date string ('YYYY-MM-DD HH:MM:SS').

    Returns:
        pd.DataFrame: DataFrame with OHLCV data, or None if error.
    """
    global logger
    if not logger: logger = logging.getLogger('MLTradingModel')
    logger.info(f"Attempting to get historical klines for {symbol}, interval {interval} from {start_date_str} to {end_date_str}.")

    if client:
        logger.info(f"Client provided. In a real scenario, would attempt to fetch data from KuCoin API for {symbol}.")
        logger.warning("Client object provided, but actual API call is disabled for this ML script. Falling back to data generation.")

    logger.info(f"Generating simulated OHLCV data for {symbol} ({interval}) from {start_date_str} to {end_date_str}.")
    
    try:
        start_dt = datetime.datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S')
        end_dt = datetime.datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
    except ValueError as e:
        logger.error(f"Invalid date format: {e}. Please use 'YYYY-MM-DD HH:MM:SS'.")
        return None

    if interval == '1hour':
        freq = 'H'
    elif interval == '1day':
        freq = 'D'
    else: 
        logger.warning(f"Interval '{interval}' not explicitly supported for simulation frequency. Defaulting to 'H'.")
        freq = 'H'
        
    num_periods = int((end_dt - start_dt).total_seconds() / (3600 if freq == 'H' else 24*3600) )
    if num_periods <=0:
        logger.error(f"Start date must be before end date. Got {num_periods} periods.")
        return None

    if symbol == 'BTC-USDT' and interval == '1hour':
        min_periods_for_2_years_hourly = 2 * 365 * 24
        if num_periods < min_periods_for_2_years_hourly:
            logger.info(f"Requested period is less than 2 years for BTC-USDT 1hour. Forcing 2 years of simulated data generation ending at {end_date_str}.")
            start_dt = end_dt - datetime.timedelta(days=2*365)
            # Recalculate num_periods based on the new start_dt
            num_periods = int((end_dt - start_dt).total_seconds() / (3600 if freq == 'H' else 24*3600))
            
    timestamps = pd.date_range(start=start_dt, periods=num_periods, freq=freq)
    
    if not len(timestamps): 
        logger.error(f"Could not generate valid date range. Start: {start_dt}, End: {end_dt}, Freq: {freq}, Num Periods: {num_periods}")
        return None

    df = pd.DataFrame(index=timestamps)
    df['Timestamp'] = df.index

    price = np.zeros(len(df))
    price[0] = 20000 + np.random.uniform(-5000, 5000) 
    
    drift_factor = 0.0001 
    volatility = 0.03 if freq == 'D' else 0.01

    for i in range(1, len(df)):
        change_pct = np.random.normal(loc=drift_factor, scale=volatility)
        price[i] = price[i-1] * (1 + change_pct)
        if price[i] <= 0: price[i] = price[i-1] * 0.98 

    df['Close'] = price
    df['Open'] = df['Close'] * (1 + np.random.normal(0, volatility/5, size=len(df))) 
    df.loc[df.index[1:], 'Open'] = df['Close'].iloc[:-1].values 
    df.loc[df.index[0], 'Open'] = df['Close'].iloc[0] * (1 + np.random.normal(0, volatility/5))

    df['High'] = df[['Open', 'Close']].max(axis=1) * (1 + np.random.uniform(0, volatility*0.5, size=len(df)))
    df['Low'] = df[['Open', 'Close']].min(axis=1) * (1 - np.random.uniform(0, volatility*0.5, size=len(df)))
    df['High'] = df[['High', 'Open', 'Close']].max(axis=1)
    df['Low'] = df[['Low', 'Open', 'Close']].min(axis=1)

    df['Volume'] = np.random.uniform(1, 100, size=len(df)) * (1 + (df['Close'] / df['Close'].max()) * 5) 

    df = df[['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']]
    logger.info(f"Successfully generated {len(df)} simulated klines for {symbol}.")
    return df.reset_index(drop=True)


# --- Main Data Loading Function ---
def load_data(symbol, interval_str, start_date_str, end_date_str, client=None, data_filepath='btc_usdt_1h_data.csv'):
    """
    Loads OHLCV data for a given symbol and interval.
    Tries to load from a local CSV file first. If not found, fetches
    (or simulates if client is None) data and saves it to the CSV.

    Args:
        symbol (str): Trading symbol (e.g., 'BTC-USDT').
        interval_str (str): Kline interval (e.g., '1hour').
        start_date_str (str): Start date for data ('YYYY-MM-DD HH:MM:SS').
        end_date_str (str): End date for data ('YYYY-MM-DD HH:MM:SS').
        client (optional): KuCoin client object. Defaults to None.
        data_filepath (str, optional): Path to the CSV data file.
                                       Defaults to 'btc_usdt_1h_data.csv'.

    Returns:
        pd.DataFrame: DataFrame with OHLCV data, or None if loading/fetching fails.
    """
    global logger
    if not logger: logger = logging.getLogger('MLTradingModel')
    logger.info(f"Loading data for {symbol}, interval {interval_str} from {start_date_str} to {end_date_str}.")
    logger.info(f"Data filepath: {data_filepath}")

    if os.path.exists(data_filepath):
        logger.info(f"Found existing data file: {data_filepath}. Loading from CSV.")
        try:
            df = pd.read_csv(data_filepath)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            logger.info(f"Data loaded successfully from {data_filepath}. Shape: {df.shape}")
            
            mask = (df['Timestamp'] >= start_date_str) & (df['Timestamp'] <= end_date_str)
            df_filtered = df.loc[mask]
            if len(df_filtered) < len(df):
                 logger.info(f"Filtered loaded data to range {start_date_str} - {end_date_str}. Shape after filter: {df_filtered.shape}")
                 if df_filtered.empty:
                     logger.warning("Filtering resulted in empty DataFrame. Will attempt to fetch/generate new data for the specified range.")
                 else:
                     return df_filtered.reset_index(drop=True) # Return filtered if it's not empty
            elif not df_filtered.empty: # If filter didn't change anything, but it's not empty
                return df_filtered.reset_index(drop=True)
            # If filtered is empty, it means the CSV doesn't cover the new range. Proceed to fetch/generate.
            logger.info(f"CSV data does not cover the full requested range {start_date_str} - {end_date_str} after filtering, or was empty. Will attempt to fetch/generate.")

        except Exception as e:
            logger.error(f"Error loading data from {data_filepath}: {e}. Will attempt to fetch/generate.", exc_info=True)

    logger.info(f"Data file {data_filepath} not found or failed to load/filter appropriately. Fetching/generating new data.")
    df = get_historical_klines(client, symbol, interval_str, start_date_str, end_date_str)

    if df is not None and not df.empty:
        try:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                 if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            dir_name = os.path.dirname(data_filepath)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name)
                logger.info(f"Created directory: {dir_name}")

            df.to_csv(data_filepath, index=False)
            logger.info(f"Data fetched/generated and saved to {data_filepath}. Shape: {df.shape}")
            return df.reset_index(drop=True)
        except Exception as e:
            logger.error(f"Error saving data to {data_filepath}: {e}", exc_info=True)
            return df # Return df even if saving fails, if it's valid
    else:
        logger.error(f"Failed to obtain data for {symbol} using get_historical_klines.")
        return None

# --- Feature Engineering ---
def create_features(df):
    """
    Generates technical analysis features for the given OHLCV data.

    Args:
        df (pd.DataFrame): DataFrame with 'Open', 'High', 'Low', 'Close', 'Volume' columns.
                           'Timestamp' column should be the index or available.

    Returns:
        pd.DataFrame: DataFrame with added feature columns. NaNs from indicator
                      calculations result in dropped rows.
    """
    global logger
    if not logger: logger = logging.getLogger('MLTradingModel')
    logger.info(f"Starting feature creation for DataFrame with shape: {df.shape}")

    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df.dropna(subset=['Close'], inplace=True) 

    df['sma_10'] = SMAIndicator(close=df['Close'], window=10, fillna=False).sma_indicator()
    df['sma_30'] = SMAIndicator(close=df['Close'], window=30, fillna=False).sma_indicator()
    logger.debug("Calculated SMAs (10, 30).")

    df['rsi_14'] = RSIIndicator(close=df['Close'], window=14, fillna=False).rsi()
    logger.debug("Calculated RSI (14).")

    macd_indicator = MACD(close=df['Close'], window_slow=26, window_fast=12, window_sign=9, fillna=False)
    df['macd_line'] = macd_indicator.macd()
    df['macd_signal_line'] = macd_indicator.macd_signal()
    df['macd_diff'] = macd_indicator.macd_diff() 
    logger.debug("Calculated MACD (12, 26, 9).")

    bb_indicator = BollingerBands(close=df['Close'], window=20, window_dev=2, fillna=False)
    df['bb_high_band'] = bb_indicator.bollinger_hband()
    df['bb_low_band'] = bb_indicator.bollinger_lband()
    df['bb_middle_band'] = bb_indicator.bollinger_mavg() 
    df['bb_width'] = (df['bb_high_band'] - df['bb_low_band']) / df['bb_middle_band'] 
    df['bb_pband'] = bb_indicator.bollinger_pband() 
    logger.debug("Calculated Bollinger Bands (20, 2).")

    for n in [1, 2, 5]:
        df[f'log_return_{n}'] = np.log(df['Close'] / df['Close'].shift(n))
    logger.debug("Calculated Log Returns (1, 2, 5 periods).")

    df['volatility_20'] = df['log_return_1'].rolling(window=20).std()
    logger.debug("Calculated Volatility (20 periods of log_return_1).")
    
    original_rows = len(df)
    df.dropna(inplace=True)
    new_rows = len(df)
    logger.info(f"Dropped {original_rows - new_rows} rows due to NaNs from feature calculation.")
    logger.info(f"DataFrame shape after feature creation and NaN drop: {df.shape}")
    
    return df

# --- Target Variable Creation ---
def create_target(df, look_ahead_periods=1, target_threshold=0.0):
    """
    Creates a binary target variable based on future price movement.

    Args:
        df (pd.DataFrame): DataFrame with 'Close' prices (and features).
        look_ahead_periods (int, optional): Number of periods to look ahead for price change. Defaults to 1.
        target_threshold (float, optional): Percentage threshold for defining a significant move.
                                           E.g., 0.001 for 0.1%. Defaults to 0.0.
                                           If 0.0, any positive future return is 1, else 0.

    Returns:
        pd.DataFrame: DataFrame with the added 'target' column. Rows with NaN targets
                      (last 'look_ahead_periods' rows) are dropped.
    """
    global logger
    if not logger: logger = logging.getLogger('MLTradingModel')
    logger.info(f"Creating target variable with look_ahead_periods={look_ahead_periods} and target_threshold={target_threshold}.")

    df['future_return'] = (df['Close'].shift(-look_ahead_periods) / df['Close']) - 1
    df['target'] = (df['future_return'] > target_threshold).astype(int)
    
    original_rows = len(df)
    df.dropna(subset=['future_return'], inplace=True) 
    new_rows = len(df)
    logger.info(f"Dropped {original_rows - new_rows} rows due to NaNs from target creation (look_ahead).")
    logger.info(f"DataFrame shape after target creation: {df.shape}")
    
    df.drop(columns=['future_return'], inplace=True)
    
    return df

# --- Data Splitting ---
def split_data(df, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
    """
    Splits the DataFrame into training, validation, and test sets chronologically.

    Args:
        df (pd.DataFrame): The input DataFrame with features and the 'target' column.
                           Must also contain a 'Timestamp' column for logging date ranges.
        train_ratio (float, optional): Proportion of the dataset to allocate to training. Defaults to 0.7.
        val_ratio (float, optional): Proportion of the dataset to allocate to validation. Defaults to 0.15.
        test_ratio (float, optional): Proportion of the dataset to allocate to testing. Defaults to 0.15.

    Returns:
        tuple: A tuple containing six DataFrames/Series:
               (X_train, y_train, X_val, y_val, X_test, y_test)
               Returns None for all if ratios don't sum to 1 or df is too small.
    """
    global logger
    if not logger: logger = logging.getLogger('MLTradingModel')

    if not np.isclose(train_ratio + val_ratio + test_ratio, 1.0):
        logger.error(f"Train, validation, and test ratios must sum to 1.0. Got: {train_ratio + val_ratio + test_ratio}")
        return None, None, None, None, None, None

    if 'target' not in df.columns:
        logger.error("Target column 'target' not found in DataFrame for splitting.")
        return None, None, None, None, None, None
    
    if 'Timestamp' not in df.columns: 
        logger.error("Timestamp column 'Timestamp' not found in DataFrame for splitting and logging ranges.")
        return None, None, None, None, None, None


    n_samples = len(df)
    if n_samples == 0:
        logger.error("Input DataFrame for split_data is empty.")
        return None, None, None, None, None, None
        
    train_end_idx = int(n_samples * train_ratio)
    val_end_idx = train_end_idx + int(n_samples * val_ratio)

    if train_end_idx == 0 or val_end_idx <= train_end_idx or val_end_idx >= n_samples :
        logger.error(f"Invalid split indices calculated. n_samples={n_samples}, train_end={train_end_idx}, val_end={val_end_idx}. Check ratios or data size.")
        return None, None, None, None, None, None


    train_df = df.iloc[:train_end_idx]
    val_df = df.iloc[train_end_idx:val_end_idx]
    test_df = df.iloc[val_end_idx:]

    logger.info(f"Data split: Train set size: {len(train_df)}, Val set size: {len(val_df)}, Test set size: {len(test_df)}")
    if len(train_df) == 0 or len(val_df) == 0 or len(test_df) == 0:
        logger.warning("One or more data splits are empty. Check data size and ratios.")

    X_train = train_df.drop(['target', 'Timestamp'], axis=1, errors='ignore')
    y_train = train_df['target']
    X_val = val_df.drop(['target', 'Timestamp'], axis=1, errors='ignore')
    y_val = val_df['target']
    X_test = test_df.drop(['target', 'Timestamp'], axis=1, errors='ignore')
    y_test = test_df['target']
    
    logger.info("--- ML Trading Model Data Splitting Finished ---")

# --- ML Strategy Backtesting ---
def backtest_ml_strategy(model, X_data, actual_prices_close, training_columns, 
                         initial_capital=1000.0, commission_rate=0.001):
    """
    Backtests a trading strategy based on ML model predictions.

    Args:
        model: The trained machine learning model.
        X_data (pd.DataFrame): DataFrame of features for the backtest period. 
                               Its index should align with actual_prices_close.
        actual_prices_close (pd.Series): Series of actual close prices for P&L calculation,
                                         indexed identically to X_data.
        training_columns (list): List of column names used during model training for alignment.
        initial_capital (float, optional): Initial capital for the backtest. Defaults to 1000.0.
        commission_rate (float, optional): Commission rate per trade. Defaults to 0.001 (0.1%).

    Returns:
        dict: A dictionary containing backtest performance metrics and trade history.
              Returns None if a critical error occurs (e.g., data misalignment).
    """
    global logger
    if not logger: logger = logging.getLogger('MLTradingModel')

    logger.info("--- Starting ML Strategy Backtest ---")
    logger.info(f"Initial Capital: {initial_capital:.2f}, Commission Rate: {commission_rate*100:.3f}%")

    # Preprocess X_data (align with training features)
    X_data_numeric = X_data.select_dtypes(include=np.number)
    X_data_processed = X_data_numeric.reindex(columns=training_columns, fill_value=0)
    
    if X_data_processed.shape[1] != len(training_columns):
         logger.warning(f"Column mismatch for X_data_processed during backtest. Expected {len(training_columns)} features, got {X_data_processed.shape[1]}.")
         # Further logging of missing/extra columns can be added here if needed.

    # Generate model predictions (signals)
    try:
        predictions = model.predict(X_data_processed)
        logger.info(f"Generated {len(predictions)} predictions for backtesting.")
    except Exception as e:
        logger.error(f"Error generating predictions during backtest: {e}", exc_info=True)
        return None

    # Ensure actual_prices_close aligns with X_data_processed and predictions
    # X_data_processed should retain the index from X_data.
    if not X_data_processed.index.equals(actual_prices_close.index):
        logger.error("Index mismatch between X_data (features) and actual_prices_close. Cannot proceed with backtest.")
        logger.debug(f"X_data_processed index (first 5): {X_data_processed.index[:5]}")
        logger.debug(f"actual_prices_close index (first 5): {actual_prices_close.index[:5]}")
        return None
        
    if len(predictions) != len(actual_prices_close):
        logger.error(f"Length mismatch: {len(predictions)} predictions vs {len(actual_prices_close)} actual prices.")
        return None

    capital = initial_capital
    position_units = 0  # Units of asset held
    trades_history = []
    
    logger.info(f"Starting backtest simulation loop over {len(predictions)} periods...")

    for i in range(len(predictions)):
        # Use index from actual_prices_close to ensure we are using the correct timestamp.
        # X_data_processed and predictions should align with this index.
        current_idx = actual_prices_close.index[i]
        current_price = actual_prices_close.loc[current_idx]
        signal = predictions[i] # predictions is a numpy array, so use iloc-style indexing (i)
        
        # current_timestamp = actual_prices_close.index[i] # This is current_idx
        current_timestamp_log = current_idx # For logging, assuming index is timestamp-like

        log_prefix = f"Backtest ML [{current_timestamp_log}] Price: {current_price:.2f}, Signal: {signal} - "

        if signal == 1 and position_units == 0: # Buy signal and no current position
            # Buy
            capital_to_invest = capital 
            commission_amount = capital_to_invest * commission_rate
            net_capital_for_purchase = capital_to_invest - commission_amount
            
            if net_capital_for_purchase <= 0 : # Not enough to even cover commission or no capital
                logger.debug(f"{log_prefix}BUY signal, but not enough capital ({capital_to_invest:.2f}) after commission ({commission_amount:.2f}) to invest.")
                continue

            amount_to_buy = net_capital_for_purchase / current_price
            position_units = amount_to_buy
            capital = 0 # All capital invested (or rather, what's left after commission is already out)
            
            trades_history.append({
                'timestamp': current_timestamp_log, 'type': 'buy', 
                'price': current_price, 'amount': position_units, 
                'cost_incl_commission': capital_to_invest, # Log the gross cost
                'commission': commission_amount
            })
            logger.info(f"{log_prefix}BUY executed. Amount: {position_units:.6f} for {capital_to_invest:.2f} (incl comm). Capital: {capital:.2f}")

        elif signal == 0 and position_units > 0: # Sell signal (or hold if interpreted differently) and have a position
            # Sell
            sell_value_gross = position_units * current_price
            commission_amount = sell_value_gross * commission_rate
            net_sell_value = sell_value_gross - commission_amount
            
            capital = net_sell_value # This is the new capital
            sold_amount = position_units
            position_units = 0
            
            trades_history.append({
                'timestamp': current_timestamp_log, 'type': 'sell', 
                'price': current_price, 'amount': sold_amount, 'value_after_commission': capital, 
                'commission': commission_amount
            })
            logger.info(f"{log_prefix}SELL executed. Amount: {sold_amount:.6f}. Gross Value: {sell_value_gross:.2f}. Capital after comm: {capital:.2f}")
        else:
            logger.debug(f"{log_prefix}HOLD. Position Units: {position_units:.6f}, Capital: {capital:.2f}")


    # At the end of the loop, if a position is still open, close it at the last available price
    if position_units > 0:
        last_price = actual_prices_close.iloc[-1]
        last_timestamp = actual_prices_close.index[-1]
        logger.info(f"End of backtest: Closing open position of {position_units:.6f} at price {last_price:.2f}.")
        
        sell_value_gross = position_units * last_price
        commission_amount = sell_value_gross * commission_rate
        net_sell_value = sell_value_gross - commission_amount
        
        capital = net_sell_value
        sold_amount = position_units
        position_units = 0 # Position closed
        
        trades_history.append({
            'timestamp': last_timestamp, 'type': 'sell_eod', 
            'price': last_price, 'amount': sold_amount, 'value_after_commission': capital,
            'commission': commission_amount
        })
        logger.info(f"Closed EOD position. Amount: {sold_amount:.6f}. Capital after comm: {capital:.2f}")

    # Calculate Performance Metrics
    final_capital = capital
    total_pnl = final_capital - initial_capital
    total_return_pct = (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0
    num_buy_trades = len([t for t in trades_history if t['type'] == 'buy'])
    num_sell_trades = len([t for t in trades_history if t['type'] == 'sell' or t['type'] == 'sell_eod']) # All sells

    backtest_metrics = {
        "initial_capital": initial_capital,
        "final_capital": final_capital,
        "total_pnl": total_pnl,
        "total_return_pct": total_return_pct,
        "num_buy_trades": num_buy_trades,
        "num_sell_trades": num_sell_trades, # Total sell operations
        "total_trade_cycles": num_buy_trades, # Each buy could be considered a start of a trade cycle
        "trade_history": trades_history # Keep full history for potential detailed analysis
    }

    logger.info("--- ML Strategy Backtest Finished ---")
    logger.info(f"Initial Capital: {initial_capital:.2f}")
    logger.info(f"Final Capital: {final_capital:.2f}")
    logger.info(f"Total P&L: {total_pnl:.2f}")
    logger.info(f"Total Return: {total_return_pct:.2f}%")
    logger.info(f"Number of Buy Trades: {num_buy_trades}")
    logger.info(f"Number of Sell Trades (incl. EOD): {num_sell_trades}")
    
    if trades_history:
        logger.info("Sample Trades (first 3 and last 3 if many):")
        display_trades = trades_history[:3]
        if len(trades_history) > 6:
            # To avoid printing "..." as a dict if there are exactly 4, 5, or 6 trades
            if len(trades_history) > 3 : display_trades.append("...")
            display_trades.extend(trades_history[-3:])
        
        for trade in display_trades:
            if isinstance(trade, str) and trade == "...":
                logger.info("  ...")
            else: # It's a dictionary
                 trade_amount = trade.get('amount', 'N/A')
                 if isinstance(trade_amount, float): trade_amount_str = f"{trade_amount:.6f}"
                 else: trade_amount_str = str(trade_amount)
                 logger.info(f"  Trade: Timestamp={trade.get('timestamp', 'N/A')}, Type={trade.get('type','N/A')}, Price={trade.get('price',0):.2f}, Amount={trade_amount_str}")

    else:
        logger.info("No trades were executed during the backtest.")

    return backtest_metrics
    return X_train, y_train, X_val, y_val, X_test, y_test

# --- Model Training ---
def train_decision_tree(X_train, y_train, X_val=None, y_val=None, model_params=None):
    """
    Trains a Decision Tree Classifier model.

    Args:
        X_train (pd.DataFrame): Training features.
        y_train (pd.Series): Training target variable.
        X_val (pd.DataFrame, optional): Validation features for preliminary evaluation.
        y_val (pd.Series, optional): Validation target variable for preliminary evaluation.
        model_params (dict, optional): Hyperparameters for DecisionTreeClassifier.
                                       If None, defaults to {'random_state': 42}.

    Returns:
        tuple: (trained_model, list_of_training_columns)
               The trained Decision Tree model and the list of column names used for training.
    """
    global logger
    if not logger: logger = logging.getLogger('MLTradingModel')

    logger.info("Starting Decision Tree model training...")
    
    if model_params is None:
        model_params = {'random_state': 42}
    elif 'random_state' not in model_params: # Ensure reproducibility if other params are set
        model_params['random_state'] = 42
        
    logger.info(f"Using model parameters: {model_params}")

    model = DecisionTreeClassifier(**model_params)
    
    X_train_numeric = X_train.select_dtypes(include=np.number)
    training_columns = X_train_numeric.columns.tolist() # Store column names

    if X_train_numeric.shape[1] < X_train.shape[1]:
        dropped_cols = set(X_train.columns) - set(X_train_numeric.columns)
        logger.warning(f"Non-numeric columns dropped from X_train for training: {dropped_cols}")
    
    logger.info(f"Training model with {len(training_columns)} features: {training_columns}")
    model.fit(X_train_numeric, y_train)
    logger.info("Decision Tree model trained successfully.")

    if X_val is not None and y_val is not None:
        X_val_numeric = X_val.select_dtypes(include=np.number)
        # Align columns with training data, crucial for consistent evaluation
        X_val_aligned = X_val_numeric.reindex(columns=training_columns, fill_value=0)

        # Log if alignment changed columns (e.g., new columns in val not in train, or vice versa)
        if X_val_aligned.shape[1] != X_val_numeric.shape[1] or not X_val_aligned.columns.equals(X_val_numeric.columns):
             logger.warning("X_val columns were realigned with training columns for validation.")
        
        unseen_cols_in_val = set(X_val_numeric.columns) - set(training_columns)
        if unseen_cols_in_val:
            logger.warning(f"Columns in X_val_numeric not present in training_columns (dropped by reindex for validation): {unseen_cols_in_val}")
        missing_cols_in_val = set(training_columns) - set(X_val_numeric.columns)
        if missing_cols_in_val:
             logger.warning(f"Columns in training_columns not present in X_val_numeric (filled with 0 by reindex for validation): {missing_cols_in_val}")


        y_pred_val = model.predict(X_val_aligned)
        accuracy = accuracy_score(y_val, y_pred_val)
        logger.info(f"Preliminary validation accuracy: {accuracy:.4f}")
    
    return model, training_columns

# --- Model Evaluation ---
def evaluate_model(model, X_test, y_test, training_columns):
    """
    Evaluates the trained model on the test set using various classification metrics.

    Args:
        model: The trained scikit-learn compatible classifier model.
        X_test (pd.DataFrame): Test features.
        y_test (pd.Series): True labels for the test set.
        training_columns (list): List of column names (features) that the model
                                 was trained on. `X_test` will be aligned to these columns.

    Returns:
        dict: A dictionary containing key evaluation metrics (accuracy, precision,
              recall, f1_score, roc_auc, confusion_matrix, classification_report_str).
              Returns None if evaluation encounters a significant error.
    """
    global logger
    if not logger: logger = logging.getLogger('MLTradingModel')

    logger.info("--- Starting Model Evaluation on Test Set ---")

    if not hasattr(model, 'predict'):
        logger.error("Provided model object does not have a 'predict' method. Cannot evaluate.")
        return None

    # Preprocess X_test: select numeric and align columns with training data
    X_test_numeric = X_test.select_dtypes(include=np.number)
    
    # Align X_test columns with the columns used during training
    X_test_aligned = X_test_numeric.reindex(columns=training_columns, fill_value=0)
    
    # Log potential discrepancies after alignment
    if X_test_aligned.shape[1] != len(training_columns): # General check
        logger.warning(f"Column count mismatch after aligning X_test. Expected {len(training_columns)} features based on training, got {X_test_aligned.shape[1]}.")
    
    missing_cols_in_test = set(training_columns) - set(X_test_numeric.columns)
    if missing_cols_in_test: 
        logger.warning(f"Columns present in training but missing in X_test (filled with 0 by reindex): {missing_cols_in_test}")
    
    extra_cols_in_test = set(X_test_numeric.columns) - set(training_columns)
    if extra_cols_in_test:
        logger.warning(f"Extra columns present in X_test but not in training (were dropped by reindex): {extra_cols_in_test}")

    logger.info(f"Evaluating model with {X_test_aligned.shape[1]} features aligned with training data: {X_test_aligned.columns.tolist()}")

    # Make predictions
    try:
        y_pred_test = model.predict(X_test_aligned)
    except Exception as e:
        logger.error(f"Error during model.predict(X_test_aligned): {e}", exc_info=True)
        logger.error(f"X_test_aligned columns: {X_test_aligned.columns.tolist()}")
        logger.error(f"Model's expected features (if available): {getattr(model, 'feature_names_in_', 'N/A')}") # Scikit-learn models store feature names
        return None
        
    metrics = {}
    try:
        accuracy = accuracy_score(y_test, y_pred_test)
        
        unique_labels_y_test = y_test.unique()
        unique_labels_y_pred = np.unique(y_pred_test) 
        present_labels = sorted(list(set(unique_labels_y_test) | set(unique_labels_y_pred)))
        
        if not present_labels : 
            present_labels = [0, 1] 
            logger.warning("No labels found in y_test or y_pred_test. Defaulting to [0, 1] for metrics.")
        elif len(present_labels) == 1: 
            single_label = present_labels[0]
            if single_label == 0: present_labels = [0, 1]
            elif single_label == 1: present_labels = [0, 1]
            else: 
                logger.warning(f"Only a single, non-standard label ({single_label}) found. Metrics may be misleading. Forcing labels [0,1].")
                present_labels = [0,1]

        precision_class1 = precision_score(y_test, y_pred_test, labels=present_labels, pos_label=1, zero_division=0)
        recall_class1 = recall_score(y_test, y_pred_test, labels=present_labels, pos_label=1, zero_division=0)
        f1_class1 = f1_score(y_test, y_pred_test, labels=present_labels, pos_label=1, zero_division=0)

        precision_weighted = precision_score(y_test, y_pred_test, average='weighted', labels=present_labels, zero_division=0)
        recall_weighted = recall_score(y_test, y_pred_test, average='weighted', labels=present_labels, zero_division=0)
        f1_weighted = f1_score(y_test, y_pred_test, average='weighted', labels=present_labels, zero_division=0)

        cm = confusion_matrix(y_test, y_pred_test, labels=present_labels)
        target_names_for_report = [f"Class {l}" for l in present_labels]
        report_str = classification_report(y_test, y_pred_test, labels=present_labels, target_names=target_names_for_report, zero_division=0)
        report_dict = classification_report(y_test, y_pred_test, labels=present_labels, target_names=target_names_for_report, zero_division=0, output_dict=True)

        logger.info(f"Test Set Accuracy: {accuracy:.4f}")
        logger.info(f"Test Set Precision (Class 1 - Buy Signal): {precision_class1:.4f}")
        logger.info(f"Test Set Recall (Class 1 - Buy Signal): {recall_class1:.4f}")
        logger.info(f"Test Set F1-Score (Class 1 - Buy Signal): {f1_class1:.4f}")
        logger.info(f"Test Set Precision (Weighted Avg): {precision_weighted:.4f}")
        logger.info(f"Test Set Recall (Weighted Avg): {recall_weighted:.4f}")
        logger.info(f"Test Set F1-Score (Weighted Avg): {f1_weighted:.4f}")
        logger.info(f"Test Set Confusion Matrix (Labels: {present_labels}):\n{cm}")
        logger.info(f"Test Set Classification Report:\n{report_str}")

        metrics = {
            'accuracy': accuracy,
            'precision_class1': precision_class1,
            'recall_class1': recall_class1,
            'f1_score_class1': f1_class1,
            'precision_weighted': precision_weighted,
            'recall_weighted': recall_weighted,
            'f1_score_weighted': f1_weighted,
            'confusion_matrix': cm.tolist(), 
            'classification_report_str': report_str,
            'classification_report_dict': report_dict 
        }

        if hasattr(model, "predict_proba") and len(np.unique(y_test)) > 1: 
            try:
                y_pred_proba_test = model.predict_proba(X_test_aligned)[:, 1] 
                fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba_test)
                roc_auc = auc(fpr, tpr)
                logger.info(f"Test Set ROC AUC: {roc_auc:.4f}")
                metrics['roc_auc'] = roc_auc
            except Exception as e_roc:
                logger.error(f"Error calculating ROC AUC: {e_roc}", exc_info=True)
                metrics['roc_auc'] = None 
        elif len(np.unique(y_test)) <= 1:
            logger.warning("ROC AUC calculation skipped: y_test contains only one class.")
            metrics['roc_auc'] = None
        else:
            logger.info("Model does not support predict_proba, skipping ROC AUC calculation.")
            metrics['roc_auc'] = None

    except Exception as e:
        logger.error(f"Error during metrics calculation: {e}", exc_info=True)
        return None 

    logger.info("--- Model Evaluation Finished ---")
    return metrics

if __name__ == "__main__":
    logger = setup_ml_logging() # Initialize logger

    logger.info("--- Starting ML Trading Model Data Preparation & Feature Engineering ---")

    # Define parameters
    SYMBOL = 'BTC-USDT'
    INTERVAL = '1hour' # Use '1hour' as string
    
    END_DATE_DT = datetime.datetime.now()
    # For 2 years of data
    START_DATE_DT = END_DATE_DT - datetime.timedelta(days=2*365) 
    
    START_DATE_STR = START_DATE_DT.strftime('%Y-%m-%d %H:%M:%S')
    END_DATE_STR = END_DATE_DT.strftime('%Y-%m-%d %H:%M:%S')
    
    kucoin_client = None 

    data_file = f"{SYMBOL.replace('/', '_')}_{INTERVAL}_data_ml.csv" 

    market_data = load_data(
        symbol=SYMBOL, 
        interval_str=INTERVAL, 
        start_date_str=START_DATE_STR, 
        end_date_str=END_DATE_STR,
        client=kucoin_client,
        data_filepath=data_file
    )
    
    if market_data is not None and not market_data.empty:
        features_df = create_features(market_data.copy()) 
        
        if features_df is not None and not features_df.empty:
            logger.info(f"Features created successfully. DataFrame shape: {features_df.shape}")
            logger.info("First 5 rows with features:\n" + features_df.head().to_string())
            logger.info("Last 5 rows with features:\n" + features_df.tail().to_string())

            TARGET_LOOK_AHEAD = 1 
            TARGET_THRESHOLD = 0.000 

            final_df = create_target(features_df.copy(), look_ahead_periods=TARGET_LOOK_AHEAD, target_threshold=TARGET_THRESHOLD)

            if final_df is not None and not final_df.empty:
                logger.info(f"Target variable created successfully. Final DataFrame shape: {final_df.shape}")
                logger.info("First 5 rows with target:\n" + final_df.head().to_string())
                logger.info("Last 5 rows with target:\n" + final_df.tail().to_string())
                
                logger.info("Target variable distribution:")
                logger.info("\n" + final_df['target'].value_counts(normalize=True).to_string())
            else:
                logger.error("Failed to create target variable or DataFrame became empty.")
        else:
            logger.error("Failed to create features or DataFrame became empty.")
        
        if final_df is not None and not final_df.empty:
            # Split data
            X_train, y_train, X_val, y_val, X_test, y_test = split_data(final_df)

            if X_train is not None: 
                logger.info(f"X_train shape: {X_train.shape}, y_train shape: {y_train.shape}")
                logger.info(f"X_val shape: {X_val.shape}, y_val shape: {y_val.shape}")
                logger.info(f"X_test shape: {X_test.shape}, y_test shape: {y_test.shape}")

                # Log timestamp ranges from the original final_df before 'Timestamp' is dropped from X sets
                # This requires accessing Timestamp from the original train_df, val_df, test_df inside split_data
                # or passing the X sets with Timestamp and dropping it just before training/evaluation.
                # For simplicity, if Timestamp was crucial for this specific log, it should be handled carefully.
                # The current split_data drops Timestamp from X sets.
                # We can still log the index range if it's meaningful (e.g., if reset_index was not True everywhere)
                # Or, more robustly, log from final_df slices.
                
                # Example: Log Timestamp ranges from final_df based on split indices
                train_end_idx_log = int(len(final_df) * 0.7)
                val_end_idx_log = train_end_idx_log + int(len(final_df) * 0.15)

                if not X_train.empty: # X_train itself doesn't have Timestamp
                    logger.info(f"Train data time range (from original df): {final_df['Timestamp'].iloc[0]} to {final_df['Timestamp'].iloc[train_end_idx_log-1]}")
                if not X_val.empty:
                    logger.info(f"Val data time range (from original df): {final_df['Timestamp'].iloc[train_end_idx_log]} to {final_df['Timestamp'].iloc[val_end_idx_log-1]}")
                if not X_test.empty:
                    logger.info(f"Test data time range (from original df): {final_df['Timestamp'].iloc[val_end_idx_log]} to {final_df['Timestamp'].iloc[-1]}")
            else:
                logger.error("Data splitting failed.")
            
            if X_train is not None and not X_train.empty: 
                dt_params = {
                    'max_depth': 10,        
                    'min_samples_split': 50, 
                    'min_samples_leaf': 25,  
                    'random_state': 42
                }
                logger.info(f"Defined Decision Tree parameters: {dt_params}")
                
                X_train_model = X_train # Already processed by split_data
                X_val_model = X_val     # Already processed by split_data
                
                trained_dt_model, model_training_cols = train_decision_tree(
                    X_train_model, y_train, 
                    X_val_model, y_val, 
                    model_params=dt_params
                )

                if trained_dt_model:
                    logger.info("Decision Tree model training complete.")
                    model_filename = "decision_tree_model.joblib"
                    columns_filename = "decision_tree_model_columns.joblib" 

                    try:
                        joblib.dump(trained_dt_model, model_filename)
                        logger.info(f"Trained Decision Tree model saved as {model_filename}")
                        
                        joblib.dump(model_training_cols, columns_filename)
                        logger.info(f"Model training columns saved as {columns_filename}")

                        # --- Model Evaluation Step ---
                        logger.info(f"Loading model from {model_filename} for evaluation...")
                        loaded_model_for_eval = joblib.load(model_filename)
                        logger.info(f"Loading training columns from {columns_filename} for evaluation...")
                        loaded_training_columns_for_eval = joblib.load(columns_filename)
                        
                        X_test_model = X_test # Already processed by split_data
                        if X_test_model is not None and y_test is not None and not X_test_model.empty:
                            if loaded_model_for_eval and loaded_training_columns_for_eval:
                                logger.info("Proceeding to evaluate model on the test set.")
                                evaluation_metrics = evaluate_model(
                                    loaded_model_for_eval, 
                                    X_test_model, 
                                    y_test, 
                                    loaded_training_columns_for_eval
                                )
                                if evaluation_metrics:
                                    logger.info("Model evaluation on test set successful. Metrics logged above.")
                                else:
                                    logger.error("Model evaluation on test set returned no metrics or failed.")
                            else:
                                logger.error("Failed to load model or training columns. Cannot evaluate.")
                        else:
                            logger.warning("X_test or y_test is None or empty. Skipping model evaluation on test set.")

                    except FileNotFoundError as fnf_e:
                        logger.error(f"Error: Model or columns file not found during load for evaluation. {fnf_e}", exc_info=True)
                    except Exception as e:
                        logger.error(f"Error during model saving/loading or evaluation: {e}", exc_info=True)
                else:
                    logger.error("Failed to train Decision Tree model.")
            else:
                logger.error("Training skipped as X_train is None or empty after splitting.")

        else:
            logger.error("Cannot proceed to model training as final_df is None or empty.")
    else:
        logger.error(f"Failed to load or generate data for {SYMBOL}. Cannot proceed.")

    logger.info("--- ML Trading Model Script Finished ---")
