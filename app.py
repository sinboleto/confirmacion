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
# account_sid = os.environ.get('ACCOUNT_SID')
# auth_token = os.environ.get('AUTH_TOKEN')
# twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')

account_sid = 'ACf01ddcd618830097852506cba7b428ef'
auth_token = '1b36553f5486a232a6edfa04db76cc66'
twilio_phone_number = '+12058391586'

# Create Twilio client
client = Client(account_sid, auth_token)


class Information(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    info = db.Column(db.String(500), nullable=False)

    def __init__(self, id, info):
        self.id = id
        self.info = info

# Inicio conversación
@app.route('/start', methods=['GET'])
def inicio_conversacion():
    
    message = client.messages.create(
        from_ = f'whatsapp:{twilio_phone_number}',
        body = 'Hola',
        to = 'whatsapp:+5215551078511'
        )
    
    return 'Inicio'


@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':

        incoming_message = request.values
        incoming_message_body = request.values.get('Body', '').lower()

        response = MessagingResponse()
        texto_respuesta = f'Tu mensaje: "{incoming_message_body}"'
        response.message(texto_respuesta)

        new_info = Information(id, str(incoming_message))
        db.session.add(new_info)
        db.session.commit()

        print(str(incoming_message))

        return str(response)
    
    else:

        return 'Inicio exitoso'

@app.route('/view')
def view():
    infos = Information.query.all()
    return render_template('view.html', infos=infos)

@app.route('/export', methods=['POST'])
def export():
    infos = Information.query.all()

    # Create the CSV file
    with open('data.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['ID', 'Information']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for info in infos:
            writer.writerow({'ID': info.id, 'Information': info.info})

    # Send the CSV file as a response for download
    with open('data.csv', 'r', encoding='utf-8') as f:
        csv_data = f.read()

    response = Response(csv_data, mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename='data.csv')

    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
