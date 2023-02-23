import ccxt
from flask import Markup, flash, request, Flask, render_template, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required
from flask_sqlalchemy import SQLAlchemy
from pprint import pprint
from classes.exchange import Exchange
from classes.models import ExchangeModel, Bots, Accounts, Signals, Positions, Role, User

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///easymarket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'super-secret-key'

# create database and data models
db = SQLAlchemy(app)

# --------- setup Flask-Security ---------
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)
# --------- setup Flask-Login ---------
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------- Reset DB ---------
@app.route('/reset-database')
@login_required
def reset_database():
    db.drop_all()
    db.create_all()
    return 'Database reset!'


#################################################################################
########################## USER-MANAGEMENT ROUTES ###############################
#################################################################################


@app.route('/users')
def users():
    all_users = User.query.all()
    return render_template('users.html', users=all_users)


@app.route('/')
@login_required
def home():
    return render_template('home.html')


@app.route('/login2', methods=['GET', 'POST'])
def login():
    print('Reached the login function')
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        print(f"email: {email}, password: {password}")
        if user is not None and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    print('Reached the register function')
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User(email=email, active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


#################################################################################
########################## BOT AND ACCOUNT ROUTES ###############################
#################################################################################


@app.route('/bots')
@login_required
def bots():
    bots = db.session.query(Bots, Accounts.name).join(Accounts, Bots.account_id == Accounts.id).all()
    return render_template('bots.html', bots=bots)


@app.route('/create/bot', methods=['GET', 'POST'])
@login_required
def create_bot():
    if request.method == 'POST':
        name = request.form['name']
        enabled = bool(request.form.get("enabled"))
        pair = request.form["pair"]
        amount = request.form["amount"]
        description = request.form['description']
        time_interval = request.form['time_interval']   #       ADD THIS TO GTML
        account_id = request.form['account']
        bt_type = request.form["type"]
        user_id = current_user.id

        # retrieve the Account object associated with the given account_id
        account = Accounts.query.filter_by(id=account_id).first()
        # retrieve the ExchangeModel id associated with the Account object
        exchange_id = account.exchange.id

        bot = Bots(name=name, enabled=enabled, description=description, time_interval=time_interval, exchange_id=exchange_id, pair=pair, type=bt_type, amount=amount, user_id=user_id, account_id=account_id)
        db.session.add(bot)
        db.session.commit()

        flash('Bot created successfully!')
        return redirect(url_for('bots'))
    else:
        accounts = Accounts.query.filter_by(user_id=current_user.id).all()
        return render_template('create_bot.html', accounts=accounts)


@app.route('/edit/bot/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_bot(id):
    bot = Bots.query.get_or_404(id)
    if request.method == 'POST':
        bot.name = request.form['name']
        bot.enabled = bool(request.form.get("enabled"))
        bot.pair = request.form["pair"]
        bot.amount = request.form["amount"]
        bot.description = request.form['description']
        bot.time_interval = request.form['time_interval']  # ADD THIS TO GTML
        bot.account_id = request.form['account']
        bot.type = request.form["type"]
        bot.user_id = current_user.id

        db.session.commit()

        flash('Bot updated successfully!')
        return redirect(url_for('bots'))
    else:
        accounts = Accounts.query.filter_by(user_id=current_user.id).all()
        bot = db.session.query(Bots, Accounts.name).join(Accounts, Bots.account_id == Accounts.id).get(id)
        return render_template('edit_bot.html', bot=bot, accounts=accounts)


@app.route('/delete/bot/<int:id>', methods=['POST'])
@login_required
def delete_bot(id):
    bot = Bots.query.get_or_404(id)
    db.session.delete(bot)
    db.session.commit()

    flash('Bot deleted successfully!')
    return redirect(url_for('bots'))


@app.route('/accounts')
@login_required
def accounts():
    accounts = db.session.query(Accounts, ExchangeModel.name).join(ExchangeModel, Accounts.exchange_id == ExchangeModel.id).all()
    return render_template('accounts.html', title="Easymarket - Connected Accounts Overview", accounts=accounts)


@app.route('/add/account', methods=['GET', 'POST'])
@login_required
def add_account():
    if request.method == 'POST':
        name = request.form['name']
        exchange_id = request.form['exchange_id']
        api_key = request.form['api_key']
        api_secret = request.form['api_secret']
        password = request.form['password']
        options = request.form['options']

        account = Accounts(name=name, exchange_id=exchange_id, api_key=api_key, api_secret=api_secret, password=password, options=options)
        db.session.add(account)
        db.session.commit()

        flash('Account created successfully!')
        return redirect(url_for('accounts'))
    else:
        exchanges = ExchangeModel.query.all()
        return render_template('add_account.html', exchanges=exchanges)


@app.route('/edit/account/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_account(id):
    account = Accounts.query.get_or_404(id)
    if request.method == 'POST':
        account.name = request.form['name']
        account.exchange_id = request.form['exchange']
        account.api_key = request.form['api_key']
        account.api_secret = request.form["api_secret"]
        account.password = request.form["password"]
        account.options = request.form["options"]

        db.session.commit()

        flash('Account updated successfully!', 'success')
        return redirect(url_for('accounts'))

    return render_template('edit_account.html',  account=account, exchanges=ExchangeModel.query.all())


@app.route('/delete/account/<int:id>', methods=['POST'])
@login_required
def delete_account(id):
    account = Accounts.query.get_or_404(id)

    db.session.delete(account)
    db.session.commit()

    flash('Account deleted successfully!', 'success')
    return redirect(url_for('accounts'))


@app.route("/addexchange")
@login_required
def addexchange():
    #new_exchange = Exchanges(name="Kucoin Futures Sandbox", short="kucoinfuturesusd")
    #db.session.add(new_exchange)
    #db.session.commit()
    all_exchanges = ExchangeModel.query.all()
    return render_template("exchanges.html", exchanges=all_exchanges)


@app.route("/trades")
@login_required
def trades():
    return render_template("trades.html")

@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


#################################################################################
############################# TEMPLATE FILTERS ##################################
#################################################################################


@app.template_filter('enabled_status')
def enabled_status_filter(value):
    if value:
        return Markup('<span class="active">ACTIVE</span>')
    else:
        return Markup('<span class="inactive">INACTIVE</span>')


@app.route('/load/pairs/<int:account_id>')
def load_pairs(account_id):
    # Get the exchange associated with the selected account
    account = Accounts.query.filter_by(id=account_id).first()
    exchange = ExchangeModel.query.filter_by(id=account.exchange_id).first()

    if exchange is not None:
        print(f"Exchange short name for account {exchange.short}")
        exchange_class = getattr(ccxt, exchange.short.lower())
        if exchange.short.lower() == "kucoinfuturesusd":
            exchange = exchange_class({
                'rateLimit': 2000,  # Optional, but recommended
                'enableRateLimit': True,  # Optional, but recommended
                'urls': {
                    'api': {
                        'public': 'https://api-sandbox-futures.kucoin.com',
                        'private': 'https://api-sandbox-futures.kucoin.com',
                    }
                }
            })
        else:
            exchange = exchange_class()
        try:
            markets = exchange.load_markets()
        except Exception as e:
            return f'Error loading markets: {e}'

        # Extract the market symbols and sort them alphabetically
        pairs = sorted(list(markets.keys()))
        pair_names = [pair.split(':')[0] for pair in pairs]

        # Return the available pairs as a JSON response
        return jsonify(pair_names)
    else:
        print(f"No account found with id {account_id}")


def convert_to_usdt(exchange, symbol, amount):
    ticker = exchange.fetch_ticker(symbol)
    price = ticker['last']
    usdt_ticker = exchange.fetch_ticker('USDT/USDT')
    usdt_price = usdt_ticker['last']
    value = price * amount
    if symbol != 'USDT':
        value = value / usdt_price
    return value


@app.route('/reload/account', methods=['POST'])
def reload_account():
    data = request.get_json()
    account_id = data['account_id']
    account = Accounts.query.filter_by(id=account_id).first()
    exchangemodel = ExchangeModel.query.filter_by(id=account.exchange_id).first()

    # Instantiate the exchange API class with the account's API key and secret
    exchange_class = getattr(ccxt, exchangemodel.short.lower())({
        'apiKey': account.api_key,
        'secret': account.api_secret,
        'password': account.password,
    })

    # Fetch the balance for the account

    balance = exchangemodel.fetch_balance()
    usdt_balance = balance['USDT']['total']
    print(usdt_balance)
    #balance = exchange_class.fetch_balance()[account.name]
    #total_balance = balance['total']

    # Convert the total balance to USDT
    #usdt_balance = convert_to_usdt(total_balance, balance['currency'], exchange_class)

    return jsonify({'total_balance': usdt_balance})


#################################################################################
########################### TRADINGVIEW WEBHOOK #################################
#################################################################################


@app.route('/webhooks/tradingview', methods=['POST'])
def tradingview_webhook():
    # Parse the TradingView signal
    # Signal EXAMPLE = "ENTER-LONG_KUCOIN_BTC-USDT_BOTNAME1_1H_744bde7b7594b117"
    signal = request.form['message']
    signal_parts = signal.split('_')
    if len(signal_parts) < 4:
        return 'Invalid signal format', 400
    signal_type = signal_parts[0]
    exchange_name = signal_parts[1].lower()
    bot_name = signal_parts[2]
    timeframe = signal_parts[3]

    # Determine exchange
    exchanges = {
        'binance': ccxt.binance,
        'binancefutures': ccxt.binance,
        'kucoin': ccxt.kucoin,
        'kucoinfutures': ccxt.kucoin,
        'bybit': ccxt.bybit,
        'bitmex': ccxt.bitmex,
        'coinbase': ccxt.coinbasepro,
        'coinbasepro': ccxt.coinbasepro,
        'ftx': ccxt.ftx,
        'ftxus': ccxt.ftx,
        'deribit': ccxt.deribit
    }
    if exchange_name not in exchanges:
        return 'Unsupported exchange', 400
    exchange = exchanges[exchange_name]({'enableRateLimit': True})

    # Check if bot exists and is enabled
    bot = Bots.query.filter_by(name=bot_name, exchange=exchange_name, enabled=True).first()
    if not bot:
        app.logger.error(f"Bot '{bot_name}' not found or is disabled.")
        return "Bot not found or disabled.", 404

    # Set API keys and symbol
    exchange.apiKey = bot.api_key
    exchange.secret = bot.secret_key
    symbol = bot.symbol

    # Determine order side and type
    if signal_type == 'ENTER-LONG':
        side = 'buy'
        order_type = 'limit'
    elif signal_type == 'ENTER-SHORT':
        side = 'sell'
        order_type = 'limit'
    elif signal_type == 'EXIT-LONG':
        side = 'sell'
        order_type = 'market'
    elif signal_type == 'EXIT-SHORT':
        side = 'buy'
        order_type = 'market'
    else:
        return 'Invalid signal type', 400

    # Determine time interval from signal timeframe
    interval_map = {
        '1m': '1m',
        '5m': '5m',
        '15m': '15m',
        '30m': '30m',
        '1h': '1h',
        '2h': '2h',
        '3h': '3h',
        '4h': '4h',
        '6h': '6h',
        '12h': '12h',
        '1d': '1d',
        '1w': '1w',
        '1M': '1M'
    }
    time_frame = signal_parts[3]
    interval = interval_map.get(time_frame)

    if not interval:
        app.logger.error(f"Invalid signal timeframe: {time_frame}")
        return "Invalid signal timeframe.", 400

    app.logger.info(f"Received signal: {signal}")

    # Check if bot exists and is enabled
    bot = Bots.query.filter_by(name=bot_name).first()

    if bot is None:
        app.logger.error(f"Bot '{bot_name}' not found in database.")
        return "Bot not found.", 404

    if not bot.enabled:
        app.logger.warning(f"Bot '{bot_name}' is not enabled.")
        return "Bot not enabled.", 400

    # Get account
    account_name = bot.account.name if bot.account else None
    account = Accounts.query.filter_by(name=account_name).first() if account_name else None

    if account is None:
        app.logger.error(f"Account for bot '{bot_name}' not found in database.")
        return "Account not found.", 404

    # Get open orders
    orders = get_open_orders(exchange, bot.pair, account.api_key, account.api_secret, account.password)

    # Determine order side and type from signal type
    if signal_type == 'ENTER-LONG':
        side = 'buy'
        order_type = 'limit'
        close_signal_type = 'EXIT-LONG'
    elif signal_type == 'ENTER-SHORT':
        side = 'sell'
        order_type = 'limit'
        close_signal_type = 'EXIT-SHORT'
    elif signal_type == 'EXIT-LONG':
        side = 'sell'
        order_type = 'market'
        close_signal_type = 'ENTER-SHORT'
    elif signal_type == 'EXIT-SHORT':
        side = 'buy'
        order_type = 'market'
        close_signal_type = 'ENTER-LONG'
    else:
        app.logger.error(f"Invalid signal type: {signal_type}")
        return "Invalid signal type.", 400

    # Determine order amount from bot amount and balance
    balance = get_balance(exchange, bot.pair, account.api_key, account.api_secret, account.password)
    order_amount = balance['free'] * bot.amount

    # Check if there are existing orders for the same bot and symbol
    existing_orders = [o for o in orders if o['info']['bot'] == bot_name and o['symbol'] == bot.pair]

    if existing_orders:
        # Cancel existing orders if there are any
        for order in existing_orders:
            cancel_order(exchange, order['id'], bot.pair, account.api_key, account.api_secret, account.password)

    # Place new order
    order = create_order(exchange, bot.pair, order_type, side, order_amount, account.api_key, account.api_secret, account.password)

    # Save bot position
    bot.position = order['id']
    db.session.commit()

    # Placing the order
    try:
        order = exchange.create_order(symbol=symbol, type='limit', side=side, amount=order_amount, price=price)
        app.logger.info(f"Placed {signal_type} order on {exchange.id} for bot '{bot_name}'. Order details: {order}")
    except Exception as e:
        app.logger.error(f"Failed to place {signal_type} order for bot '{bot_name}' on {exchange.id}. Error: {e}")
        return "Failed to place order.", 500
    if existing_orders:
        # Cancel existing orders if there are any
        for order in existing_orders:
            cancel_order(exchange, order['id'], bot.pair, account.api_key, account.api_secret, account.password)
            app.logger.info(f"Canceled existing order: {order['id']}")

    # Place order
    order = create_order(exchange, symbol, side, order_type, order_amount, bot.take_profit, bot.stop_loss, bot.trailing_stop, bot.trailing_stop_distance, bot.leverage, bot.post_only)
    if not order:
        app.logger.error(f"Failed to place order for bot '{bot_name}'.")
        return "Failed to place order.", 500

    app.logger.info(f"Placed {side} order for bot '{bot_name}' and symbol '{bot.symbol}'.")
    app.logger.debug(f"Order: {order}")

    # Save order to database
    db_order = Positions(
        bot_id=bot.id,
        exchange=exchange_name,
        symbol=symbol,
        order_id=order['id'],
        order_type=order_type,
        side=side,
        amount=order_amount,
        price=order['price'],
        status='open',
        take_profit=bot.take_profit,
        stop_loss=bot.stop_loss,
        trailing_stop=bot.trailing_stop,
        trailing_stop_distance=bot.trailing_stop_distance,
        leverage=bot.leverage,
        post_only=bot.post_only
    )
    db.session.add(db_order)
    db.session.commit()

    return 'OK', 200


def cancel_order(exchange, order_id, symbol, api_key, secret_key, password=None):
    try:
        exchange.cancel_order(order_id, symbol, api_key=api_key, secret=secret_key, password=password)
        return True
    except Exception as e:
        app.logger.error(f"Failed to cancel order {order_id}: {e}")
        return False


def create_order(exchange, symbol, side, order_type, amount, take_profit=None, stop_loss=None, trailing_stop=None, trailing_stop_distance=None, leverage=None, post_only=False):
    if side == 'buy':
        if order_type == 'limit':
            price = exchange.fetch_order_book(symbol)['asks'][0][0]
            if post_only:
                order = exchange.create_limit_buy_order(symbol, amount, price, {'postOnly': True})
            else:
                order = exchange.create_limit_buy_order(symbol, amount, price)
        elif order_type == 'market':
            if post_only:
                app.logger.error(f"Cannot set post_only to True for market buy order.")
                return None
            else:
                order = exchange.create_market_buy_order(symbol, amount)
            elif side == 'sell':
                if order_type == 'limit':
                    price = exchange.fetch_order_book(symbol)['bids'][0][0]
                    if post_only:
                        order = exchange.create_limit_sell_order(symbol, amount, price, {'postOnly': True})
                    else:
                        order = exchange.create_limit_sell_order(symbol, amount, price)
                elif order_type == 'market':
                        if post_only:
                            app.logger.error(f"Cannot set post_only to True for market sell order.")
                            return None
                        else:
                            order = exchange.create_market_sell_order(symbol, amount)
                            if order and take_profit:
                                take_profit_price = calculate_take_profit_price(side=side, entry_price=entry_price,
                                                                                take_profit=take_profit)
                                try:
                                    tp_order = exchange.create_order(
                                        symbol=symbol,
                                        side='SELL' if side == 'BUY' else 'BUY',
                                        type='LIMIT',
                                        timeInForce='GTC',
                                        quantity=amount,
                                        price=take_profit_price,
                                        stopPrice=take_profit_price,
                                        newOrderRespType='FULL'
                                    )
                                    print(f"Take Profit order created: {tp_order}")
                                except Exception as e:
                                    print(f"Error creating Take Profit order: {e}")


def get_open_orders(exchange, pair, api_key, api_secret, password):
    exchange = getattr(ccxt, exchange)({
        'apiKey': api_key,
        'secret': api_secret,
        'password': password,
    })
    orders = exchange.fetch_open_orders(pair)
    return orders


def get_balance(exchange, pair, api_key, api_secret, password):
    exchange = getattr(ccxt, exchange)({
        'apiKey': api_key,
        'secret': api_secret,
        'password': password,
    })
    balance = exchange.fetch_balance()
    return balance[pair]


def calculate_take_profit_price(side, entry_price, take_profit):
    if side == "buy":
        return entry_price * (1 + take_profit)
    elif side == "sell":
        return entry_price * (1 - take_profit)
    else:
        raise ValueError("Invalid side specified. Must be 'buy' or 'sell'.")


if __name__ == '__main__':
    #app.app_context().push()
    #db.drop_all()
    #db.create_all()

    #Accounts.__table__.columns.user_id.unique = False
    app.run(debug=True)