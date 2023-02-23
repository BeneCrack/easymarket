from datetime import datetime
import ccxt
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

    def get_open_positions(self, symbol):
        positions = []
        try:
            orders = self.exchange_class.fetch_open_orders(symbol)
            for order in orders:
                if order['type'] == 'limit':
                    continue
                position = {
                    'order_id': order['id'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'amount': order['remaining'],
                    'entry_price': order['price'],
                    'leverage': None,
                    'margin_type': None,
                    'isolated': None,
                    'stop_loss': None,
                    'take_profit': None,
                    'liquidation_price': None,
                }
                positions.append(position)
        except Exception as e:
            print(f"Failed to get open positions: {e}")
        return positions

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

    def create_limit_order(self, symbol, side, amount, price):
        order = None
        try:
            exchange_order = self.exchange.create_order(symbol, type='limit', side=side, amount=amount, price=price)
            order = Positions(exchange=self.name, order_id=exchange_order['id'], symbol=symbol, side=side,
                          amount=amount,
                          price=price, status=exchange_order['status'], type='limit')
            self.session.add(order)
            self.session.commit()
        except Exception as e:
            print(f"Error creating limit order on {self.name}: {e}")
        return order

    def create_market_order(self, symbol, side, amount):
        order = None
        try:
            exchange_order = self.exchange.create_order(symbol, type='market', side=side, amount=amount)
            order = Positions(exchange=self.name, order_id=exchange_order['id'], symbol=symbol, side=side,
                          amount=amount,
                          price=exchange_order['price'], status=exchange_order['status'], type='market')
            self.session.add(order)
            self.session.commit()
        except Exception as e:
            print(f"Error creating market order on {self.name}: {e}")
        return order

    def cancel_order(self, symbol, order_id):
        order = None
        try:
            exchange_order = self.exchange.cancel_order(order_id, symbol=symbol)
            if exchange_order:
                order = self.session.query(Positions).filter_by(exchange=self.name,
                                                            order_id=exchange_order['id']).first()
                if order:
                    order.status = exchange_order['status']
                    self.session.commit()
        except Exception as e:
            print(f"Error cancelling order on {self.name}: {e}")
        return order

    def get_order_status(self, symbol, order_id):
        status = None
        try:
            exchange_order = self.exchange.fetch_order(order_id, symbol=symbol)
            status = exchange_order['status'] if exchange_order else None
        except Exception as e:
            print(f"Error getting order status on {self.name}: {e}")
        return status

    def create_order(self, side, order_type, symbol, amount, price=None):
        try:
            order_params = {'type': order_type, 'side': side, 'symbol': symbol, 'amount': amount}
            if price:
                order_params['price'] = price
            response = self.exchange_client.create_order(**order_params)
            return response
        except Exception as e:
            print(f"Error placing {order_type} order on {self.exchange_id}: {e}")
            return None

    def create_testnet_order(self, side, order_type, symbol, amount, price=None):
        if not self.testnet:
            print("Error: create_testnet_order can only be used with testnet exchanges.")
            return None
        try:
            order_params = {'type': order_type, 'side': side, 'symbol': symbol, 'amount': amount}
            if price:
                order_params['price'] = price
            response = self.exchange_client.create_order(**order_params)
            return response
        except Exception as e:
            print(f"Error placing {order_type} order on {self.exchange_id} testnet: {e}")
            return None

    def get_position(self, bot_id):
        position = Positions.query.filter_by(bot_id=bot_id).first()
        if position:
            return position.to_dict()
        else:
            return None

    def update_position(self, bot_id, side, amount, price=None):
        position = Positions.query.filter_by(bot_id=bot_id).first()
        if not position:
            position = Positions(bot_id=bot_id, side=side, amount=amount, price=price)
            self.session.add(position)
        else:
            position.side = side
            position.amount = amount
            position.price = price
        self.session.commit()
        # Update the position in the database
        if position.id:
            self.session.add(position)
        else:
            self.session.commit()
            return True
        return False