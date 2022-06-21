import os

from dotenv import load_dotenv
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy

load_dotenv()  # take environment variables from .env.

app = Flask(__name__)

Bootstrap(app)

ckeditor = CKEditor(app)

moment = Moment(app)

mail = Mail(app)

app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///elephant_raiser.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)

stripe_keys = {
    'publishable_key': os.environ['STRIPE_PUBLISHABLE_KEY'],
    'secret_key': os.environ['STRIPE_SECRET_KEY'],
    'endpoint_secret': os.environ['STRIPE_ENDPOINT_SECRET']
}


gmail = {
    'address': os.environ['GMAIL_ADDRESS'],
    'password': os.environ['GMAIL_PASSWORD']
}

from elephant_raiser import routes
