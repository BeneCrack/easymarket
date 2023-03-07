import json
from datetime import datetime
from flask import Markup, flash, request, Flask, render_template, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required
from flask_sqlalchemy import SQLAlchemy
from classes.exchange import Exchange
from classes.models import ExchangeModel, Bots, Accounts, Signals, Positions, Role, User, BotFees

# Load Flask app
app = Flask(__name__)

# Load configuration from environment variable
app.config.from_envvar('APP_CONFIG')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///easymarket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'super-secret-key'

# create database and data models
db = SQLAlchemy(app)
engine = db.engine
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
    bots = Bots.query.filter_by(user_id=current_user.id).all()
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
        time_interval = request.form['time_interval']
        account_id = request.form['account']
        bt_type = request.form["type"]
        user_id = current_user.id
        leverage = request.form["leverage"]
        take_profit = request.form["take_profit"]
        stop_loss = request.form["stop_loss"]

        # retrieve the Account object associated with the given account_id
        account = Accounts.query.filter_by(id=account_id).first()
        # retrieve the ExchangeModel id associated with the Account object
        exchange_short = account.exchanges.short

        # Create a new bot object
        bot = Bots(name=name, enabled=enabled, order_type=bt_type, base_order_size=amount, leverage=leverage,
                   exchange=exchange_short, symbol=pair,
                   take_profit=take_profit, stop_loss=stop_loss, description=description, time_interval=time_interval,
                   user_id=user_id,
                   account_id=account_id)

        # Get the exchange associated with the selected account
        account = Accounts.query.filter_by(id=account_id).first()
        exchange_model = get_exchange_client(account)

        # Load Fees
        maker_fee, taker_fee = exchange_model.get_trading_fees(pair)

        bot_fees = BotFees(bot=bot, maker_fee=maker_fee, taker_fee=taker_fee)

        db.session.add(bot_fees)
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
    bot = Bots.query.filter_by(id=id).first()
    if not bot:
        raise ValueError(f'Bot "{bot.name}" not found')

    if request.method == 'POST':
        bot.name = request.form['name']
        bot.enabled = bool(request.form.get("enabled"))
        bot.symbol = request.form["pair"]
        bot.amount = request.form["amount"]
        bot.description = request.form['description']
        bot.time_interval = request.form['time_interval']
        bot.account_id = request.form['account']
        bot.order_type = request.form["type"]
        bot.user_id = current_user.id
        bot.leverage = request.form["leverage"]
        bot.take_profit = request.form["take_profit"]
        bot.stop_loss = request.form["stop_loss"]

        # Get the exchange associated with the selected account
        account = Accounts.query.filter_by(id=request.form['account']).first()
        exchange_model = get_exchange_client(account)

        # Load Fees
        maker_fee, taker_fee = exchange_model.get_trading_fees(request.form["pair"])

        bot.botfees.maker_fee = maker_fee
        bot.botfees.taker_fee = taker_fee

        db.session.commit()

        flash('Bot updated successfully!')
        return redirect(url_for('bots'))
    else:
        accounts = Accounts.query.filter_by(user_id=current_user.id).all()
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
    #accounts = db.session.query(Accounts, ExchangeModel.name).join(ExchangeModel, Accounts.exchange_id == ExchangeModel.id).all()
    accounts = Accounts.query.filter_by(user_id=current_user.id).all()
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
        testnet = bool(request.form.get("testnet"))

        account = Accounts(name=name, exchange_id=exchange_id, api_key=api_key, api_secret=api_secret,
                           password=password, testnet=testnet)

        # Save the total balance in USDT to the account
        exchange_client = get_exchange_client(account)
        total_balance = exchange_client.get_total_balance()
        account.balance_usdt = total_balance

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
        account.testnet = request.form["testnet"]

        db.session.commit()

        flash('Account updated successfully!', 'success')
        return redirect(url_for('accounts'))

    return render_template('edit_account.html', account=account, exchanges=ExchangeModel.query.all())


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
    # new_exchange = Exchanges(name="Kucoin Futures Sandbox", short="kucoinfuturesusd")
    # db.session.add(new_exchange)
    # db.session.commit()
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
    exchange_model = get_exchange_client(account)

    if exchange_model is not None:

        # Load markets
        try:
            markets = exchange_model.load_markets()
        except Exception as e:
            return f'Error loading markets: {e}'

        # Extract the market symbols and sort them alphabetically
        pairs = sorted([symbol for symbol in markets.keys()])
        # Convert pairs to a JSON-formatted string
        pairs_json = json.dumps(pairs)
        # Return the available pairs as a JSON response
        return pairs_json
    else:
        print(f"No account found with id {account_id}")


