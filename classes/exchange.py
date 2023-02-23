import ccxt
from ccxt import ExchangeError
import time

from flask import jsonify

from main import Accounts, Exchanges

class Exchange(ccxt.Exchange):

    def __init__(self, exchange_id, sandbox=False, database=None, account=None, config={}):

        self.sandbox = sandbox

        self.database = database
        self.account = account

        if self.database is not None and self.account is not None:
            account_details = self.database.session.query(Accounts).filter_by(id=account).join(Exchanges).filter_by(short=exchange_id).first()

            if account_details is None:
                raise ValueError(f"No account found for exchange {exchange_id} with ID {account}")

            self.apiKey = account_details.api_key
            self.secret = account_details.api_secret
            self.uid = account_details.uid

            if 'password' in account_details:
                self.password = account_details.password

        super().__init__({
            'id': exchange_id,
            'rateLimit': 250, # default: 2000, but some exchanges can't handle it
            'enableRateLimit': True,
            **config
        })

    def fetch_trades(self, symbol, since=None, limit=None, params={}):
        if self.sandbox:
            return []

        try:
            trades = self.exchange.fetch_trades(symbol, since, limit, params)
            return trades
        except ccxt.BaseError as e:
            raise ExchangeError(f"Failed to fetch trades: {str(e)}")

    def fetch_ohlcv(self, symbol, timeframe='1m', since=None, limit=None, params={}):
        if self.sandbox:
            return [
                [time.time() * 1000, 1, 1, 1, 1, 1],
                [time.time() * 1000, 1, 1, 1, 1, 1],
                [time.time() * 1000, 1, 1, 1, 1, 1],
                [time.time() * 1000, 1, 1, 1, 1, 1],
                [time.time() * 1000, 1, 1, 1, 1, 1],
            ]
        else:
            return super().fetch_ohlcv(symbol, timeframe, since, limit, params)

    def create_order(self, symbol, type, side, amount, price=None, params={}):
        if self.sandbox:
            return {
                'id': 'test-order-id',
                'clientOrderId': 'test-client-order-id',
                'timestamp': time.time() * 1000,
                'datetime': self.iso8601(time.time() * 1000),
                'lastTradeTimestamp': None,
                'status': 'open',
                'symbol': symbol,
                'type': type,
                'side': side,
                'price': price,
                'amount': amount,
                'filled': 0,
                'remaining': amount,
                'trades': None,
                'fee': None
            }
        else:
            return super().create_order(symbol, type, side, amount, price, params)

    def cancel_order(self, id, symbol=None, params={}):
        if self.sandbox:
            return {
                'id': id,
                'symbol': symbol,
                'clientOrderId': None,
                'timestamp': time.time() * 1000,
                'datetime': self.iso8601(time.time() * 1000),
                'lastTradeTimestamp': None,
                'status': 'canceled',
                'price': None,
                'amount': None,
                'average': None,
                'filled': None,
                'remaining': None,
                'cost': None,
                'trades': None
            }

        if not self.bot or not self.bot.enabled:
            return jsonify({
                'status': 'error',
                'message': f"Unable to cancel order {id}. Bot is disabled or doesn't exist."
            })

        account = self.bot.accounts[0]  # we assume only one account for now
        exchange = self.get_exchange(account.exchange)

        try:
            order = exchange.cancel_order(id, symbol, params)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f"Unable to cancel order {id}: {str(e)}"
            })

        balance = exchange.fetch_balance()

        return jsonify({
            'status': 'success',
            'order': order,
            'cost': order['cost'],
            'remaining_balance': balance['free']['USDT'],
            'message': f"Order {id} on {account.exchange.name} cancelled successfully."
        })

    def load_exchange(self):
        if self.is_sandbox:
            if self.exchange_id == 'binance':
                self.exchange = ccxt.binance({
                    'apiKey': 'your_sandbox_api_key',
                    'secret': 'your_sandbox_api_secret',
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future'
                    },
                    'urls': {
                        'api': 'https://testnet.binancefuture.com',
                        'test': 'https://testnet.binancefuture.com'
                    }
                })
            elif self.exchange_id == 'kucoin':
                self.exchange = ccxt.kucoin({
                    'apiKey': 'your_sandbox_api_key',
                    'secret': 'your_sandbox_api_secret',
                    'password': 'your_sandbox_password',
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future'
                    },
                    'urls': {
                        'api': 'https://api-sandbox-futures.kucoin.com',
                        'test': 'https://api-sandbox-futures.kucoin.com'
                    }
                })
            elif self.exchange_id == 'bitmex':
                self.exchange = ccxt.bitmex({
                    'apiKey': 'your_sandbox_api_key',
                    'secret': 'your_sandbox_api_secret',
                    'enableRateLimit': True,
                    'urls': {
                        'api': 'https://testnet.bitmex.com',
                        'test': 'https://testnet.bitmex.com'
                    }
                })
            elif self.exchange_id == 'bybit':
                self.exchange = ccxt.bybit({
                    'apiKey': 'your_sandbox_api_key',
                    'secret': 'your_sandbox_api_secret',
                    'enableRateLimit': True,
                    'urls': {
                        'api': 'https://api-testnet.bybit.com',
                        'test': 'https://api-testnet.bybit.com'
                    }
                })
            elif self.exchange_id == 'coinbasepro':
                self.exchange = ccxt.coinbasepro({
                    'apiKey': 'your_sandbox_api_key',
                    'secret': 'your_sandbox_api_secret',
                    'password': 'your_sandbox_password',
                    'enableRateLimit': True,
                    'urls': {
                        'api': 'https://api-public.sandbox.pro.coinbase.com',
                        'test': 'https://api-public.sandbox.pro.coinbase.com'
                    }
                })
        else:
            if self.exchange_id == 'binance':
                self.exchange = ccxt.binance({
                    'apiKey': 'your_api_key',
                    'secret': 'your_api_secret',
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future'
                    }
                })
            elif self.exchange_id == 'kucoin':
                self.exchange = ccxt.kucoin({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'password': self.password})

            # set the commission rate for the exchange
            if self.exchange_id == 'binance':
                self.commission_rate = 0.1  # 0.1% or 0.001
            elif self.exchange_id == 'kucoin':
                self.commission_rate = 0.1  # 0.1% or 0.001
            else:
                # default commission rate of 0.25%
                self.commission_rate = 0.25  # 0.25% or 0.0025

    def fetch_balance(self):
        """
        Fetch the current balance for the account.
        """
        # make the API request
        balance = self.exchange.fetch_balance()

        # extract the available balances for each asset
        available_balances = {asset: balance['free'][asset] for asset in self.assets}

        # return the available balances
        return available_balances

    def fetch_ticker(self):
        """
        Fetch the current ticker price for the symbol.
        """
        # make the API request
        ticker = self.exchange.fetch_ticker(self.symbol)

        # extract the bid and ask prices
        bid_price = ticker['bid']
        ask_price = ticker['ask']

        # return the bid and ask prices
        return bid_price, ask_price

    def place_order(self, order_type, price, amount):
        """
        Place an order for the symbol at the given price and amount.
        """
        # calculate the order parameters based on the order type
        if order_type == 'buy':
            side = 'buy'
            cost = price * amount
        elif order_type == 'sell':
            side = 'sell'
            cost = None

        # adjust the amount to account for minimum trade size
        amount = self.adjust_amount(amount)

        # make the API request to place the order
        order = self.exchange.create_order(self.symbol, type='limit', side=side, price=price, amount=amount)

        # return the order details
        return order

    def adjust_amount(self, amount):
        """
        Adjust the amount to account for minimum trade size requirements.
        """
        # get the minimum trade size for the symbol
        minimum_trade_size = self.get_minimum_trade_size()

        # round the amount to the nearest valid trade size
        amount = round(amount / minimum_trade_size) * minimum_trade_size

        # return the adjusted amount
        return amount

    def get_minimum_trade_size(self):
        """
        Get the minimum trade size for the symbol.
        """
        # make the API request to get the symbol info
        symbol_info = self.exchange.load_markets()[self.symbol]

        # extract the minimum trade size
        minimum_trade_size = symbol_info['limits']['amount']['min']

        # return the minimum trade size
        return minimum_trade_size

    def get_account_balance(self, symbol):
        balance = self.exchange.fetch_balance()
        return balance['free'][symbol]

    def get_ticker_price(self, symbol):
        ticker = self.exchange.fetch_ticker(symbol)
        return ticker['last']

    def get_order_book(self, symbol, limit=100):
        order_book = self.exchange.fetch_order_book(symbol, limit=limit)
        return order_book

    def get_recent_trades(self, symbol, limit=100):
        trades = self.exchange.fetch_trades(symbol, limit=limit)
        return trades

    def get_ohlcv_data(self, symbol, timeframe='1m', limit=100):
        ohlcv_data = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return ohlcv_data
