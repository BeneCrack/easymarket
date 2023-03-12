import asyncio
import json
from datetime import datetime
from flask import Markup, flash, request, Flask, render_template, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required
from database import db, init_db
from config import Config
from classes.exchange import Exchange
from classes.models import ExchangeModels, Bots, Accounts, Signals, Positions, Role, User, BotFees

# Load Flask app
app = Flask(__name__)

# Load configuration from config file
app.config.from_object(Config)

# Initialize the db object with the Flask app
init_db(app)

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
        user = User()
        user.email = email
        user.active = True
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
        amount = float(request.form["amount"])
        description = request.form['description']
        time_interval = request.form['time_interval']
        account_id = request.form['account']
        bt_type = request.form["type"]
        user_id = current_user.id
        leverage = float(request.form["leverage"])

        try:
            take_profit = float(request.form["take_profit"])
        except ValueError:
            take_profit = 0.0  # or some other default value
        try:
            stop_loss = float(request.form["stop_loss"])
        except ValueError:
            stop_loss = 0.0  # or some other default value

        # retrieve the Account object associated with the given account_id
        account = Accounts.query.filter_by(id=account_id).first()
        # retrieve the ExchangeModel id associated with the Account object
        exchange_short = account.exchangemodels.short

        # Create a new bot object
        bot = Bots(name=name, enabled=enabled, order_type=bt_type, base_order_size=amount, leverage=leverage,
                   exchange=exchange_short, symbol=pair,
                   take_profit=take_profit, stop_loss=stop_loss, description=description, time_interval=time_interval,
                   user_id=user_id, exchange_id=account.exchange_id, account_id=account_id)

        db.session.add(bot)
        db.session.commit()
        bot = Bots.query.filter_by(user_id=current_user.id).first()

        exchange_model = get_exchange_client(account)

        # Load Fees
        maker_fee, taker_fee = exchange_model.get_trading_fees(pair)

        bot_fees = BotFees(bot_id=bot.id, maker_fee=maker_fee, taker_fee=taker_fee)

        db.session.add(bot_fees)
        db.session.commit()

        flash('Bot created successfully!')
        return redirect(url_for('bots'))
    else:
        account = Accounts.query.filter_by(user_id=current_user.id).all()
        return render_template('create-bot.html', accounts=account)


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
    # accounts = db.session.query(Accounts, ExchangeModel.name).join(ExchangeModel, Accounts.exchange_id == ExchangeModel.id).all()
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
        account.user_id = current_user.id

        db.session.add(account)
        db.session.commit()

        # Retrieve the account from the database to get the exchange short name
        account = Accounts.query.filter_by(user_id=current_user.id).order_by(Accounts.id.desc()).first()

        # Save the total balance in USDT to the account
        exchange_client = get_exchange_client(account)
        total_balance = exchange_client.get_usdt_balance
        account.balance_usdt = total_balance

        flash('Account created successfully!')
        return redirect(url_for('accounts'))
    else:
        exchanges = ExchangeModels.query.all()
        return render_template('add-account.html', exchanges=exchanges)


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

    return render_template('edit-account.html', account=account, exchanges=ExchangeModels.query.all())


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
    new_exchange = ExchangeModels(name="Kucoin Spot", short="kucoin")
    db.session.add(new_exchange)
    db.session.commit()
    all_exchanges = ExchangeModels.query.all()
    return render_template("exchanges.html", exchanges=all_exchanges)

@app.route("/transfer/main/futures")
@login_required
def transfer():
    account = Accounts.query.get_or_404(4)
    exchange_client = get_exchange_client(account)
    # Transfer from main account to futures account
    response = exchange_client.transfer('main', 'futures', 'USDT', 1)
    return render_template("transfer.html", response=response)


@app.route("/trades")
@login_required
def trades():
    return render_template("trades.html")


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


#################################################################################
################################ FUNCTIONS ######################################
#################################################################################


def convert_to_usdt(exchange, symbol, amount):
    ticker = exchange.get_ticker(symbol)
    price = ticker['last']
    usdt_ticker = exchange.get_ticker('USDT/USDT')
    usdt_price = usdt_ticker['last']
    value = price * amount
    if symbol != 'USDT':
        value = value / usdt_price
    return value