@app.route('/load/leverage/<int:account_id>/<string:pair>')
def load_leverage(account_id, pair):
    # Get the exchange associated with the selected account
    account = Accounts.query.filter_by(id=account_id).first()
    exchange = get_exchange_client(account)
    if exchange is not None:
        # Load Leverage
        try:
            leverage = exchange.get_available_leverage(pair)
        except Exception as e:
            return f'Error loading leverage: {e}'

        # Return the available pairs as a JSON response
        return jsonify(leverage)
    else:
        print(f"No account found with id {exchange}")


@app.route('/load/intervals/<int:account_id>/<string:symbol>')
def load_intervals(account_id, symbol):
    # Get the exchange associated with the selected account
    account = Accounts.query.filter_by(id=account_id).first()
    exchange_client = get_exchange_client(account)
    if exchange_client is not None:
        # Load Leverage
        try:
            time_intervals = exchange_client.get_time_intervals(symbol)
        except Exception as e:
            return f'Error loading time_intervals: {e}'

        # Return the available pairs as a JSON response
        return jsonify(time_intervals)
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


@app.route('/load/balance', methods=['POST'])
def load_balance():
    data = request.get_json()
    account_id = data['account_id']
    total_balance = get_total_account_balance(account_id)
    usdt_balance = get_usdt_account_balance(account_id)
    # Return the available pairs as a JSON response
    return jsonify({'total_balance': total_balance, 'usdt_balance': usdt_balance})



#################################################################################
########################### TRADINGVIEW WEBHOOK #################################
#################################################################################

# GET PORTFOLIO VALUE OF ACCOUNT
def get_total_account_balance(account_id):

    account = Accounts.query.filter_by(id=account_id).first()

    exchange_client = get_exchange_client(account)
    # Load balance
    account.balance_total = exchange_client.get_total_balance()
    db.session.commit()
    # Return the available pairs as a JSON response
    return account.balance_total

# GET PORTFOLIO VALUE OF ACCOUNT
def get_usdt_account_balance(account_id):

    account = Accounts.query.filter_by(id=account_id).first()

    exchange_client = get_exchange_client(account)
    # Load balance
    account.balance_usdt = exchange_client.get_usdt_balance()
    db.session.commit()
    # Return the available pairs as a JSON response
    return account.balance_usdt


# Get the exchange client for the bot
def get_exchange_client(account):
    exchange_instance = Exchange(account.exchanges.short, account.api_key, account.api_secret, account.password,
                                 account.testnet)
    if account.testnet:
        exchange_instance.set_testnet()
    return exchange_instance


# Get the current position for the bot
def get_position(bot_id):
    return Positions.query.filter_by(bot_id=bot_id).first()


# Calculate the order amount based on the bot's configured amount
def get_balances(bot):
    if not bot:
        return None
    balance_usdt = get_usdt_account_balance(bot.accounts.id) or 0.0
    order_amount = balance_usdt * bot.base_order_size / 100.0
    return order_amount

def calculate_order_quantity(exchange_client, symbol, order_amount, price=None):
    """
    Calculate the order quantity based on the order amount, price and symbol.

    Args:
        exchange_client (ccxt.Exchange): The exchange client.
        symbol (str): The symbol (e.g. 'BTC/USDT').
        order_amount (float): The order amount as a percentage of the available balance.
        price (float): The price at which the order should be executed.

    Returns:
        float: The order quantity.
    """
    symbol_info = exchange_client.load_markets()[symbol]
    balance = exchange_client.fetch_balance()['total']
    quote_currency = symbol_info['quote']
    quantity_precision = symbol_info['precision']['amount']

    # Retrieve the available balance in the quote currency
    if quote_currency in balance:
        available_balance = balance[quote_currency]['free']
    else:
        # Fetch balance for the quote currency from the symbol
        available_balance = exchange_client.fetch_balance({'type': 'trading', 'currency': quote_currency})['free']

    # Calculate the order amount based on the bot's configured percentage of the available balance
    amount = float(available_balance) * (order_amount / 100.0)

    if price is None:
        # For market orders, we calculate the quantity based on the order amount
        min_notional = symbol_info['limits']['cost']['min']
        quantity = max(exchange_client.amount_to_precision(symbol, amount / min_notional), symbol_info['limits']['amount']['min'])
    else:
        # For limit orders, we calculate the quantity based on the order amount and price
        min_cost = symbol_info['limits']['cost']['min']
        quantity = max(exchange_client.amount_to_precision(symbol, amount / price), symbol_info['limits']['amount']['min'])
        quantity = exchange_client.price_to_precision(symbol, quantity * price)
        quantity = max(quantity, exchange_client.amount_to_precision(symbol, min_cost / price))

    return exchange_client.amount_to_precision(symbol, quantity, precision=quantity_precision)


