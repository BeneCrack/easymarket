import json
from datetime import datetime
import ccxt
from flask import Markup, flash, request, Flask, render_template, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required
from flask_sqlalchemy import SQLAlchemy
from classes.exchange2 import Exchange
from classes.models import ExchangeModel, Bots, Accounts, Signals, Positions, Role, User

app = Flask(__name__)

# Load configuration from environment variable
app.config.from_envvar('APP_CONFIG')

# Create an exchange client
exchange = Exchange(app.config['EXCHANGE_NAME'], app.config['API_KEY'], app.config['API_SECRET'])

app.config.from_envvar('APP_CONFIG')
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


# Get bot configuration from the database
def get_bot_config(bot_id):
    bot = Bots.query.filter_by(id=bot_id).first()
    if not bot:
        return None
    return {
        'bot_type': bot.type,           # WHY IS BOT TYPE TESTNET
        'amount': bot.amount,
        'pair': bot.pair
    }

# Get the exchange client for the bot
def get_exchange_client(bot_id):
    bot_config = get_bot_config(bot_id)
    if not bot_config:
        return None
    exchange.set_testnet(bot_config['bot_type'] == 'testnet')       # SET TESTNET DOESNT EXIST
    return exchange

# Get the current position for the bot
def get_position(bot_id):
    return Positions.query.filter_by(bot_id=bot_id).first()

# Calculate the order amount based on the bot's configured amount
def calculate_order_amount(bot_config, position):
    if not bot_config or not position:
        return None
    return int(bot_config['amount'] * position.capital / 100)       # ORDER AMOUNT SHOULD BE pp percent of portfolio


def update_position(bot_id, order_id, status, amount, price, timestamp):
    """
    Update the status of a position in the database
    """
    bot = Bots.query.filter_by(id=bot_id).first()
    if not bot:
        raise ValueError(f'Bot "{bot.name}" not found')
    position = Positions.query.filter_by(bot_id=bot.id, order_id=order_id).first()
    if not position:
        raise ValueError(f'Position with order ID "{order_id}" not found')

    position.status = status
    position.amount = amount
    position.price = price
    position.closed_at = timestamp

    position.close_price = price
    position.close_quantity = amount
    position.fees = amount * price * bot.fee_rate
    db.session.commit()

def create_order(exchange_client, bot, quantity, price=None):
    try:
        if price is not None:
            order = exchange_client.create_order(
                symbol=bot.pair,
                side=bot.side,
                type=bot.type,
                timeInForce='GTC',
                quantity=quantity,
                price=price
            )
        else:
            order = exchange_client.create_order(
                symbol=bot.pair,
                side=bot.side,
                type=bot.type,
                timeInForce='GTC',
                quantity=quantity
            )

        # Update positions table with order details
        if bot.side == 'BUY':
            position_entry = Positions(
                bot_id=bot.id,
                symbol=bot.pair,
                order_type=bot.type,
                order_id=order['orderId'],
                open_time=order['transactTime'],
                order_price=order['price'],
                order_quantity=order['origQty'],
                stop_loss=None,
                take_profit=None,
                status='OPEN'
            )
            db.session.add(position_entry)
        else:
            position = Positions.query.filter_by(
                bot_id=bot.id,
                symbol=bot.pair,
                status='OPEN'
            ).first()
            if position:
                position.order_type = bot.type
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
        exchange_client = get_exchange_client(bot.exchange)
        if not exchange_client:
            return jsonify({'error': 'Invalid bot configuration'}), 400
        position = get_position(bot.id)
        if not position:
            return jsonify({'error': f'Position for bot "{bot.name}" not found'}), 404
        order_amount = calculate_order_amount(bot, position)
        if not order_amount:
            return jsonify({'error': 'Unable to calculate order amount'}), 400
        if signal.startswith('ENTER-LONG'):
            order_type = bot.order_type
            pair = bot.pair
            side = 'BUY'
            quantity = order_amount
            order = create_order(exchange_client, order_type, pair, side, quantity)
            if not order:
                return jsonify({'error': 'Unable to create order'}), 500
            stop_loss = bot.stop_loss
            take_profit = bot.take_profit
            update_position(bot.id, order['orderId'], 'long', order_amount, order['price'], datetime.now(), stop_loss,
                            take_profit)
            return jsonify({'message': 'Long position created successfully'}), 200
        elif signal.startswith('EXIT-LONG'):
            position = get_position(bot.id)
            if not position:
                return jsonify({'error': f'Position for bot "{bot.name}" not found'}), 404
            order = exchange_client.get_order(position.exchange_order_id)
            if not order:
                return jsonify({'error': 'Unable to get order details'}), 500
            if order['status'] == 'FILLED':
                order_type = bot.order_type
                pair = bot.pair
                side = 'SELL'
                quantity = order_amount
                if order_type == 'LIMIT':
                    price = float(order['price'])
                else:
                    price = None
                order = create_order(exchange_client, order_type, pair, side, quantity, price)
                update_position(bot.id, order['orderId'], 'closed', order_amount, order['price'], datetime.now())
                return 'Order created successfully'
            else:
                return jsonify({'error': 'Order has not been filled yet'}), 400
        elif signal.startswith('ENTER-SHORT'):
            order_type = bot.order_type
            pair = bot.pair
            side = 'SELL'
            quantity = order_amount
            order = create_order(exchange_client, order_type, pair, side, quantity)
            if not order:
                return jsonify({'error': 'Unable to create order'}), 500
            stop_loss = bot.stop_loss
            take_profit = bot.take_profit
            update_position(bot.id, order['orderId'], 'short', order_amount, order['price'], datetime.now(), stop_loss,
                            take_profit)
            return jsonify({'message': 'Short position created successfully'}), 200
        elif signal.startswith('EXIT-SHORT'):
            position = get_position(bot.id)
            if not position:
                return jsonify({'error': f'Position for bot "{bot.name}" not found'}), 404
            order = exchange_client.get_order(position.exchange_order_id)
            if not order:
                return jsonify({'error': 'Unable to get order details'}), 500
            if order['status'] == 'FILLED':
                order_type = bot.order_type
                pair = bot.pair
                side = 'BUY'
                quantity = order_amount
                if order_type == 'LIMIT':
                    price = float(order['price'])
                else:
                    price = None
                order = create_order(exchange_client, order_type, pair, side, quantity, price)
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
    #app.app_context().push()
    #db.drop_all()
    #db.create_all()

    #Accounts.__table__.columns.user_id.unique = False
    app.run(debug=True)