def get_total_account_balance(account_id):
    """
    GET TOTAL PORTFOLIO VALUE OF ACCOUNT
    """
    account = Accounts.query.filter_by(id=account_id).first()
    exchange_client = get_exchange_client(account)
    # Load balance
    account.balance_total = exchange_client.get_total_balance()
    db.session.commit()
    # Return the available pairs as a JSON response
    return account.balance_total


def get_usdt_account_balance(account_id):
    """
    GET USDT PORTFOLIO VALUE OF ACCOUNT
    """
    account = Accounts.query.filter_by(id=account_id).first()
    exchange_client = get_exchange_client(account)
    # Load balance
    account.balance_usdt = exchange_client.get_usdt_balance()
    db.session.commit()
    # Return the available pairs as a JSON response
    return account.balance_usdt


def get_exchange_client(account):
    """
    Get the exchange client.
    """
    print("371")
    exchange_instance = Exchange(account)
    return exchange_instance


def get_position(bot_id):
    """
    Get the position for a bot.
    """
    return Positions.query.filter_by(bot_id=bot_id).first()


def get_bot_by_id(bot_id):
    """
    Get a bot by ID.
    """
    return Bots.query.filter_by(id=bot_id).first()


def get_balances(bot):
    """
    Calculate the order amount based on the bot's configured amount
    """
    if not bot:
        return None
    balance_usdt = get_usdt_account_balance(bot.accounts.id) or 0.0
    order_amount = balance_usdt * bot.base_order_size / 100.0
    return order_amount


def calculate_order_quantity(exchange_client, symbol, order_amount_percentage, position_type, order_type, price=None):
    """
    Calculate the order quantity based on the order amount, price, symbol, position type, and order type.

    Args:
        exchange_client (ccxt.Exchange): The exchange client.
        symbol (str): The symbol (e.g. 'BTC/USDT').
        order_amount_percentage (float): The order amount as a percentage of the available balance.
        position_type (str): The position type ('long' or 'short').
        order_type (str): The order type ('limit' or 'market').
        price (float): The price at which the order should be executed.

    Returns:
        float: The order quantity.
    """

    symbol_info = exchange_client.load_markets()[symbol]

    # Check if symbol is inverted in the exchange
    print(symbol)
    print(symbol_info)
    if 'inverted' in symbol_info:
        symbol = f"{symbol.split('/')[1]}/{symbol.split('/')[0]}"

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
    amount = float(available_balance) * (order_amount_percentage / 100.0)

    if order_type == 'market':
        # For market orders, we calculate the quantity based on the order amount
        min_notional = symbol_info['limits']['cost']['min']
        quantity = max(exchange_client.amount_to_precision(symbol, amount / min_notional),
                       symbol_info['limits']['amount']['min'])
    elif order_type == 'limit':
        # For limit orders, we calculate the quantity based on the order amount and price
        min_cost = symbol_info['limits']['cost']['min']
        quantity = max(exchange_client.amount_to_precision(symbol, amount / price),
                       symbol_info['limits']['amount']['min'])
        quantity = exchange_client.price_to_precision(symbol, quantity * price)
        quantity = max(quantity, exchange_client.amount_to_precision(symbol, min_cost / price))
    else:
        raise ValueError(f'Invalid order type: {order_type}')

    if position_type == 'long':
        # For long positions, we buy the base currency and sell the quote currency
        if order_type == 'limit':
            quantity = calculate_long_limit_order_quantity(exchange_client, symbol, price, quantity)
        elif order_type == 'market':
            quantity = calculate_long_market_order_quantity(exchange_client, symbol, quantity)
        else:
            raise ValueError(f'Invalid order type: {order_type}')
    elif position_type == 'short':
        # For short positions, we sell the base currency and buy the quote currency
        if order_type == 'limit':
            quantity = calculate_short_limit_order_quantity(exchange_client, symbol, price, quantity)
        elif order_type == 'market':
            quantity = calculate_short_market_order_quantity(exchange_client, symbol, quantity)
        else:
            raise ValueError(f'Invalid order type: {order_type}')
    else:
        raise ValueError(f'Invalid position type: {position_type}')

    return exchange_client.amount_to_precision(symbol, quantity)