def update_position(bot_id, order_id, status, amount, price, timestamp, stop_loss, take_profit):
    """
    Update the status of a position in the database
    """
    bot = Bots.query.filter_by(id=bot_id).first()
    if not bot:
        raise ValueError(f'Bot "{bot.name}" not found')
    position = Positions.query.filter_by(bot_id=bot.id, order_id=order_id).first()
    if not position:
        raise ValueError(f'Position with order ID "{order_id}" not found')
    if bot.order_type == "LIMIT":
        fees = bot.botfees.maker_fee
    else:
        fees = bot.botfees.taker_fee
    position.status = status
    position.amount = amount
    position.price = price
    position.closed_at = timestamp
    position.take_profit = take_profit
    position.stop_loss = stop_loss

    position.close_price = price
    position.close_quantity = amount
    position.fees = amount * price * fees
    db.session.commit()


def create_long_order(exchange_client, bot, order_amount, price=None):
    symbol = bot.symbol
    side = 'BUY'
    position_side = 'long'
    order_type = bot.order_type

    # Calculate the order quantity
    quantity = calculate_order_quantity(exchange_client, symbol, order_amount, price)

    # Create the order
    if order_type == 'LIMIT':
        order = exchange_client.create_limit_buy_order(symbol, quantity, price)
    else:
        order = exchange_client.create_market_buy_order(symbol, quantity)

    # Create or update the position
    update_position(bot.id, order['id'], position_side, order_amount, order['price'], datetime.now())

    return order


def create_short_order(exchange_client, bot, order_amount, price=None):
    symbol = bot.symbol
    side = 'SELL'
    position_side = 'short'
    order_type = bot.order_type

    # Check if symbol is reversed in the exchange
    exchange_info = exchange_client.get_symbol_info(symbol)
    if exchange_info['symbol_type'] == 'FUTURE' and bot.reverse_market:
        symbol = f"{symbol.split('/')[1]}{symbol.split('/')[0]}"

    # Calculate the order quantity
    quantity = calculate_order_quantity(exchange_client, symbol, order_amount, price)

    # Create the order
    if order_type == 'LIMIT':
        order = exchange_client.create_limit_sell_order(symbol, quantity, price)
    else:
        order = exchange_client.create_market_sell_order(symbol, quantity)

    # Create or update the position
    update_position(bot.id, order['id'], position_side, order_amount, order['price'], datetime.now())

    return order


def create_long_exit_order(exchange_client, bot, quantity, price=None):
    """
    Create a sell order to exit a long position
    """
    if not exchange_client or not bot or not quantity:
        return None

    symbol = bot.symbol
    exchange_info = exchange_client.get_exchange_info(symbol)
    if not exchange_info:
        return None

    # Check if symbol is reversed in the exchange
    if exchange_info['symbol_type'] == 'FUTURE' and bot.reverse_market:
        symbol = f"{symbol.split('/')[1]}{symbol.split('/')[0]}"

    order_type = bot.order_type
    if order_type == 'MARKET':
        order = exchange_client.create_market_sell_order(symbol, quantity)
    else:
        if not price:
            ticker = exchange_client.get_ticker(symbol)
            if not ticker:
                return None
            price = ticker['askPrice']
        order = exchange_client.create_limit_sell_order(symbol, quantity, price)

    return order


