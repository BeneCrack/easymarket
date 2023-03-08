from flask_security import RoleMixin, UserMixin
from database import db
from sqlalchemy.orm import relationship
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                       db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Bots(db.Model):
    __tablename__ = 'bots'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=False, nullable=False)
    order_type = db.Column(db.String(10), nullable=False)
    base_order_size = db.Column(db.Float, nullable=False)
    leverage = db.Column(db.Float, nullable=True)
    exchange = db.Column(db.String(50), nullable=False)
    symbol = db.Column(db.String(16), nullable=False)
    stop_loss = db.Column(db.Float, nullable=True)
    take_profit = db.Column(db.Float, nullable=True)
    description = db.Column(db.String(512), nullable=True)
    time_interval = db.Column(db.String(32), nullable=False)
    type = db.Column(db.String(15))
    exchange_id = db.Column(db.Integer, db.ForeignKey('exchanges.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    accounts = relationship('Accounts', back_populates='bots')
    signals = relationship('Signals', back_populates='bots')
    positions = relationship('Positions', back_populates='bots')
    botfees = db.relationship('BotFees', backref='bots', lazy=True)

    def __repr__(self):
        return f'<Bot {self.name}>'


class BotFees(db.Model):
    __tablename__ = 'botfees'
    id = db.Column(db.Integer, primary_key=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bots.id'), nullable=False)
    maker_fee = db.Column(db.Float)
    taker_fee = db.Column(db.Float)

    def __repr__(self):
        return f'<BotFees for Bot {self.bot_id}>'


class ExchangeModels(db.Model):
    __tablename__ = 'exchangemodels'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    short = db.Column(db.String(64), unique=True, nullable=False)

    accounts = relationship('Accounts', back_populates='exchangemodels')

    def __repr__(self):
        return f'<Exchanges {self.name}>'


class Accounts(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    exchange_id = db.Column(db.Integer, db.ForeignKey('exchanges.id'), nullable=False)
    api_key = db.Column(db.String(256), nullable=False)
    api_secret = db.Column(db.String(256), nullable=False)
    password = db.Column(db.String(256), nullable=True)
    options = db.Column(db.JSON, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    testnet = db.Column(db.Boolean())
    balance_usdt = db.Column(db.Float, nullable=True)
    balance_total = db.Column(db.Float, nullable=True)

    bots = relationship('Bots', back_populates='accounts')
    exchanges = relationship('ExchangeModels', back_populates='accounts')

    def __repr__(self):
        return f'<Account {self.name}>'


class Signals(db.Model):
    __tablename__ = 'signals'
    id = db.Column(db.Integer, primary_key=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bots.id'), nullable=False)
    exchange_id = db.Column(db.Integer, db.ForeignKey('exchanges.id'), nullable=False)
    symbol = db.Column(db.String(16), nullable=False)
    signal_type = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    bots = relationship('Bots', back_populates='signals')
    exchanges = relationship('ExchangeModels')

    def __repr__(self):
        return f'<Signal {self.signal_type} {self.symbol}>'


class Positions(db.Model):
    __tablename__ = 'positions'
    id = db.Column(db.Integer, primary_key=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bots.id'), nullable=False)
    symbol = db.Column(db.String(16), nullable=False)
    exchange_id = db.Column(db.Integer, db.ForeignKey('exchanges.id'), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False)
    exit_price = db.Column(db.Float, nullable=True)
    exit_time = db.Column(db.DateTime, nullable=True)
    order_id = db.Column(db.String(64), nullable=False)
    order_quantity = db.Column(db.Float, nullable=False)
    order_type = db.Column(db.String(10), nullable=False)
    position_type = db.Column(db.String(10), nullable=False)
    initial_stop_loss = db.Column(db.Float, nullable=True)
    exit_order_id = db.Column(db.String(64), nullable=True)
    stop_loss_order_id = db.Column(db.String(64), nullable=True)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    status = db.Column(db.String(10), nullable=False)
    fees = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    bots = relationship('Bots', back_populates='positions')
    exchanges = relationship('ExchangeModels', back_populates='positions')

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return f"<Position {self.signal_type} {self.symbol}>"


class Role(db.Model, RoleMixin):
    __tablename__ = 'role'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f"<Role {self.name}>"


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    bots = relationship('Bots', backref='user')
    accounts = relationship('Accounts', backref='user')
    signals = relationship('Signals', backref='user')
    positions = relationship('Positions', backref='user')

    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<User {self.email}>"