def calculate_long_limit_order_quantity(exchange_client, symbol, price, quantity):
    """
    Calculate the order quantity for a long limit order.

    Args:
        exchange_client (ccxt.Exchange): The exchange client.
        symbol (str): The symbol (e.g. 'BTC/USDT').
        price (float): The price at which the order should be executed.
        quantity (float): The quantity of the order.

    Returns:
        float: The order quantity.
    """
    symbol_info = exchange_client.load_markets()[symbol]

    # Retrieve the maximum allowed quantity
    max_quantity = symbol_info['limits']['amount']['max']

    # Calculate the maximum order quantity based on the maximum allowed quantity
    max_quantity_from_limit = max_quantity

    # Calculate the maximum order quantity based on the available quote currency
    quote_currency = symbol_info['quote']
    balance = exchange_client.fetch_balance()['total']
    if quote_currency in balance:
        available_quote_balance = float(balance[quote_currency]['free'])
    else:
        available_quote_balance = float(
            exchange_client.fetch_balance({'type': 'trading', 'currency': quote_currency})['free'])

    # Calculate the maximum order quantity based on the order price and quote currency balance
    max_quantity_from_balance = available_quote_balance / price

    # Choose the minimum of the three calculated maximum order quantities
    max_order_quantity = min(max_quantity_from_limit, max_quantity_from_balance)

    # Ensure that the calculated order quantity is within the minimum and maximum allowed quantities
    min_quantity = symbol_info['limits']['amount']['min']
    order_quantity = max(min_quantity, min(max_order_quantity, quantity))

    return order_quantity


def calculate_short_limit_order_quantity(exchange_client, symbol, price, quantity):
    """
    Calculate the order quantity for a short limit order.

    Args:
        exchange_client (ccxt.Exchange): The exchange client.
        symbol (str): The symbol (e.g. 'BTC/USDT').
        price (float): The price at which the order should be executed.
        quantity (float): The quantity of the order.

    Returns:
        float: The order quantity.
    """
    symbol_info = exchange_client.load_markets()[symbol]

    # Retrieve the maximum allowed quantity
    max_quantity = symbol_info['limits']['amount']['max']

    # Calculate the maximum order quantity based on the maximum allowed quantity
    max_quantity_from_limit = max_quantity

    # Calculate the maximum order quantity based on the available base currency
    base_currency = symbol_info['base']
    balance = exchange_client.fetch_balance()['total']
    if base_currency in balance:
        available_base_balance = float(balance[base_currency]['free'])
    else:
        available_base_balance = float(
            exchange_client.fetch_balance({'type': 'trading', 'currency': base_currency})['free'])

    # Calculate the maximum order quantity based on the order price and base currency balance
    max_quantity_from_balance = available_base_balance

    # Choose the minimum of the three calculated maximum order quantities
    max_order_quantity = min(max_quantity_from_limit, max_quantity_from_balance)

    # Ensure that the calculated order quantity is within the minimum and maximum allowed quantities
    min_quantity = symbol_info['limits']['amount']['min']
    order_quantity = max(min_quantity, min(max_order_quantity, quantity))

    return order_quantity


def calculate_long_market_order_quantity(exchange_client, symbol, quantity):
    """
    Calculate the order quantity for a long market order.

    Args:
        exchange_client (ccxt.Exchange): The exchange client.
        symbol (str): The symbol (e.g. 'BTC/USDT').
        quantity (float): The desired order quantity.

    Returns:
        float: The order quantity.
    """
    # Check the minimum notional value
    symbol_info = exchange_client.load_markets()[symbol]
    min_notional = symbol_info['limits']['cost']['min']
    notional = quantity * symbol_info['last']
    if notional < min_notional:
        raise ValueError(
            f'Order quantity {quantity} is too low for symbol {symbol}. Minimum notional value is {min_notional}')

    return quantity


def calculate_short_market_order_quantity(exchange_client, symbol, quantity):
    """
    Calculate the order quantity for a short market order.

    Args:
        exchange_client (ccxt.Exchange): The exchange client.
        symbol (str): The symbol (e.g. 'BTC/USDT').
        quantity (float): The desired order quantity.

    Returns:
        float: The order quantity.
    """
    # Check the minimum notional value
    symbol_info = exchange_client.load_markets()[symbol]
    min_notional = symbol_info['limits']['cost']['min']
    notional = quantity * symbol_info['last']
    if notional < min_notional:
        raise ValueError(
            f'Order quantity {quantity} is too low for symbol {symbol}. Minimum notional value is {min_notional}')

    return quantity