def create_short_exit_order(exchange_client, bot, quantity, price=None):
    """
    Create a buy order to exit a short position
    """
    if not exchange_client or not bot or not quantity:
        return None

    symbol = bot.symbol
    exchange_info = exchange_client.get_exchange_info(symbol)
    if not exchange_info:
        return None

    # Check if symbol is reversed in the exchange
    if exchange_info['symbol_type'] == 'FUTURE' and bot.reverse_market:
        symbol = f"{symbol.split('/')[1]}{symbol.split('/')[0]}"

    order_type = bot.order_type
    if order_type == 'MARKET':
        order = exchange_client.create_market_buy_order(symbol, quantity)
    else:
        if not price:
            ticker = exchange_client.get_ticker(symbol)
            if not ticker:
                return None
            price = ticker['bidPrice']
        order = exchange_client.create_limit_buy_order(symbol, quantity, price)

    return order


def calculate_exit_order_size(bot_config, position):
    if not bot_config or not position:
        return None
    if position.side == 'long':
        return position.quantity
    elif position.side == 'short':
        # For a short position, we need to calculate the amount of the base currency (e.g. BTC) to sell
        # We can use the unrealized PNL as an estimate of the amount of the base currency held in the position
        unrealized_pnl = position.pnl
        base_currency = bot_config['symbol'].split('/')[0]
        ticker = get_ticker(bot_config)
        if ticker:
            base_price = ticker['bid'] if position.side == 'short' else ticker['ask']
            base_currency_amount = unrealized_pnl / base_price
            return base_currency_amount
    return None


def create_order(exchange_client, bot, side, signal_type, quantity, price=None):
    try:
        if price is not None:
            order = exchange_client.create_order(
                symbol=bot.symbol,
                side=side,
                type=bot.order_type,
                timeInForce='GTC',
                quantity=quantity,
                price=price
            )
        else:
            order = exchange_client.create_order(
                symbol=bot.symbol,
                side=side,
                type=bot.order_type,
                timeInForce='GTC',
                quantity=quantity
            )

        # Update positions table with order details
        if side == 'BUY':
            position_entry = Positions(
                bot_id=bot.id,
                symbol=bot.symbol,
                entry_price=order['price'],
                entry_time=order['transactTime'],
                signal_type=signal_type,
                order_id=order['orderId'],
                order_quantity=order['origQty'],
                order_type=bot.order_type,
                stop_loss=None,
                take_profit=None,
                user_id=None,
                status='OPEN'
            )
            db.session.add(position_entry)
        else:
            position = Positions.query.filter_by(
                bot_id=bot.id,
                symbol=bot.symbol,
                status='OPEN'
            ).first()
            if position:
                position.signal_type = bot.order_type
                position.order_id = order['orderId']
                position.open_time = order['transactTime']
                position.order_price = order['price']
                position.order_quantity = order['origQty']
            else:
                raise ValueError('Could not update position table: Position not found')

        db.session.commit()
        return order

    except Exception as e:
        # Log error
        app.logger.error(f'Error processing TradingView webhook: {e}')
        return None


def get_bot_by_id(bot_id):
    return Bots.query.filter_by(id=bot_id).first()


