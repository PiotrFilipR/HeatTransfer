from flask import Flask, flash, redirect, url_for, request, render_template
import math
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = b'21354245346asd]]]]1]]]]/////2qwe1234'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    first_name = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(20))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'{self.__class__.__name__} - {self.id} {self.username}'


with app.app_context():
    db.create_all()

SCREED_CONDUCTIVITY = 1.4
HEAT_RESISTANCE_COEFFICIENT = 0.0926

thermal_output = 0


@app.route('/', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username_input = request.form['username']
        password_input = request.form['password']
        with app.app_context():
            logged = db.session.query(Users).filter(Users.username == username_input).first()
            if logged:
                if db.session.query(Users).filter(Users.password == password_input).first():
                    login_user(logged)
                    flash(f'Logged in. You can go to main page now.')
                else:
                    flash(f'Password incorrect.')
            else:
                flash(f'User does not exist')
    return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash("You've been logged out.")
    return redirect(url_for('login'))


@app.route('/account/register', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        user = Users(username=request.form['username'],
                     first_name=request.form['first_name'],
                     password=request.form['password'],
                     email=request.form['email'])
        with app.app_context():
            db.session.add(user)
            db.session.commit()
        with app.app_context():
            db.create_all()
        Users.query.order_by(Users.date_added)
        flash(f'Successfully created account. You can get back to main page and log in. ')
    return render_template("create_account.html")


@app.route('/main', methods=['POST', 'GET'])
@login_required
def main_screen():
    global thermal_output

    if request.method == 'POST':
        temp_above = float(request.form['temp_above'])
        temp_below = float(request.form['temp_below'])
        supply_temp = float(request.form['supply_temp'])
        return_temp = float(request.form['return_temp'])
        pipe_ext_diameter = float(request.form['pipe_ext_diameter'])
        screed = float(request.form['screed']) * 0.001
        pipe_spacing = float(request.form['pipe_spacing'])
        floor_covering_resistance = float(request.form['floor_covering_resistance'])

        # Delta_t calculation

        temp = supply_temp - return_temp
        temp2 = supply_temp - temp_above
        temp3 = return_temp - temp_above
        delta_temperature = temp / (math.log(temp2 / temp3))

        # a modules calculation

        upward_heat_trans_Ro = HEAT_RESISTANCE_COEFFICIENT + (
                screed / SCREED_CONDUCTIVITY) + floor_covering_resistance
        floor_covering_factor = (HEAT_RESISTANCE_COEFFICIENT + screed) / upward_heat_trans_Ro

        mt = 1 - pipe_spacing / 0.075
        if 0 < floor_covering_resistance <= 0.05:
            spacing_factor_m = 1.188
        elif 0.05 < floor_covering_resistance <= 0.1:
            spacing_factor_m = 1.156
        elif floor_covering_resistance == 0.0:
            spacing_factor_m = 1.23
        spacing_factor = math.pow(spacing_factor_m, mt)

        mu = 100 * (0.045 - screed)
        covering_factor = math.pow(1.040, mu)

        md = 250 * (pipe_ext_diameter - 0.020)
        diameter_factor = math.pow(1.038, md)

        # B - system coefficient - uproszczone dla rur 16x2,0 i 20x2,0

        system_coefficient = 6.7

        # Thermal output

        thermal_output = system_coefficient * floor_covering_factor * spacing_factor * covering_factor * \
                         diameter_factor * delta_temperature

        return redirect(url_for('result'))

    return render_template('main.html')


@app.route('/result', methods=['POST', 'GET'])
@login_required
def result():
    if request.method == 'POST':
        return redirect(url_for('main_screen'))

    return render_template('result.html',
                           thermal_output=round(thermal_output, 2))


if __name__ == '__main__':
    app.run(debug=True)