def check_inverted_symbol(exchange_client, symbol):
    """
    Check if the symbol is inverted in the exchange.

    Args:
        exchange_client (ccxt.Exchange): The exchange client.
        symbol (str): The symbol to check.

    Returns:
        str: The inverted symbol, if applicable. Otherwise, the original symbol.
    """
    exchange_markets = exchange_client.load_markets()
    symbol_info = exchange_markets.get(symbol)
    if symbol_info and symbol_info['type'] == 'future' and symbol_info.get('inverse'):
        if '/' in symbol:
            return f"{symbol.split('/')[1]}{symbol.split('/')[0]}"
        else:
            return f"{symbol[-3:]}{symbol[:-3]}"
    else:
        return symbol


def update_position(bot, order_id, position_side, quantity, price, timestamp, position_action=None) -> None:
    """
    Create or update a position based on the provided order details.

    Args:
        bot (Bots): The Bot DB Class
        order_id (str): The ID of the order.
        position_side (str): The side of the position ('long' or 'short').
        quantity (float): The quantity of the position.
        price (float): The price of the position.
        timestamp (datetime): The timestamp of the position.
        position_action (str): The action being taken ('open' or 'close').
    """
    positions = Positions().get_positions(bot.id)

    # Check if there is already an existing position for the order
    for position in positions:
        if position.order_id == order_id:
            # Update the existing position
            if position_action == 'open':
                raise ValueError(f'Position for order {order_id} already exists')
            elif position_action == 'close':
                if position.status != 'open':
                    raise ValueError(f'Position for order {order_id} is not open')
                position.status = 'closed'
                position.exit_price = price
                position.exit_time = timestamp
                # Calculate fees
                if position.order_type == 'limit':
                    if position_side == 'long':
                        fee_rate = bot.botfees.maker_fee
                    else:
                        fee_rate = bot.botfees.taker_fee
                    fee = fee_rate * quantity * price
                else:
                    if position_side == 'long':
                        fee_rate = bot.botfees.taker_fee
                    else:
                        fee_rate = bot.botfees.maker_fee
                    fee = fee_rate * quantity
                position.fees = fee
            else:
                raise ValueError(f'Invalid position action: {position_action}')
            position.save()
            return

    # Create a new position
    if position_action == 'open':
        position_type = 'long' if position_side == 'long' else 'short'
        position = Positions(bot_id=bot.id, symbol=bot.symbol, exchange_id=bot.exchange.id, entry_price=price,
                             entry_time=timestamp, order_id=order_id, order_quantity=quantity,
                             order_type=bot.order_type, position_type=position_type, status='open', user_id=bot.user_id)
        # Calculate fees
        if bot.order_type == 'limit':
            if position_side == 'long':
                fee_rate = bot.botfees.maker_fee
            else:
                fee_rate = bot.botfees.taker_fee
            fee = fee_rate * quantity * price
        else:
            if position_side == 'long':
                fee_rate = bot.botfees.taker_fee
            else:
                fee_rate = bot.botfees.maker_fee
            fee = fee_rate * quantity
        position.fees = fee
        position.save()
    elif position_action == 'close':
        raise ValueError(f'Position for order {order_id} not found')
    else:
        raise ValueError(f'Invalid position action: {position_action}')


async def create_long_order(exchange_client, bot, quantity, price=None):
    """
        Create a long order.

        Args:
            exchange_client (ccxt.Exchange): The exchange client.
            bot (Bot): The Bot object.
            side (str): The order side ('buy' or 'sell').
            quantity (float): The order quantity.

        Returns:
            dict: The order object.
            :param quantity:
            :param bot:
            :param exchange_client:
            :param price:
    """
    symbol = bot.symbol
    position_type = 'long'
    order_type = bot.order_type

    # Check if symbol is reversed in the exchange
    symbol = check_inverted_symbol(exchange_client, symbol)

    # Create the order
    if order_type == 'LIMIT':
        order = exchange_client.create_limit_buy_order(symbol, quantity, price)
    else:
        order = exchange_client.create_market_buy_order(symbol, quantity)

    # Wait for limit order to be filled
    if order_type == 'limit':
        while True:
            order = exchange_client.fetch_order(order['id'], symbol)
            if order['status'] == 'filled':
                break
            await asyncio.sleep(5)

    # Create or update the position
    update_position(bot.id, order['id'], position_type, quantity, order['price'], datetime.now())

    return order


