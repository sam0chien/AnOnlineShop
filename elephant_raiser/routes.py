from functools import wraps

import stripe
from flask import abort, request, jsonify
from flask import render_template, redirect, url_for, flash, session
from flask_login import login_user, login_required, current_user, logout_user
from iteration_utilities import unique_everseen

from elephant_raiser import app, db, login_manager, stripe_keys
from elephant_raiser.form import RegisterForm, LoginForm, ContactForm
from elephant_raiser.models import Elephant, User, ElephantRaiser, send_email

stripe.api_key = stripe_keys["secret_key"]


def admin_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return func(*args, **kwargs)

    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/browse')
def browse():
    elephants = Elephant.query.all()
    return render_template('browse.html', elephants=elephants)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User(username=form.username.data,
                        email=form.email.data,
                        password=form.password.data)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash(f'Thank you for joining Elephant Donator!', category='success')
        return redirect(url_for('home'))
    else:
        for err_msg in form.errors.values():
            err_msg = ''.join(err_msg)
            flash(err_msg, category='danger')
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        attempted_user = User.query.filter_by(username=form.username.data).first()
        if attempted_user and attempted_user.check_password_correction(attempted_password=form.password.data):
            login_user(attempted_user)
            flash(f'Success! You are log in as {attempted_user.username}.', category='success')
            return redirect(url_for('home'))
        else:
            flash('Username and password are not matched! Please try again.', category='danger')
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', category='success')
    return redirect(url_for('home'))


@app.route("/config")
def get_publishable_key():
    stripe_config = {"public_key": stripe_keys["publishable_key"]}
    return jsonify(stripe_config)


@app.route("/create-checkout-session")
@login_required
def create_checkout_session():
    elephants = session['raise_list']
    line_items = []
    for elephant in elephants:
        line_items.append({'price': elephant['price_id'], "quantity": 1, })
    stripe.api_key = stripe_keys["secret_key"]
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            success_url=url_for('success', _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for('cancel', _external=True),
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items
        )
        return jsonify({"sessionId": checkout_session["id"]})
    except Exception as e:
        return jsonify(error=str(e)), 403


@app.route('/success')
@login_required
def success():
    try:
        elephants = session['raise_list']
        for elephant in elephants:
            elephant_object = Elephant.query.get(elephant['id'])
            elephant_raiser = ElephantRaiser(raiser=current_user,
                                             elephant=elephant_object)
            db.session.add(elephant_raiser)
        db.session.commit()
        session.pop('raise_list', None)
        return render_template('success.html')
    except KeyError:
        flash("You don't have elephant in your raise list.", category='info')
        return redirect(url_for('raise_list'))


@app.route('/cancel')
@login_required
def cancel():
    return render_template('cancel.html')


@app.route("/webhook", methods=["POST"])
@login_required
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, stripe_keys["endpoint_secret"])
    except ValueError as e:
        # Invalid payload
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return "Invalid signature", 400

    # Handle the checkout.session.completed event
    if event["type"] == "checkout.session.completed":
        print("Payment was successful.")

    return "Success", 200


@app.route('/add-to-raise-list/<int:elephant_id>')
@login_required
def add_to_raise_list(elephant_id):
    elephant = Elephant.query.get(elephant_id)
    if 'raise_list' not in session:
        session['raise_list'] = []
    session['raise_list'].append({'id': elephant.id,
                                  'name': elephant.name,
                                  'image': elephant.image,
                                  'price': elephant.price,
                                  'price_id': elephant.price_id})
    session['raise_list'] = list(unique_everseen(session['raise_list']))
    flash(f'{elephant.name} is added to your raise list.', category='success')
    return redirect(url_for('browse'))


@app.route('/remove-from-raise-list/<int:elephant_id>')
@login_required
def remove_from_raise_list(elephant_id):
    elephant = Elephant.query.get(elephant_id)
    session['raise_list'].remove({'id': elephant.id,
                                  'name': elephant.name,
                                  'image': elephant.image,
                                  'price': elephant.price,
                                  'price_id': elephant.price_id})
    flash(f'{elephant.name} is removed from your raise list.', category='success')
    return redirect(url_for('raise_list'))


@app.route('/raise-list')
@login_required
def raise_list():
    if 'raise_list' not in session or session['raise_list'] == []:
        return render_template('raise-list.html', is_raised=False)
    else:
        elephants = session['raise_list']
        total_elephants = len(elephants)
        total_amount = 0
        for elephant in elephants:
            total_amount += elephant['price']
    return render_template('raise-list.html', elephants=elephants,
                           total_elephants=total_elephants, total_amount=total_amount, is_raised=True)


@app.route('/info')
@login_required
def info():
    raised_elephants = ElephantRaiser.query.filter_by(raiser_id=current_user.id).all()
    if raised_elephants:
        return render_template('info.html', raised_elephants=raised_elephants, is_raised=True)
    else:
        return render_template('info.html', is_raised=False)


@app.route('/contact', methods=["POST", "GET"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        send_email(form.name.data, form.email.data, form.subject.data, form.message.data)
        flash(f'Thank you for contacting us! We will reply back as soon as possible', category='success')
        return redirect(url_for('contact'))
    else:
        for err_msg in form.errors.values():
            err_msg = ''.join(err_msg)
            flash(err_msg, category='danger')
    return render_template('contact.html', form=form)
