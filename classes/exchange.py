import ccxt
from _decimal import Decimal
from ccxt import ExchangeError
import decimal

class Exchange:
    markets = {}

    def __init__(self, exchange_name, api_key=None, secret=None, passphrase=None, testnet=False, defaultType=None):
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        self.testnet = testnet
        self.defaultType = defaultType
        self.exchange_class = self.get_exchange_class()

    def get_exchange_class(self):
        exchange_options = {
            'apiKey': self.api_key,
            'secret': self.secret,
            'password': self.passphrase,
            'enableRateLimit': True,
            'options': {'adjustForTimeDifference': True}
        }

        if self.testnet:
            exchange_options['options']['defaultType'] = 'future'
            exchange_options['options']['urls']['api'] = exchange_options['options']['urls']['test']
            exchange_options['options']['urls']['www'] = exchange_options['options']['urls']['test']

        if self.defaultType:
            exchange_options['options']['defaultType'] = self.defaultType

        if self.exchange_name == 'binance':
            exchange_class = ccxt.binance(exchange_options)
            if self.testnet:
                exchange_class.urls['api'] = exchange_class.urls['api'].replace('binance.', 'testnet.binance.')
        elif self.exchange_name == 'kucoinfutures':
            exchange_class = ccxt.kucoin(exchange_options)
            if self.testnet:
                exchange_class.urls['api'] = exchange_class.urls['api'].replace('api', 'futures-test')
                exchange_class.urls['www'] = exchange_class.urls['www'].replace('www', 'futures-test')
            if self.defaultType:
                exchange_class.urls['api'] = exchange_class.urls['api'].replace('api', 'futures-api')
                exchange_class.urls['www'] = exchange_class.urls['www'].replace('www', 'futures')
        elif self.exchange_name == 'kucoin':
            exchange_class = ccxt.kucoin(exchange_options)
        elif self.exchange_name == 'bybit':
            exchange_class = ccxt.bybit(exchange_options)
            if self.testnet:
                exchange_class.urls['api'] = exchange_class.urls['api'].replace('api', 'api-testnet')
                exchange_class.urls['www'] = exchange_class.urls['www'].replace('www', 'www-testnet')
        elif self.exchange_name == 'binanceusdm':
            exchange_class = ccxt.binanceusdm(exchange_options)
            if self.defaultType:
                exchange_class.urls['api'] = exchange_class.urls['api'].replace('binance.', 'fapi.')
        elif self.exchange_name == 'coinbasepro':
            exchange_class = ccxt.coinbasepro(exchange_options)
        else:
            raise ValueError(f"Unsupported exchange: {self.exchange_name}")

        return exchange_class

    def get_trading_fees(self, symbol):
        try:
            fees = self.exchange_class.fetch_trading_fees(symbol)
            maker_fee = fees['maker']
            taker_fee = fees['taker']
            return maker_fee, taker_fee
        except Exception as e:
            print(f"Error fetching trading fees for {self.exchange_name}: {e}")
            return None, None

    def get_available_leverage(self, symbol):
        # Check if testnet is supported for the exchange
        if self.testnet:
            if hasattr(self.exchange_class, 'futures_get_leverage_brackets'):
                # Load leverage information for the testnet exchange
                leverage_info = self.exchange_class.futures_get_leverage_brackets(symbol)
                return [float(level['initialLeverage']) for level in leverage_info]
            else:
                # Testnet not supported for this exchange, return None
                return None
        else:
            # Load leverage information for the live exchange
            leverage_info = self.exchange_class.futures_get_leverage_brackets(symbol)
            return [float(level['initialLeverage']) for level in leverage_info]

    def load_markets(self):
        """Load all available markets for the exchange."""
        if not Exchange.markets:
            exchange_client = self.get_exchange_class()
            try:
                Exchange.markets = exchange_client.load_markets()
            except ccxt.ExchangeError as e:
                raise ExchangeError(f"Error loading markets for {self.exchange_name}: {e}")

        return Exchange.markets

    def get_time_intervals(self):
        timeframes = None
        try:
            self.exchange_class.load_markets()
            timeframes = self.exchange_class.timeframes.keys()
        except ccxt.ExchangeError as e:
            print(f"Error loading timeframes for {self.exchange_name}: {e}")
        return timeframes

    def set_testnet(self):
        self.testnet = True
        return False

    def get_balance(self, currency):
        balance = self.exchange_class.fetch_balance()[currency]
        return balance['free']

    # Fetch the account balance
    def fetch_balance(self, type='trading', currency=None):
        balance = self.exchange_class.fetch_balance()
        if type:
            balance = balance[type]
        if currency:
            balance = balance[currency]
        return balance

    def get_total_balance(self):
        # Retrieve the balance for all currencies in the exchange
        balance = self.exchange_class.fetch_balance()

        # Calculate the total value in USDT
        usdt_value = 0.0
        for currency in balance:
            if currency != 'USDT':
                ticker = self.exchange_class.fetch_ticker(f"{currency}/USDT")
                usdt_value += balance[currency] * ticker['last']
            else:
                usdt_value += balance[currency]

        return usdt_value

    def get_usdt_balance(self):
        # Retrieve the balance for all currencies in the account
        balance = self.exchange_class.fetch_balance()

        # Calculate the available USDT balance
        if 'USDT' in balance:
            usdt_balance = balance['USDT']['free']
        else:
            usdt_balance = 0.0

        return usdt_balance

    def get_ticker(self, symbol):
        try:
            return self.exchange_class.fetch_ticker(symbol)
        except Exception as e:
            print(f"Error getting ticker for {symbol}: {e}")
            return None

    def get_ticker_price(self, symbol):
        ticker = self.exchange_class.fetch_ticker(symbol)
        return ticker['last'] if ticker else None

    def create_limit_order(self, symbol, side, amount, price):
        order = None
        try:
            order = self.exchange_class.create_order(symbol, 'limit', side, amount, price)
        except Exception as e:
            print(f"Failed to create limit order: {e}")
        return order

    def create_market_order(self, symbol, side, amount):
        order = None
        try:
            order = self.exchange_class.create_order(symbol, 'market', side, amount)
        except Exception as e:
            print(f"Failed to create market order: {e}")
        return order

    def cancel_order(self, symbol, order_id):
        exchange_order = None
        try:
            exchange_order = self.exchange_class.cancel_order(order_id, symbol=symbol)
            # if exchange_order:
            # order = self.session.query(Positions).filter_by(exchange=self.exchange_name, order_id=exchange_order['id']).first()
            # if order:
            #   order.status = exchange_order['status']
            #   self.session.commit()
        except Exception as e:
            print(f"Error cancelling order on {self.exchange_name}: {e}")
        return exchange_order

    def get_order_status(self, symbol, order_id):
        status = None
        try:
            exchange_order = self.exchange_class.fetch_order(order_id, symbol=symbol)
            status = exchange_order['status'] if exchange_order else None
        except Exception as e:
            print(f"Error getting order status on {self.exchange_name}: {e}")
        return status

    def create_order(self, side, order_type, symbol, amount, price=None):
        try:
            order_params = {'type': order_type, 'side': side, 'symbol': symbol, 'amount': amount}
            if price:
                order_params['price'] = price
            response = self.exchange_class.create_order(**order_params)
            return response
        except Exception as e:
            print(f"Error placing {order_type} order on {self.exchange_name}: {e}")
            return None

    def create_testnet_order(self, side, order_type, symbol, amount, price=None):
        if not self.testnet:
            print("Error: create_testnet_order can only be used with testnet exchanges.")
            return None
        try:
            order_params = {'type': order_type, 'side': side, 'symbol': symbol, 'amount': amount}
            if price:
                order_params['price'] = price
            response = self.exchange_class.create_order(**order_params)
            return response
        except Exception as e:
            print(f"Error placing {order_type} order on {self.exchange_name} testnet: {e}")
            return None

    def amount_to_precision(self, symbol, quantity, precision=None, rounding_mode=None):
        if symbol not in self.exchange_class.markets:
            raise ValueError(f"{symbol} not found in markets dictionary. Please call load_markets() first.")
        if precision is None:
            precision = self.exchange_class.markets[symbol]['precision']['amount']
        if rounding_mode is None:
            rounding_mode = decimal.ROUND_HALF_UP
        return Decimal(str(quantity)).quantize(Decimal(str(precision)), rounding=rounding_mode)