async def create_short_order(exchange_client, bot, quantity, price=None):
    """
        Create a short order.

        Args:
            exchange_client (ccxt.Exchange): The exchange client.
            bot (Bot): The Bot object.
            quantity (float): The order quantity.
            price (float): The order price.

        Returns:
            dict: The order object.
    """
    symbol = bot.symbol
    position_type = 'short'
    order_type = bot.order_type

    # Check if symbol is reversed in the exchange
    symbol = check_inverted_symbol(exchange_client, symbol)

    # Create the order
    if order_type == 'LIMIT':
        order = exchange_client.create_limit_sell_order(symbol, quantity, price)
    else:
        order = exchange_client.create_market_sell_order(symbol, quantity)

    # Wait for limit order to be filled
    if order_type == 'limit':
        while True:
            order = exchange_client.fetch_order(order['id'], symbol)
            if order['status'] == 'filled':
                break
            await asyncio.sleep(5)

    # Create or update the position
    update_position(bot.id, order['id'], position_type, quantity, order['price'], datetime.now())

    return order


async def create_long_exit_order(exchange_client, bot, quantity, price=None):
    """
    Create an order to exit a long position.

    Args:
        exchange_client (ccxt.Exchange): The exchange client.
        bot (Bot): The bot instance.
        quantity (float): The quantity of the order.
        price (float): The price at which the order should be executed (for limit orders).

    Returns:
        dict: The order object returned by the exchange.
    """
    if not exchange_client or not bot or not quantity:
        return None

    symbol = bot.symbol

    # Check if symbol is reversed in the exchange
    symbol = check_inverted_symbol(exchange_client, symbol)
    position_type = 'long'

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

    # Wait for limit order to be filled
    if order_type == 'limit':
        while True:
            order = exchange_client.fetch_order(order['id'], symbol)
            if order['status'] == 'filled':
                break
            await asyncio.sleep(5)

    # Create or update the position
    update_position(bot.id, order['id'], position_type, quantity, order['price'], datetime.now())

    return order


async def create_short_exit_order(exchange_client, bot, quantity, price=None):
    """
    Create an order to exit a short position.

    Args:
        exchange_client (ccxt.Exchange): The exchange client.
        bot (Bot): The bot instance.
        quantity (float): The quantity of the order.
        price (float): The price at which the order should be executed (for limit orders).

    Returns:
        dict: The order object returned by the exchange.
    """
    if not exchange_client or not bot or not quantity:
        return None

    symbol = bot.symbol

    # Check if symbol is reversed in the exchange
    symbol = check_inverted_symbol(exchange_client, symbol)
    position_type = 'short'

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

    # Wait for limit order to be filled
    if order_type == 'limit':
        while True:
            order = exchange_client.fetch_order(order['id'], symbol)
            if order['status'] == 'filled':
                break
            await asyncio.sleep(5)

    # Create or update the position
    update_position(bot.id, order['id'], position_type, quantity, order['price'], datetime.now())

    return order


def calculate_take_profit_price(side, entry_price, take_profit):
    if side == "buy":
        return entry_price * (1 + take_profit)
    elif side == "sell":
        return entry_price * (1 - take_profit)
    else:
        raise ValueError("Invalid side specified. Must be 'buy' or 'sell'.")


#################################################################################
######################## ROUTES FOR AJAX LOADERS  ###############################
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
            print(markets)
        except Exception as e:
            return f'Error loading markets: {e}'

        # Extract the market symbols and sort them alphabetically
        pairs = sorted([symbol.split(":")[0] for symbol in markets.keys()])

        # Return the available pairs as a JSON response
        return jsonify(pairs)
    else:
        print(f"No account found with id {account_id}")


@app.route('/load/leverage/<int:account_id>/<string:symbol>')
def load_leverage(account_id, symbol):
    # Get the exchange associated with the selected account
    account = Accounts.query.filter_by(id=account_id).first()
    exchange_client = get_exchange_client(account)
    print("we here")
    if exchange_client is not None:
        # Load Leverage
        try:
            print("we here1")
            symbolnew = symbol.replace('-', '/')
            leverage = exchange_client.get_available_leverage(symbolnew + ":" + symbolnew.split("/")[1].split(":")[0])
        except Exception as e:
            return f'Error loading leverage: {e}'

        # Return the available pairs as a JSON response
        return jsonify(leverage)
    else:
        print(f"No account found with id {exchange_client}")