# TradingView webhook route
@app.route('/webhook/tradingview', methods=['POST'])
def tradingview_webhook():
    try:
        data = json.loads(request.data)
        signal = data['message']
        bot = get_bot_by_id(signal.split('_')[-1])
        if not bot:
            return jsonify({'error': f'Bot "{bot.name}" not found'}), 404

        exchange_client = get_exchange_client(bot.accounts)
        if not exchange_client:
            return jsonify({'error': 'Invalid bot configuration'}), 400
        position = get_position(bot.id)
        if not position:
            return jsonify({'error': f'Position for bot "{bot.name}" not found'}), 404
        order_amount = calculate_order_quantity(exchange_client, bot.symbol, bot.order_amount)
        if not order_amount:
            return jsonify({'error': 'Unable to calculate order amount'}), 400

        # ENTER LONG TRADE AND CREATE POSITION
        if signal.startswith('ENTER-LONG'):
            order_type = bot.order_type
            side = 'BUY'

            if order_type == 'LIMIT':
                price = bot.price
                quantity = calculate_order_quantity(exchange_client, bot.symbol, bot.order_amount, price)
            else:
                price = None
                quantity = order_amount

            order = create_long_order(exchange_client, bot, side, quantity)

            if not order:
                return jsonify({'error': 'Unable to create order'}), 500
            stop_loss = bot.stop_loss
            take_profit = bot.take_profit

            update_position(bot.id, order['orderId'], 'long', order_amount, order['price'], datetime.now(), stop_loss,
                            take_profit)
            return jsonify({'message': 'Long position created successfully'}), 200

        # EXIT LONG TRADE AND UPDATE POSITION
        elif signal.startswith('EXIT-LONG'):
            position = get_position(bot.id)
            if not position:
                return jsonify({'error': f'Position for bot "{bot.name}" not found'}), 404
            order = exchange_client.get_order_status(bot.symbol, position.order_id)
            if not order:
                return jsonify({'error': 'Unable to get order details'}), 500
            if order['status'] == 'FILLED':
                order_type = bot.order_type
                side = 'SELL'
                if order_type == 'LIMIT':
                    price = float(order['price'])
                    quantity = calculate_order_quantity(exchange_client=exchange_client, symbol=bot.symbol,
                                                        order_amount=bot.order_amount, price=price)
                else:
                    price = None
                    quantity = order_amount
                order = create_long_exit_order(exchange_client, bot, side, quantity, price)
                update_position(bot.id, order['orderId'], 'closed', order_amount, order['price'], datetime.now())
                return 'Order created successfully'
            else:
                return jsonify({'error': 'Order has not been filled yet'}), 400

        # ENTER SHORT TRADE AND CREATE POSITION
        elif signal.startswith('ENTER-SHORT'):
            order_type = bot.order_type
            side = 'SELL'
            if order_type == 'LIMIT':
                price = bot.price
                quantity = calculate_order_quantity(exchange_client, bot.symbol, bot.order_amount, price)
            else:
                price = None
                quantity = order_amount
            order = create_short_order(exchange_client, bot, side, quantity, price)
            if not order:
                return jsonify({'error': 'Unable to create order'}), 500
            stop_loss = bot.stop_loss
            take_profit = bot.take_profit
            update_position(bot.id, order['orderId'], 'short', order_amount, order['price'], datetime.now(), stop_loss,
                            take_profit)
            return jsonify({'message': 'Short position created successfully'}), 200

        # EXIT SHORT TRADE AND UPDATE POSITION
        elif signal.startswith('EXIT-SHORT'):
            position = get_position(bot.id)
            if not position:
                return jsonify({'error': f'Position for bot "{bot.name}" not found'}), 404
            order = exchange_client.get_order_status(position.order_id)
            if not order:
                return jsonify({'error': 'Unable to get order details'}), 500
            if order['status'] == 'FILLED':
                order_type = bot.order_type
                side = 'BUY'
                if order_type == 'LIMIT':
                    price = float(order['price'])
                    quantity = calculate_order_quantity(exchange_client=exchange_client, symbol=bot.symbol, order_amount=bot.order_amount, price=price)
                else:
                    quantity = order_amount
                    price = None
                order = create_short_exit_order(exchange_client, bot, side, quantity, price)
                update_position(bot.id, order['orderId'], 'closed', order_amount, order['price'], datetime.now())
                return 'Order created successfully'
            else:
                return jsonify({'error': 'Order has not been filled yet'}), 400
    except Exception as e:
        # Log error
        app.logger.error(f'Error processing TradingView webhook: {e}')
        return 'Error processing TradingView webhook', 500


def calculate_take_profit_price(side, entry_price, take_profit):
    if side == "buy":
        return entry_price * (1 + take_profit)
    elif side == "sell":
        return entry_price * (1 - take_profit)
    else:
        raise ValueError("Invalid side specified. Must be 'buy' or 'sell'.")



if __name__ == '__main__':
    # app.app_context().push()
    # db.drop_all()
    # db.create_all()

    # Accounts.__table__.columns.user_id.unique = False
    app.run(debug=True)

# def close_position(self, symbol, position_id):
# order = None
# position = None
# for open_position in self.get_open_positions(symbol):
# if open_position['order_id'] == position_id:
# position = open_position
# break
# if position:
# side = 'sell' if position['side'] == 'buy' else 'buy'
# order = self.create_market_order(symbol, side, abs(position['amount']))
# if order and order['status'] == 'closed':
# position['is_open'] = False
# position['close_order_id'] = order['id']
# position['close_price'] = order['price']
# position['close_time'] = datetime.now()
# self.session.commit()
# return True
# return False
