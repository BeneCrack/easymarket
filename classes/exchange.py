from datetime import datetime
import ccxt
from ccxt import ExchangeError
from sqlalchemy.orm import sessionmaker

from models import Positions


class Exchange:
    def __init__(self, exchange_name, api_key=None, secret=None, passphrase=None, testnet=False, defaultType=None):
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        self.testnet = testnet
        self.defaultType = defaultType
        self.exchange_class = self.get_exchange_class()
        self.session = sessionmaker(bind=engine)()

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

    def load_markets(self):
        """Load all available markets for the exchange."""
        try:
            self.exchange_class.load_markets()
            return self.exchange_class.markets
        except ccxt.ExchangeError as e:
            raise ExchangeError(f"Error loading markets for {self.exchange_name}: {e}")

    def set_testnet(self):
        self.testnet = True
        return False

    def get_balance(self, currency):
        balance = self.exchange_class.fetch_balance()[currency]
        return balance['free']

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

    def close_position(self, symbol, position_id):
        order = None
        position = None
        for open_position in self.get_open_positions(symbol):
            if open_position['order_id'] == position_id:
                position = open_position
                break
        if position:
            side = 'sell' if position['side'] == 'buy' else 'buy'
            order = self.create_market_order(symbol, side, abs(position['amount']))
            if order and order['status'] == 'closed':
                position['is_open'] = False
                position['close_order_id'] = order['id']
                position['close_price'] = order['price']
                position['close_time'] = datetime.now()
                self.session.commit()
                return True
        return False

    def cancel_order(self, symbol, order_id):
        order = None
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