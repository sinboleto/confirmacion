import csv
from flask import Flask, render_template, request, Response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

from dotenv import load_dotenv
import os

app = Flask(__name__)

port = int(os.environ.get('PORT', 5000))

# Variables base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Load environment variables from .env file
load_dotenv()

# Twilio credentials
account_sid = os.environ.get('ACCOUNT_SID')
auth_token = os.environ.get('AUTH_TOKEN')
twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')

# Create Twilio client
client = Client(account_sid, auth_token)


class Information(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # name = db.Column(db.String(50))
    # email = db.Column(db.String(50))
    info = db.Column(db.String(500))

    def __init__(self, id, info):
        self.id = id
        self.info = info
        # self.email = email

# Inicio conversación
@app.route('/start', methods=['GET'])
def inicio_conversacion():
    response = MessagingResponse()
    response.message('Hola')
    return str(response)


@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':

        # incoming_message = request.values.get('Body', '').lower()
        incoming_message = request.values
        response = MessagingResponse()

        new_info = Information(id, incoming_message)
        db.session.add(new_info)
        db.session.commit()

        return str(response)
    
    else:

        return 'Inicio exitoso'

# @app.route('/input', methods=['GET', 'POST'])
# def index():
#     if request.method == 'POST':
#         name = request.form['name']
#         email = request.form['email']

#         new_info = Information(id, name, email)
#         db.session.add(new_info)
#         db.session.commit()

#     infos = Information.query.all()

#     return render_template('index.html', infos=infos)

@app.route('/view')
def view():
    infos = Information.query.all()
    return render_template('view.html', infos=infos)

# @app.route('/export', methods=['POST'])
# def export():
#     infos = Information.query.all()

#     # Create the CSV file
#     with open('data.csv', 'w', newline='') as csvfile:
#         writer = csv.writer(csvfile)
#         writer.writerow(['ID','Name', 'Email'])
#         for info in infos:
#             writer.writerow([info.id, info.name, info.email])

#     # Send the CSV file as a response for download
#     with open('data.csv', 'r') as f:
#         csv_data = f.read()

#     response = Response(csv_data, mimetype='text/csv')
#     response.headers.set('Content-Disposition', 'attachment', filename='data.csv')
    
#     return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
