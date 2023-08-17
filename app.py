# Libraries

# Flask app
from flask import Flask, render_template, request, Response

# Database
import csv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Twilio
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

# System
from dotenv import load_dotenv
import os

# Delay
import time

# Graph
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
import numpy as np
import base64

import json


# Main script
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
conversations_sid = os.environ.get('CONVERSATIONS_SERVICE_SID')
twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')
app.secret_key = os.environ.get('APP_SECRET_KEY')
messaging_service_sid = os.environ.get('MESSAGING_SERVICE_SID')

# Create Twilio client
client = Client(account_sid, auth_token)

# Twilio Conversations API client
conversations_client = client.conversations.v1.services(conversations_sid)


class Information(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_sid = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(20), nullable=False)
    answer_1 = db.Column(db.String(500), nullable=False)
    answer_2 = db.Column(db.String(500), nullable=False)

    def __init__(self, conversation_sid, name, phone_number, answer_1, answer_2):
        self.conversation_sid = conversation_sid
        self.name = name
        self.phone_number = phone_number
        self.answer_1 = answer_1
        self.answer_2 = answer_2


# Model inputs
global intro
global messages
global recipient_phone_numbers
global list_info_event
global dict_info_recipients
global conversation_states


# list_info_event = ['Andrea',  # bride
#                    'Santiago',  # groom
#                    12,  # day
#                    'junio',  # month
#                    2021,  # year
#                    'Xochitepec, Morelos'  # place
#                    ]

list_info_event = ['Sin Boleto',  # organizer
                   'Presentación Sin Boleto',  # event_name
                   17,  # day
                   'agosto',  # month
                   2023,  # year
                   'Salón Francés, Ambrosía',  # place
                   '4:30 pm',  # time
                   'Ambrosía',  # venue
                   'Periferico Sur 3395, Rincón del Pedregal, Tlalpan, 14120 Ciudad de México, CDMX',  # address
                   'https://g.co/kgs/WxioUL',  # address_link
                   'https://wa.link/c4ju15'  # contact_link
                   ]

dict_info_recipients = {'+5215551078511': {'recipient_ID':'AMB_170823_004', 'recipient_name': 'Santiago'},
                        # '+5215585308944': {'recipient_name': 'Gerardo', 'tickets': 2},
                        # '+5215585487594':{'recipient_name':'Fernanda', 'tickets':2},
                        # '+5215554186584':{'recipient_name':'Maru', 'tickets':2},
                        # '+5215537139718':{'recipient_name':'Pablo', 'tickets':2},
                        # '+5215544907299':{'recipient_name':'Andrea', 'tickets':2}
                        }

conversation_states = {}

# intro = """Hola {recipient_name}:

# De parte de {bride} y {groom} te extendemos la invitación para su boda que se celebrará el día {day} de {month} de {year} en {place}. Te agradeceríamos si nos pudieras confirmar tu asistencia"""

intro = """Hola {recipient_name}:

De parte de {organizer} te extendemos la invitación para el evento {event_name} que se realizará el día {day} de {month} de {year} en {place}. Te agradeceríamos si nos pudieras confirmar tu asistencia"""

messages = [
    # 'De acuerdo. Vemos que cuentas con {tickets} {str_tickets}. Te agradeceríamos que nos confirmaras el número de invitados que estarían asistiendo a la boda',
    # 'De acuerdo. Vemos que cuentas con {tickets} {str_tickets}. Te agradeceríamos que nos confirmaras el número de invitados que asistirán al evento'
    'De acuerdo. Te compartimos tu boleto con código QR de acceso, el cual les permitirá ingresar de manera ágil y segura al evento. Les solicitamos amablemente que tengan el código QR listo en su dispositivo móvil el día del evento, para facilitar el proceso de ingreso. ¿Lo recibiste?'
]

# Inicio conversación


@app.route('/start', methods=['GET'])
def inicio_conversacion():
    global intro
    global conversation_states

    for recipient_phone_number in dict_info_recipients:

        conversation = conversations_client.conversations.create()
        app.logger.info(conversation.sid)

        # Get the recipient_name dynamically for each recipient_phone_number
        recipient_name = dict_info_recipients[recipient_phone_number]['recipient_name']

        # intro_formatted = intro.format(
        #     recipient_name=recipient_name,
        #     bride=list_info_event[0],
        #     groom=list_info_event[1],
        #     day=list_info_event[2],
        #     month=list_info_event[3],
        #     year=list_info_event[4],
        #     place=list_info_event[5])

        intro_formatted = intro.format(
            recipient_name=recipient_name,
            organizer=list_info_event[0],
            event_name=list_info_event[1],
            day=list_info_event[2],
            month=list_info_event[3],
            year=list_info_event[4],
            place=list_info_event[5])

        message = client.messages.create(
            messaging_service_sid=messaging_service_sid,
            from_=f'whatsapp:{twilio_phone_number}',
            body=intro_formatted,
            to=f'whatsapp:{recipient_phone_number}'
        )

        # Store the conversation SID and initial state for each recipient
        conversation_states[recipient_phone_number] = {
            'conversation_sid': conversation.sid,
            'recipient_ID': dict_info_recipients[recipient_phone_number]['recipient_ID'], 
            'current_question_index': 0,
            'answers': [],
        }

    app.logger.info(conversation_states)

    return 'Inicio'