@app.route('/load/intervals/<int:account_id>/<string:symbol>')
def load_intervals(account_id, symbol):
    # Get the exchange associated with the selected account
    account = Accounts.query.filter_by(id=account_id).first()
    exchange_client = get_exchange_client(account)
    if exchange_client is not None:
        # Load Leverage
        try:
            symbolnew = symbol.replace('-', '/')
            time_intervals = exchange_client.get_time_intervals(symbolnew + ":" + symbolnew.split("/")[1].split(":")[0])
        except Exception as e:
            return f'Error loading time_intervals: {e}'

        # Return the available pairs as a JSON response
        return list(time_intervals)
    else:
        print(f"No account found with id {account_id}")


@app.route('/load/balance', methods=['POST'])
def load_balance():
    data = request.get_json()
    account_id = data['account_id']
    total_balance = get_total_account_balance(account_id)
    print(total_balance)
    usdt_balance = get_usdt_account_balance(account_id)
    # Return the available pairs as a JSON response
    return jsonify({'total_balance': total_balance, 'usdt_balance': usdt_balance})


#################################################################################
########################### TRADINGVIEW WEBHOOK #################################
#################################################################################

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

        # ENTER LONG TRADE AND CREATE POSITION
        if signal.startswith('ENTER-LONG'):
            order_type = bot.order_type
            if order_type == 'LIMIT':
                price = bot.price
            else:
                price = None
            print("before calculate order ")
            quantity = calculate_order_quantity(exchange_client, bot.symbol, bot.base_order_size, 'long', bot.order_type,
                                                price)
            order = create_long_order(exchange_client, bot, quantity, price)

            if not order:
                return jsonify({'error': 'Unable to create order'}), 500
            stop_loss = bot.stop_loss
            take_profit = bot.take_profit

            update_position(bot, order['orderId'], 'long', quantity, order['price'], datetime.now(), 'open')
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
                    quantity = position.order_quantity
                else:
                    price = None
                    quantity = position.order_quantity
                order = create_long_exit_order(exchange_client, bot, quantity, price)
                update_position(bot.id, order['orderId'], 'closed', quantity, order['price'], datetime.now(), 'close')
                return 'Order created successfully'
            else:
                return jsonify({'error': 'Order has not been filled yet'}), 400

        # ENTER SHORT TRADE AND CREATE POSITION
        elif signal.startswith('ENTER-SHORT'):
            order_type = bot.order_type
            side = 'SELL'
            if order_type == 'LIMIT':
                price = bot.price
            else:
                price = None
            quantity = calculate_order_quantity(exchange_client, bot.symbol, bot.base_order_size, 'short', bot.order_type,
                                                price)
            order = create_short_order(exchange_client, bot, quantity, price)
            if not order:
                return jsonify({'error': 'Unable to create order'}), 500
            stop_loss = bot.stop_loss
            take_profit = bot.take_profit
            update_position(bot, order['orderId'], 'short', quantity, order['price'], datetime.now(), 'open')
            return jsonify({'message': 'Short position created successfully'}), 200

        # EXIT SHORT TRADE AND UPDATE POSITION
        elif signal.startswith('EXIT-SHORT'):
            position = get_position(bot.id)
            if not position:
                return jsonify({'error': f'Position for bot "{bot.name}" not found'}), 404
            order = exchange_client.get_order_status(bot.symbol, position.order_id)
            if not order:
                return jsonify({'error': 'Unable to get order details'}), 500
            if order['status'] == 'FILLED':
                order_type = bot.order_type
                side = 'BUY'
                if order_type == 'LIMIT':
                    price = float(order['price'])
                    quantity = position.order_quantity
                else:
                    quantity = position.order_quantity
                    price = None
                order = create_short_exit_order(exchange_client, bot, quantity, price)
                update_position(bot.id, order['orderId'], 'closed', quantity, order['price'], datetime.now(), 'close')
                return 'Order created successfully'
            else:
                return jsonify({'error': 'Order has not been filled yet'}), 400
    except Exception as e:
        # Log error
        app.logger.error(f'Error processing TradingView webhook: {e}')
        return 'Error processing TradingView webhook', 500


if __name__ == '__main__':
    app.run(debug=True)