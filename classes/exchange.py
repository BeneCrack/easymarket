import ccxt
from _decimal import Decimal
from ccxt import ExchangeError
import decimal


class Exchange(ccxt.Exchange):
    markets = {}
    instances = {}

    def __init__(self, account):
        super().__init__()
        self.account_id = account.id
        self.exchange_name = account.exchangemodels.short
        self.api_key = account.api_key
        self.secret = account.api_secret
        self.passphrase = account.password
        self.testnet = bool(account.testnet)
        self.urls = {}  # initialize urls to an empty dictionary
        self.exchange_instance = self.get_instance()

    def get_instance(self):
        if self.account_id in Exchange.instances:
            print("Found Exchange Instance")
            return Exchange.instances[self.account_id]

        exchange = getattr(ccxt, self.exchange_name)(self.build_exchange_options())
        exchange.set_sandbox_mode(self.testnet)
        #print(exchange.fetch_balance()['total']['USDT'])
        Exchange.instances[self.account_id] = exchange
        return exchange

    def build_exchange_options(self):
        exchange_options = {
            'apiKey': self.api_key,
            'secret': self.secret,
            'password': self.passphrase,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
                'defaultType': 'future',
                'test': self.testnet
            }  # Enable testnet
        }
        return exchange_options

    #def transfer(self, symbol):


    def get_trading_fees(self, symbol):
        try:
            fees = self.exchange_instance.fetch_trading_fees(symbol)
            maker_fee = fees['maker']
            taker_fee = fees['taker']
            return maker_fee, taker_fee
        except Exception as e:
            print(f"Error fetching trading fees for {self.exchange_name}: {e}")
            return None, None

    def get_available_leverage(self, symbol):
        # Check if testnet is supported for the exchange
        print("we here2")
        if self.testnet:
            if hasattr(self.exchange_instance, 'fetch_markets'):
                # Load markets information for the testnet exchange
                markets = self.exchange_instance.fetch_markets()
                market = next((m for m in markets if m['symbol'] == symbol), None)
                if market:
                    print(market)
                    print("market")
                    max_leverage = int(market['limits']['leverage']['max'])
                    print(max_leverage)
                    return ['{}x'.format(i) for i in [1, 3, 5, 10, 15, 20, 30, 40, 50, 60, 100, 150, 200] if
                            i <= max_leverage]
            # Testnet not supported for this exchange, return None
            return None
        else:
            # Load leverage information for the live exchange
            leverage_info = self.exchange_instance.futures_get_leverage_brackets(symbol)
            return [float(level['initialLeverage']) for level in leverage_info]

    def load_markets(self, reload=False, params=None):
        """Load all available markets for the exchange."""
        if params is None:
            params = {}
        if not Exchange.markets:
            try:
                print(self.urls)
                Exchange.markets = self.exchange_instance.load_markets()
            except ccxt.ExchangeError as e:
                raise ExchangeError(f"Error loading markets for {self.exchange_name}: {e}")

        return Exchange.markets

    def get_time_intervals(self, symbol):
        timeframes = None
        try:
            self.exchange_instance.load_markets()

            # timeframes = [tf for tf in self.exchange_instance.timeframes.keys() if market['quote'] in tf]
        except ccxt.ExchangeError as e:
            print(f"Error loading timeframes for {self.exchange_name}: {e}")
        return self.exchange_instance.timeframes.keys()

    def set_testnet(self):
        self.testnet = True
        return False

    def get_balance(self, currency):
        balance = self.exchange_instance.fetch_balance()[currency]
        return balance['free']

    # Fetch the account balance
    def fetch_balance(self, type='trading', currency=None):
        total_balance = super().fetch_total_balance()
        if currency in total_balance:
            return total_balance[currency]
        return None

    def get_total_balance(self):
        total_balance = float(self.exchange_instance.fetch_balance()['total']['USDT'])
        return total_balance

    def get_usdt_balance(self):
        usdt_balance = float(self.exchange_instance.fetch_balance()['free']['USDT'])
        return usdt_balance

    def get_ticker(self, symbol):
        try:
            return self.exchange_instance.fetch_ticker(symbol)
        except Exception as e:
            print(f"Error getting ticker for {symbol}: {e}")
            return None

    def get_ticker_price(self, symbol):
        ticker = self.exchange_instance.fetch_ticker(symbol)
        return ticker['last'] if ticker else None

    def create_limit_order(self, symbol, side, amount, price):
        order = None
        try:
            order = self.exchange_instance.create_order(symbol, 'limit', side, amount, price)
        except Exception as e:
            print(f"Failed to create limit order: {e}")
        return order

    def create_market_order(self, symbol, side, amount, params={}):
        order = None
        try:
            order = self.exchange_instance.create_order(symbol, 'market', side, amount)
        except Exception as e:
            print(f"Failed to create market order: {e}")
        return order

    def cancel_order(self, symbol, order_id):
        exchange_order = None
        try:
            exchange_order = self.exchange_instance.cancel_order(order_id, symbol=symbol)
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
            exchange_order = self.exchange_instance.fetch_order(order_id, symbol=symbol)
            status = exchange_order['status'] if exchange_order else None
        except Exception as e:
            print(f"Error getting order status on {self.exchange_name}: {e}")
        return status

    def create_order(self, side, order_type, symbol, amount, price=None):
        try:
            order_params = {'type': order_type, 'side': side, 'symbol': symbol, 'amount': amount}
            if price:
                order_params['price'] = price
            response = self.exchange_instance.create_order(**order_params)
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
            response = self.exchange_instance.create_order(**order_params)
            return response
        except Exception as e:
            print(f"Error placing {order_type} order on {self.exchange_name} testnet: {e}")
            return None

    def amount_to_precision(self, symbol, quantity, precision=None, rounding_mode=None):
        if symbol not in self.exchange_instance.markets:
            raise ValueError(f"{symbol} not found in markets dictionary. Please call load_markets() first.")
        if precision is None:
            precision = self.exchange_instance.markets[symbol]['precision']['amount']
        if rounding_mode is None:
            rounding_mode = decimal.ROUND_HALF_UP
        return Decimal(str(quantity)).quantize(Decimal(str(precision)), rounding=rounding_mode)