@app.route('/', methods=['POST'])
def webhook():

    incoming_message_body = request.values.get('Body', '').lower()
    incoming_phone_number = request.values.get('From', '').lower()
    incoming_phone_number = incoming_phone_number.replace('whatsapp:', '')

    app.logger.info(incoming_phone_number)

    # Get the conversation state for the current recipient
    conversation_state = conversation_states.get(incoming_phone_number, None)

    if not conversation_state:
        app.logger.info('Invalid recipient phone number')
        return 'Invalid recipient phone number'

    response = MessagingResponse()

    # Get the user's answer
    user_answer = str(incoming_message_body)

    # Get the conversation SID
    conversation_sid = conversation_state['conversation_sid']

    # Get recepient_ID
    recepient_ID = conversation_state['recipient_ID']

    # Append the answer to the conversation state
    conversation_state['answers'].append(user_answer)

    current_question_index = conversation_state['current_question_index']

    if current_question_index == 0 and user_answer == 'no':
        current_question_index = -1
        conversation_state['answers'].append(0)

    app.logger.info(f'current_question_index:{current_question_index}')

    if current_question_index >= 0 and current_question_index < len(messages):
        # Ask the next question
        next_message = messages[current_question_index]

        # Autocomplete messages with personalized information
        # if current_question_index == 0:
        #     if dict_info_recipients[incoming_phone_number]['tickets'] > 1:
        #         str_tickets = 'boletos'
        #     else:
        #         str_tickets = 'boleto'
        #     next_message = next_message.format(
        #         tickets=dict_info_recipients[incoming_phone_number]['tickets'], str_tickets=str_tickets)

        time.sleep(2)
        # response.message(next_message)

        content_SID = 'HXfd44cf82c32f0bd4ee0b96fc249fc1fb'  # Revisar

        content_variables = json.dumps({'1': recepient_ID})

        message = client.messages.create(
            messaging_service_sid=messaging_service_sid,
            from_=f'whatsapp:{twilio_phone_number}',
            content_sid=content_SID,
            content_variables=content_variables,
            to=f'whatsapp:{incoming_phone_number}',
        )
        
        message = client.messages.create(
            messaging_service_sid=messaging_service_sid,
            from_=f'whatsapp:{twilio_phone_number}',
            body=next_message,
            to=f'whatsapp:{incoming_phone_number}'
        )

        # time.sleep(0.25)
        current_question_index += 1
        conversation_state['current_question_index'] = current_question_index

    elif current_question_index == 1 and user_answer == 'no':
        message = client.messages.create(
            messaging_service_sid=messaging_service_sid,
            from_=f'whatsapp:{twilio_phone_number}',
            body='En un momento te reenviaremos el boleto por este medio',
            to=f'whatsapp:{incoming_phone_number}'
        )

    elif current_question_index == len(messages):
        # No more questions, end the conversation
        date = f'{list_info_event[2]} de {list_info_event[3]} de {list_info_event[4]}'

        time.sleep(2)
        response.message(
            f"""Finalmente, te compartimos la información general del evento:
Fecha y hora de inicio: {date} a las {list_info_event[6]}
Lugar: {list_info_event[7]}
Dirección: {list_info_event[8]} - {list_info_event[9]}""")

        time.sleep(2)
        response.message(
            f'{dict_info_recipients[incoming_phone_number]["recipient_name"]}, agradecemos mucho tu tiempo y tu respuesta. Que tengas un buen día')

        answers = [str(answer) for answer in conversation_state['answers']]

        # We have asked all the question, save the answer in the database
        new_info = Information(conversation_sid,
                               dict_info_recipients[incoming_phone_number]["recipient_name"],
                               incoming_phone_number,
                               answers[0],
                               answers[1])
        db.session.add(new_info)
        db.session.commit()

        current_question_index += 1
        conversation_state['current_question_index'] = current_question_index

    elif current_question_index == -1:
        time.sleep(2)
        response.message(
            f'{dict_info_recipients[incoming_phone_number]["recipient_name"]}, agradecemos mucho tu tiempo y tu respuesta. Que tengas un buen día')

        answers = [str(answer) for answer in conversation_state['answers']]
        # We have asked all the question, save the answer in the database
        new_info = Information(conversation_sid,
                               dict_info_recipients[incoming_phone_number]["recipient_name"],
                               incoming_phone_number,
                               answers[0],
                               answers[1])
        db.session.add(new_info)
        db.session.commit()

    else:
        time.sleep(2)
        response.message(
            f'Hola, soy un chatbot y estoy programado para hacer confirmaciones y brindar información general del evento. Cualquier otra duda, favor de comunicarse a este teléfono: {list_info_event[10]}. Gracias')

    # Update the conversation state in the global dictionary
    conversation_states[incoming_phone_number] = conversation_state

    return str(response)


