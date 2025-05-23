import unittest
import pandas as pd
import numpy as np
from datetime import datetime

# Assuming kucoin_scalping_bot.py is in the same directory or accessible in PYTHONPATH
from kucoin_scalping_bot import (
    calculate_moving_averages,
    generate_signals,
    strategy_decision,
    calculate_position_size,
    setup_logging # Import to ensure logger is configured for bot functions if they use global logger
)

class TestBotLogic(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Setup logging for the bot functions if they rely on a global logger initialized elsewhere
        # This is to prevent errors if bot functions try to log during tests
        # and the main script's logger setup hasn't run.
        # However, ideally, functions should accept a logger instance or get it via logging.getLogger.
        # For this test suite, we'll assume functions can run without pre-configured global logger
        # or they handle logger initialization safely (e.g. `if not logger: logger = ...`)
        # If functions directly use a global `logger` variable that `setup_logging` initializes,
        # we might need to call `setup_logging()` here or pass logger instances.
        # For now, the bot's functions have `global logger; if not logger: logger = ...`
        # which should be okay.
        pass

    def test_calculate_moving_averages(self):
        data = {
            'Timestamp': pd.to_datetime(['2023-01-01 10:00', '2023-01-01 10:01', '2023-01-01 10:02', 
                                          '2023-01-01 10:03', '2023-01-01 10:04', '2023-01-01 10:05']),
            'Close': [10, 12, 11, 13, 14, 15]
        }
        df = pd.DataFrame(data)
        
        # Test with valid data
        df_ma = calculate_moving_averages(df.copy(), short_window=2, long_window=4)
        self.assertTrue('short_ma' in df_ma.columns)
        self.assertTrue('long_ma' in df_ma.columns)
        
        # Expected values (manual calculation with min_periods=1)
        # Close: [10, 12, 11, 13, 14, 15]
        # Short MA (2, min_periods=1):
        # 10.0 (10/1)
        # 11.0 ((10+12)/2)
        # 11.5 ((12+11)/2)
        # 12.0 ((11+13)/2)
        # 13.5 ((13+14)/2)
        # 14.5 ((14+15)/2)
        expected_short_ma = pd.Series([10.0, 11.0, 11.5, 12.0, 13.5, 14.5], name='short_ma')
        pd.testing.assert_series_equal(df_ma['short_ma'], expected_short_ma, check_dtype=False, rtol=1e-5)

        # Long MA (4, min_periods=1):
        # 10.0 (10/1)
        # 11.0 ((10+12)/2)
        # 11.0 ((10+12+11)/3)
        # 11.5 ((10+12+11+13)/4)
        # 12.5 ((12+11+13+14)/4)
        # 13.25 ((11+13+14+15)/4)
        expected_long_ma = pd.Series([10.0, 11.0, (10+12+11)/3.0, 11.5, 12.5, 13.25], name='long_ma')
        pd.testing.assert_series_equal(df_ma['long_ma'], expected_long_ma, check_dtype=False, rtol=1e-5)

        # Test with empty DataFrame
        empty_df = pd.DataFrame(columns=['Timestamp', 'Close'])
        df_empty_ma = calculate_moving_averages(empty_df.copy(), short_window=2, long_window=4)
        self.assertTrue('short_ma' in df_empty_ma.columns) # Columns are added
        self.assertTrue(df_empty_ma['short_ma'].empty)

        # Test with insufficient data for full window (due to min_periods=1, it will still calculate)
        short_df_data = {'Timestamp': pd.to_datetime(['2023-01-01 10:00']), 'Close': [10]}
        short_df = pd.DataFrame(short_df_data)
        df_short_ma = calculate_moving_averages(short_df.copy(), short_window=2, long_window=4)
        self.assertEqual(df_short_ma['short_ma'].iloc[0], 10)
        self.assertEqual(df_short_ma['long_ma'].iloc[0], 10)

        # Test with no 'Close' column
        no_close_df = pd.DataFrame({'Timestamp': pd.to_datetime(['2023-01-01 10:00']), 'Price': [10]})
        df_no_close = calculate_moving_averages(no_close_df.copy(), short_window=2, long_window=4)
        self.assertFalse('short_ma' in df_no_close.columns) # Should not add columns if 'Close' is missing

    def test_generate_signals(self):
        data = {
            'Timestamp': pd.to_datetime(['2023-01-01 10:00', '2023-01-01 10:01', '2023-01-01 10:02', 
                                          '2023-01-01 10:03', '2023-01-01 10:04']),
            'short_ma': [10, 11, 10, 9,  12], # Simulate short_ma
            'long_ma':  [11, 10, 11, 10, 10]  # Simulate long_ma
        }
        df = pd.DataFrame(data)
        
        # Expected signals:
        # t0: short (10) < long (11) -> no signal (0) (no previous data for crossover)
        # t1: short (11) > long (10). Prev: short (10) < long (11). Crossover BUY (1)
        # t2: short (10) < long (11). Prev: short (11) > long (10). Crossover SELL (-1)
        # t3: short (9) < long (10). Prev: short (10) < long (11). No crossover (0)
        # t4: short (12) > long (10). Prev: short (9) < long (10). Crossover BUY (1)
        
        df_signals = generate_signals(df.copy())
        self.assertTrue('signal' in df_signals.columns)
        expected_signals = pd.Series([0, 1, -1, 0, 1], name='signal')
        pd.testing.assert_series_equal(df_signals['signal'], expected_signals, check_dtype=False)

        # Test with no MA columns
        no_ma_df = pd.DataFrame({'Timestamp': pd.to_datetime(['2023-01-01 10:00'])})
        df_no_ma = generate_signals(no_ma_df.copy())
        self.assertFalse('signal' in df_no_ma.columns) # Should not add signal if MAs missing

    def test_strategy_decision(self):
        # Create a dummy DataFrame with a 'signal' column and 'Timestamp'
        # The content of other columns doesn't matter for this specific test
        def create_test_df(signal_value):
            return pd.DataFrame({'Timestamp': [datetime.now()], 'signal': [signal_value]})

        # Scenario 1: Buy signal, no current position -> 'buy'
        self.assertEqual(strategy_decision(create_test_df(1), 'none'), 'buy')
        
        # Scenario 2: Buy signal, already in long position -> 'hold'
        self.assertEqual(strategy_decision(create_test_df(1), 'long'), 'hold')
        
        # Scenario 3: Sell signal, in long position -> 'sell'
        self.assertEqual(strategy_decision(create_test_df(-1), 'long'), 'sell')
        
        # Scenario 4: Sell signal, no current position -> 'hold'
        self.assertEqual(strategy_decision(create_test_df(-1), 'none'), 'hold')
        
        # Scenario 5: No signal (0), no current position -> 'hold'
        self.assertEqual(strategy_decision(create_test_df(0), 'none'), 'hold')
        
        # Scenario 6: No signal (0), in long position -> 'hold'
        self.assertEqual(strategy_decision(create_test_df(0), 'long'), 'hold')

        # Scenario 7: Empty DataFrame
        self.assertEqual(strategy_decision(pd.DataFrame(columns=['Timestamp', 'signal']), 'none'), 'hold')


    def test_calculate_position_size(self):
        # Test with simulated balance
        # Client is None for these tests, relying on simulated_balance_usdt
        symbol = "BTC-USDT"
        available_capital_percentage = 0.1 # 10%
        last_price = 20000.0
        simulated_balance = 1000.0 # USDT
        
        expected_capital_to_use = simulated_balance * available_capital_percentage # 100 USDT
        expected_amount = expected_capital_to_use / last_price # 100 / 20000 = 0.005 BTC
        
        amount = calculate_position_size(None, symbol, available_capital_percentage, last_price, simulated_balance)
        self.assertAlmostEqual(amount, expected_amount)

        # Test with zero price (should return None or raise error, current returns None)
        amount_zero_price = calculate_position_size(None, symbol, available_capital_percentage, 0, simulated_balance)
        self.assertIsNone(amount_zero_price)

        # Test with zero capital percentage
        amount_zero_perc = calculate_position_size(None, symbol, 0, last_price, simulated_balance)
        self.assertEqual(amount_zero_perc, 0)
        
        # Test with zero balance
        amount_zero_bal = calculate_position_size(None, symbol, available_capital_percentage, last_price, 0)
        self.assertEqual(amount_zero_bal, 0)

if __name__ == '__main__':
    unittest.main()
