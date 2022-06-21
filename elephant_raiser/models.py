import smtplib

from flask_login import UserMixin

from elephant_raiser import db, bcrypt, gmail


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, nullable=False, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(100))
    elephants = db.relationship(lambda: ElephantRaiser, backref='raiser', lazy=True)

    @property
    def password(self):
        return self.password

    @password.setter
    def password(self, plaintext_password):
        self.password_hash = bcrypt.generate_password_hash(plaintext_password).decode('utf-8')

    def check_password_correction(self, attempted_password):
        return bcrypt.check_password_hash(self.password_hash, attempted_password)


class Elephant(db.Model):
    __tablename__ = 'elephant'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    affiliation = db.Column(db.String(50), nullable=False)
    species = db.Column(db.String(10), nullable=False)
    sex = db.Column(db.String(10), nullable=False)
    wikilink = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    note = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    price_id = db.Column(db.String(30), nullable=False)
    raisers = db.relationship(lambda: ElephantRaiser, backref='elephant', lazy=True)

    def __repr__(self):
        return f'Elephant {self.name}'


class ElephantRaiser(db.Model):
    __tablename__ = 'elephant_raiser'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    raiser_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    elephant_id = db.Column(db.Integer, db.ForeignKey('elephant.id'))


# db.create_all()


def send_email(name, email, subject, message):
    info = f"Subject: {subject}\n\n" \
           f"Name: {name}\n" \
           f"Email: {email}\n" \
           f"Message: {message}"
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(gmail['address'], gmail['password'])
        connection.sendmail(
            from_addr=gmail['address'],
            to_addrs=gmail['address'],
            msg=info
        )

# stripe.api_key = stripe_keys['secret_key']
# response = requests.get('https://elephant-api.herokuapp.com/elephants')
# elephants = response.json()
# for elephant in elephants:
#     try:
#         check = Elephant.query.filter_by(name=elephant['name']).first()
#         if 'miss' not in elephant['image'] and not check:
#             random_price = random.randint(10,19)
#             product = stripe.Product.create(
#                 name=elephant['name'],
#                 images=[elephant['image']],
#                 description=elephant['note']
#             )
#             price = stripe.Price.create(
#                 currency='usd',
#                 unit_amount=random_price * 100,
#                 product=product['id']
#             )
#             elephant_item = Elephant(
#                 name=elephant['name'],
#                 affiliation=elephant['affiliation'],
#                 species=elephant['species'],
#                 sex=elephant['sex'],
#                 wikilink=elephant['wikilink'],
#                 image=elephant['image'],
#                 note=elephant['note'],
#                 price=random_price,
#                 price_id=price['id']
#             )
#             db.session.add(elephant_item)
#             db.session.commit()
#     except KeyError:
#         break