@app.route('/dashboard')
def view():
    infos = Information.query.all()

    # Extract distinct answer_1 values and their counts from the database
    answer_1_values = [info.answer_1 for info in infos]
    unique_values, value_counts = np.unique(
        answer_1_values, return_counts=True)

    if len(answer_1_values) < 1:
        value_counts = 0

    # Create a bar plot for Answer 1 using Matplotlib
    colors = ['green' if value == 'si' else 'red' for value in unique_values]

    plt.figure()
    plt.bar(unique_values, value_counts, color=colors)
    plt.xlabel('Value')
    plt.ylabel('Count')
    plt.title('Confirmation distribution')
    plt.xticks()
    # plt.yticks(np.arange(0,
    #            int(max(value_counts)) + 1, 1))
    plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.0f}'))

    # Save the plot to a bytes buffer and encode it in base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    plot1_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Extract distinct answer_2 values and their counts from the database
    answer_2_values = [info.answer_2 for info in infos]
    unique_values, value_counts = np.unique(
        answer_2_values, return_counts=True)

    if len(answer_2_values) < 1:
        value_counts = 0

    # Create a bar plot for Answer 1 using Matplotlib
    colors = ['green' if value == 'si' else 'red' for value in unique_values]

    plt.figure()
    plt.bar(unique_values, value_counts, color=colors)
    plt.xlabel('Value')
    plt.ylabel('Count')
    plt.title('Ticket reception distribution')
    plt.xticks()
    # plt.yticks(np.arange(0,
    #            int(max(value_counts)) + 1, 1))
    plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.0f}'))

    # Save the plot to a bytes buffer and encode it in base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    plot2_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Extract distinct answer_2 values and their sums from the database
    # answer_2_values = [int(info.answer_2) for info in infos]

    # if len(answer_2_values) > 0:
    #     value_sums = sum(answer_2_values)
    # else:
    #     value_sums = 0

    # # Create a bar plot for Answer 2 using Matplotlib
    # plt.figure()
    # plt.bar(0, value_sums)
    # plt.xlabel('Value')
    # plt.ylabel('Sum')
    # plt.title('Total confirmations')
    # plt.xticks([])
    # # plt.yticks(np.arange(0, int(max(value_sums)) + 1, 1))
    # plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.0f}'))

    # # Save the plot to a bytes buffer and encode it in base64
    # buffer2 = io.BytesIO()
    # plt.savefig(buffer2, format='png')
    # buffer2.seek(0)
    # plt.close()
    # plot2_base64 = base64.b64encode(buffer2.getvalue()).decode()

    return render_template('view.html', infos=infos, plot1_base64=plot1_base64, plot2_base64=plot2_base64)
    # return render_template('view.html', infos=infos, plot1_base64=plot1_base64)


@app.route('/export', methods=['POST'])
def export():
    infos = Information.query.all()

    # Create the CSV file
    with open('data.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['ID', 'Conversation_SID',
                      'Telefono', 'Respuesta_1', 'Respuesta_2']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for info in infos:
            writer.writerow({'ID': info.id,
                             'Conversation_SID': info.conversation_sid,
                             'Telefono': info.phone_number,
                             'Respuesta_1': info.answer_1,
                             'Respuesta_2': info.answer_2,
                             })

    # Send the CSV file as a response for download
    with open('data.csv', 'r', encoding='utf-8') as f:
        csv_data = f.read()

    response = Response(csv_data, mimetype='text/csv')
    response.headers.set('Content-Disposition',
                         'attachment', filename='data.csv')

    return response


@app.route('/delete_information', methods=['POST'])
def delete_information():
    # Open a new SQLAlchemy session
    session_db = db.session

    # Delete all records from the Information table
    session_db.query(Information).delete()

    # Commit the changes to the database
    session_db.commit()

    return 'Database information has been deleted successfully'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
