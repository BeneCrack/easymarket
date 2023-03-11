import time

import ccxt
from _decimal import Decimal
from ccxt import ExchangeError
import decimal


class Exchange(ccxt.Exchange):
    markets = {}

    def __init__(self, exchange_name, api_key=None, secret=None, passphrase=None, testnet=False, defaultType=None):
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        self.testnet = testnet
        self.defaultType = defaultType
        self.urls = None
        self.exchange_class = self.get_exchange_class()

    def get_exchange_class(self):
        exchange = self.exchange_name
        exchange_options = self.build_exchange_options()

        print(exchange_options)
        # Determine the exchange class
        if exchange == 'binance':
            exchange_class = ccxt.binance(exchange_options)
        elif exchange == 'binanceusdm':
            exchange_class = ccxt.binanceusdm(exchange_options)
        elif exchange == 'kucoin':
            exchange_class = ccxt.kucoin(exchange_options)
        elif exchange == 'kucoinfutures':
            exchange_class = ccxt.kucoinfutures(exchange_options)
        elif exchange == 'bybit':
            exchange_class = ccxt.bybit(exchange_options)
        elif exchange == 'coinbasepro':
            exchange_class = ccxt.coinbasepro(exchange_options)
        elif exchange == 'bitfinex':
            exchange_class = ccxt.bitfinex(exchange_options)
        elif exchange == 'bitmex':
            exchange_class = ccxt.bitmex(exchange_options)
        elif exchange == 'bittrex':
            exchange_class = ccxt.bittrex(exchange_options)
        elif exchange == 'cex':
            exchange_class = ccxt.cex(exchange_options)
        elif exchange == 'deribit':
            exchange_class = ccxt.deribit(exchange_options)
        elif exchange == 'gateio':
            exchange_class = ccxt.gateio(exchange_options)
        elif exchange == 'gemini':
            exchange_class = ccxt.gemini(exchange_options)
        elif exchange == 'huobifutures':
            exchange_class = ccxt.huobifutures(exchange_options)
        elif exchange == 'huobi':
            exchange_class = ccxt.huobipro(exchange_options)
        elif exchange == 'kraken':
            exchange_class = ccxt.kraken(exchange_options)
        elif exchange == 'krakenfutures':
            exchange_class = ccxt.krakenfutures(exchange_options)
        elif exchange == 'phemex':
            exchange_class = ccxt.phemex(exchange_options)
        elif exchange == 'bitflyer':
            exchange_class = ccxt.bitflyer(exchange_options)
        elif exchange == 'binancecoinm':
            exchange_class = ccxt.binancecoinm(exchange_options)
        elif exchange == 'bitdotcom':
            exchange_class = ccxt.bitdotcom(exchange_options)
        elif exchange == 'bitbay':
            exchange_class = ccxt.bitbay(exchange_options)
        elif exchange == 'bitmart':
            exchange_class = ccxt.bitmart(exchange_options)
        else:
            exchange_class = ccxt.kucoinfutures(exchange_options)

        self.urls = exchange_class.urls
        print(self.api_key)
        self.set_sandbox_mode(self.testnet)
        print(self.urls)
        exchange_class.load_markets()

        return exchange_class

    def build_exchange_options(self):
        api_key = self.api_key
        api_secret = self.secret
        password = self.passphrase

        """
        if exchange == 'binance':
            if testnet:
                urls = {
                    'api': 'https://testnet.binance.vision/api',
                    'public': 'https://testnet.binance.vision/api/v3',
                }
            else:
                urls = {
                    'api': 'https://api.binance.com/api',
                    'public': 'https://api.binance.com/api/v3',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls}
            }
        elif exchange == 'binanceusdm':
            if testnet:
                urls = {
                    'api': 'https://testnet.binancefuture.com',
                    'public': 'https://testnet.binancefuture.com/fapi/v1',
                }
            else:
                urls = {
                    'api': 'https://fapi.binance.com',
                    'public': 'https://fapi.binance.com/fapi/v1',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls}
            }
        elif exchange == 'binancecoinm':
            if testnet:
                raise ValueError("Binance COIN-M Futures does not support testnet.")
            else:
                urls = {
                    'api': 'https://dapi.binance.com',
                    'public': 'https://dapi.binance.com/dapi/v1',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
            }
        elif exchange == 'kucoin':
            if testnet:
                urls = {
                    'api': 'https://api-sandbox.kucoin.com',
                    'public': 'https://api-sandbox.kucoin.com/api',
                }
            else:
                urls = {
                    'api': 'https://api.kucoin.com',
                    'public': 'https://api.kucoin.com/api',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'password': password,
                'options': {'urls': urls}
            }
        elif exchange == 'kucoinfutures':
            urls = {
                'logo': 'https://user-images.githubusercontent.com/1294454/147508995-9e35030a-d046-43a1-a006-6fabd981b554.jpg',
                'doc': [
                    'https://docs.kucoin.com/futures',
                    'https://docs.kucoin.com',
                ],
                'www': 'https://futures.kucoin.com/',
                'referral': 'https://futures.kucoin.com/?rcode=E5wkqe',
                'api': {
                    'public': 'https://openapi-v2.kucoin.com',
                    'private': 'https://openapi-v2.kucoin.com',
                    'futuresPrivate': 'https://api-futures.kucoin.com',
                    'futuresPublic': 'https://api-futures.kucoin.com',
                    'webFront': 'https://futures.kucoin.com/_api/web-front',
                },
                'test': {
                    'public': 'https://openapi-sandbox.kucoin.com',
                    'private': 'https://openapi-sandbox.kucoin.com',
                    'futuresPrivate': 'https://api-sandbox-futures.kucoin.com',
                    'futuresPublic': 'https://api-sandbox-futures.kucoin.com',
                },
            }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'password': password,
                'options': {'urls': urls}
            }
        elif exchange == 'bybit':
            if testnet:
                urls = {
                    'api': 'https://api-testnet.bybit.com',
                    'public': 'https://api-testnet.bybit.com',
                }
            else:
                urls = {
                    'api': 'https://api.bybit.com',
                    'public': 'https://api.bybit.com',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls}
            }
        elif exchange == 'coinbasepro':
            if testnet:
                urls = {
                    'api': 'https://api-public.sandbox.pro.coinbase.com',
                    'public': 'https://api-public.sandbox.pro.coinbase.com',
                }
            else:
                urls = {
                    'api': 'https://api.pro.coinbase.com',
                    'public': 'https://api.pro.coinbase.com',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'passphrase': password,
                'enableRateLimit': True,
                'options': {
                    'urls': urls,
                    'timeDifference': 0,
                },
            }
        elif exchange == 'bitfinex':
            if testnet:
                raise ValueError("Bitfinex does not support testnet.")
            else:
                urls = {
                    'api': 'https://api.bitfinex.com',
                    'public': 'https://api-pub.bitfinex.com/v2',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls}
            }
        elif exchange == 'bitmex':
            if testnet:
                urls = {
                    'api': 'https://testnet.bitmex.com',
                    'public': 'https://testnet.bitmex.com/api/v1',
                }
            else:
                urls = {
                    'api': 'https://www.bitmex.com',
                    'public': 'https://www.bitmex.com/api/v1',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
                'rateLimit': 3000,
            }
        elif exchange == 'bittrex':
            if testnet:
                raise ValueError("Bittrex does not support testnet.")
            else:
                urls = {
                    'api': 'https://api.bittrex.com/v3',
                    'public': 'https://api.bittrex.com/v3',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
            }
        elif exchange == 'kraken':
            if testnet:
                raise ValueError("Kraken does not support testnet.")
            else:
                urls = {
                    'api': 'https://api.kraken.com/0',
                    'public': 'https://api.kraken.com/0/public',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'nonce': lambda: str(int(time.time() * 1000)),
                'options': {'urls': urls},
            }
        elif exchange == 'krakenfutures':
            if testnet:
                urls = {
                    'api': 'https://demo-futures.kraken.com',
                    'public': 'https://demo-futures.kraken.com/derivatives/api/v3',
                }
            else:
                urls = {
                    'api': 'https://futures.kraken.com',
                    'public': 'https://futures.kraken.com/derivatives/api/v3',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'nonce': lambda: str(int(time.time() * 1000)),
                'options': {'urls': urls},
            }
        elif exchange == 'okex':
            if testnet:
                urls = {
                    'api': 'https://www.okex.com',
                    'public': 'https://www.okex.com/api/v5',
                }
            else:
                urls = {
                    'api': 'https://www.okex.com',
                    'public': 'https://www.okex.com/api/v5',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'password': password,
                'options': {'urls': urls},
            }
        elif exchange == 'cex':
            if testnet:
                urls = {
                    'api': 'https://testnet.cex.io',
                    'public': 'https://testnet.cex.io',
                }
            else:
                urls = {
                    'api': 'https://cex.io',
                    'public': 'https://cex.io',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'password': password,
                'enableRateLimit': True,
                'options': {'urls': urls},
            }
        elif exchange == 'poloniex':
            if testnet:
                urls = {
                    'api': 'https://testnet.poloniex.com',
                    'public': 'https://testnet.poloniex.com/public',
                }
            else:
                urls = {
                    'api': 'https://poloniex.com',
                    'public': 'https://poloniex.com/public',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
            }
        elif exchange == 'bitstamp':
            if testnet:
                urls = {
                    'api': 'https://www.bitstamp.net/api/v2',
                    'public': 'https://www.bitstamp.net/api/v2',
                }
            else:
                urls = {
                    'api': 'https://www.bitstamp.net/api/v2',
                    'public': 'https://www.bitstamp.net/api/v2',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {'urls': urls}
            }
        elif exchange == 'phemex':
            if testnet:
                urls = {
                    'api': 'https://testnet-api.phemex.com',
                    'public': 'https://testnet-api.phemex.com',
                }
            else:
                urls = {
                    'api': 'https://api.phemex.com',
                    'public': 'https://api.phemex.com',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
            }
        elif exchange == 'phemexfutures':
            if testnet:
                urls = {
                    'api': 'https://testnet-api.phemex.com',
                    'public': 'https://testnet-api.phemex.com',
                }
            else:
                urls = {
                    'api': 'https://api.phemex.com',
                    'public': 'https://api.phemex.com',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
            }
        elif exchange == 'bitflyer':
            if testnet:
                raise ValueError("bitFlyer does not support testnet.")
            else:
                urls = {
                    'api': 'https://api.bitflyer.com/v1',
                    'public': 'https://api.bitflyer.com',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
            }
        elif exchange == 'gateio':
            if testnet:
                raise ValueError("Gate.io does not support testnet.")
            else:
                urls = {
                    'api': 'https://api.gateio.ws',
                    'public': 'https://api.gateio.ws/api/v4',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'password': password,
                'options': {'urls': urls},
            }
        elif exchange == 'bitmax':
            if testnet:
                urls = {
                    'api': 'https://demo-api.bitmaxpro.com',
                    'public': 'https://demo-api.bitmaxpro.com',
                }
            else:
                urls = {
                    'api': 'https://bitmax.io',
                    'public': 'https://bitmax.io',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'password': password,
                'options': {'urls': urls},
            }
        elif exchange == 'huobi':
            if testnet:
                raise ValueError("Huobi does not support testnet.")
            else:
                urls = {
                    'api': 'https://api.huobi.pro',
                    'public': 'https://api.huobi.pro',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
            }
        elif exchange == 'huobifutures':
            if testnet:
                raise ValueError("Huobi Futures does not support testnet.")
            else:
                urls = {
                    'api': 'https://api.hbdm.com',
                    'public': 'https://api.hbdm.com',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
            }
        elif exchange == 'deribit':
            if testnet:
                urls = {
                    'api': 'https://test.deribit.com/api/v2',
                    'public': 'https://test.deribit.com/api/v2',
                }
            else:
                urls = {
                    'api': 'https://www.deribit.com/api/v2',
                    'public': 'https://www.deribit.com/api/v2',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
            }
        elif exchange == 'bitdotcom':
            if testnet:
                urls = {
                    'api': 'https://testnet.bit.com',
                    'public': 'https://testnet.bit.com',
                }
            else:
                urls = {
                    'api': 'https://bit.com',
                    'public': 'https://bit.com',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'password': password,
                'options': {'urls': urls},
            }
        elif exchange == 'deribit':
            if testnet:
                urls = {
                    'api': 'https://test.deribit.com/api/v2',
                    'public': 'https://test.deribit.com/api/v2',
                }
            else:
                urls = {
                    'api': 'https://www.deribit.com/api/v2',
                    'public': 'https://www.deribit.com/api/v2',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {'urls': urls},
            }
        elif exchange == 'huobi':
            if testnet:
                urls = {
                    'api': 'https://api.testnet.huobi.pro',
                    'public': 'https://api.testnet.huobi.pro/v1',
                }
            else:
                urls = {
                    'api': 'https://api.huobi.pro',
                    'public': 'https://api.huobi.pro/v1',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
            }
        elif exchange == 'huobifutures':
            if testnet:
                urls = {
                    'api': 'https://api.dm.testnet.huobi.pro',
                    'public': 'https://api.dm.testnet.huobi.pro',
                }
            else:
                urls = {
                    'api': 'https://api.hbdm.com',
                    'public': 'https://api.hbdm.com',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'password': password,
                'options': {'urls': urls},
            }
        elif exchange == 'bitmax':
            if testnet:
                urls = {
                    'api': 'https://bitmax-test.io',
                    'public': 'https://bitmax-test.io/api/v1',
                }
            else:
                urls = {
                    'api': 'https://bitmax.io',
                    'public': 'https://bitmax.io/api/v1',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
            }
        elif exchange == 'gemini':
            if testnet:
                raise ValueError("Gemini does not support testnet.")
            else:
                urls = {
                    'api': 'https://api.gemini.com',
                    'public': 'https://api.gemini.com/v1',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'nonce': lambda: str(int(time.time() * 1000)),
                'options': {'urls': urls},
            }
        elif exchange == 'bitmart':
            if testnet:
                raise ValueError("BitMart does not support testnet.")
            else:
                urls = {
                    'api': 'https://api-cloud.bitmart.com',
                    'public': 'https://api-cloud.bitmart.com',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'urls': urls},
            }
        elif exchange == 'bitbay':
            if testnet:
                raise ValueError("BitBay does not support testnet.")
            else:
                urls = {
                    'api': 'https://api.bitbay.net/rest',
                    'public': 'https://api.bitbay.net/rest',
                }
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'password': password,
                'options': {'urls': urls},
            }
            """
        exchange_options = {
            'apiKey': api_key,
            'secret': api_secret,
            'password': password,
            'enableRateLimit': True,
            'options': {'adjustForTimeDifference': True},
        }
        return exchange_options

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
        print("we here2")
        if self.testnet:
            if hasattr(self.exchange_class, 'fetch_markets'):
                # Load markets information for the testnet exchange
                markets = self.exchange_class.fetch_markets()
                market = next((m for m in markets if m['symbol'] == symbol), None)
                if market:
                    print(market)
                    print("market")
                    max_leverage = int(market['limits']['leverage']['max'])
                    print(max_leverage)
                    return ['{}x'.format(i) for i in [1, 3, 5, 10, 15, 20, 30, 40, 50, 60, 100, 150, 200] if i <= max_leverage]
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

    def get_time_intervals(self, symbol):
        timeframes = None
        try:
            self.exchange_class.load_markets()

            #timeframes = [tf for tf in self.exchange_class.timeframes.keys() if market['quote'] in tf]
        except ccxt.ExchangeError as e:
            print(f"Error loading timeframes for {self.exchange_name}: {e}")
        return self.exchange_class.timeframes.keys()

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
