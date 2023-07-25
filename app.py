# Libraries

# Flask app
from flask import Flask, render_template, request, Response, send_file

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
import io
import numpy as np
import base64


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


list_info_event = ['Andrea', # bride
                   'Santiago', # groom
                   12, # day
                   'junio', # month
                   2021, # year
                   'Xochitepec, Morelos' # place
                   ]

dict_info_recipients = {'+5215551078511':{'recipient_name':'Santiago', 'tickets':2},
                        # '+5215585308944':{'recipient_name':'Gerardo', 'tickets':2},
                        # '+5215585487594':{'recipient_name':'Fernanda', 'tickets':2},
                        # '+5215554186584':{'recipient_name':'Maru', 'tickets':2},
                        # '+5215537139718':{'recipient_name':'Pablo', 'tickets':2},
                        # '+5215544907299':{'recipient_name':'Andrea', 'tickets':2}
                        }

conversation_states = {}

intro = """Hola {recipient_name}:

De parte de {bride} y {groom} te extendemos la invitación para su boda que se celebrará el día {day} de {month} de {year} en {place}. Te agradeceríamos si nos pudieras confirmar tu asistencia"""

messages = [
    'De acuerdo. Vemos que cuentas con {tickets} {str_tickets}. Te agradeceríamos que nos confirmaras el número de invitados que estarían asistiendo a la boda'
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

        intro_formatted = intro.format(
            recipient_name=recipient_name,
            bride=list_info_event[0],
            groom=list_info_event[1],
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
        if current_question_index == 0:
            if dict_info_recipients[incoming_phone_number]['tickets'] > 1:
                str_tickets = 'boletos'
            else:
                str_tickets = 'boleto'
            next_message = next_message.format(tickets=dict_info_recipients[incoming_phone_number]['tickets'], str_tickets=str_tickets)

        time.sleep(2)
        response.message(next_message)

        current_question_index += 1
        conversation_state['current_question_index'] = current_question_index
    
    elif current_question_index == len(messages):
        # No more questions, end the conversation
        time.sleep(2)
        response.message(f'{dict_info_recipients[incoming_phone_number]["recipient_name"]}, agradecemos mucho tu tiempo y tu respuesta. Que tengas un buen día')
        
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
        response.message(f'{dict_info_recipients[incoming_phone_number]["recipient_name"]}, agradecemos mucho tu tiempo y tu respuesta. Que tengas un buen día')
        
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
        response.message(f'{dict_info_recipients[incoming_phone_number]["recipient_name"]}, agradecemos mucho tu tiempo y tu respuesta. Que tengas un buen día')

    # Update the conversation state in the global dictionary
    conversation_states[incoming_phone_number] = conversation_state

    return str(response)

@app.route('/view')
def view():
    infos = Information.query.all()
    return render_template('view.html', infos=infos)

@app.route('/export', methods=['POST'])
def export():
    infos = Information.query.all()

    # Create the CSV file
    with open('data.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['ID','Conversation_SID','Telefono','Respuesta_1','Respuesta_2']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for info in infos:
            writer.writerow({'ID':info.id,
                             'Conversation_SID':info.conversation_sid,
                             'Telefono':info.phone_number,
                             'Respuesta_1':info.answer_1,
                             'Respuesta_2':info.answer_2,
                             })

    # Send the CSV file as a response for download
    with open('data.csv', 'r', encoding='utf-8') as f:
        csv_data = f.read()

    response = Response(csv_data, mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename='data.csv')

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

@app.route('/plot', methods=['GET'])
def plot():
    # Extract distinct answer_1 values and their counts from the database
    answer_1_values = [info.answer_1 for info in Information.query.all()]
    unique_values, value_counts = np.unique(answer_1_values, return_counts=True)

    # Create a bar plot for Answer 1 using Matplotlib
    plt.figure(figsize=(8, 6))
    plt.bar(unique_values, value_counts)
    plt.xlabel('Answer 1 Value')
    plt.ylabel('Count')
    plt.title('Answer 1 Value Counts')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the Answer 1 plot to a bytes buffer
    buffer1 = io.BytesIO()
    plt.savefig(buffer1, format='png')
    buffer1.seek(0)
    plt.close()

    # Extract distinct answer_2 values and their sums from the database
    answer_2_values = [info.answer_2 for info in Information.query.all()]
    unique_values2, value_sums = np.unique(answer_2_values, return_counts=False)

    # Create a bar plot for Answer 2 using Matplotlib
    plt.figure(figsize=(8, 6))
    plt.bar(unique_values2, value_sums)
    plt.xlabel('Answer 2 Value')
    plt.ylabel('Sum')
    plt.title('Answer 2 Value Sums')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the Answer 2 plot to a bytes buffer
    buffer2 = io.BytesIO()
    plt.savefig(buffer2, format='png')
    buffer2.seek(0)
    plt.close()

    # Convert plots to base64 encoded strings
    plot1_base64 = base64.b64encode(buffer1.read()).decode()
    plot2_base64 = base64.b64encode(buffer2.read()).decode()

    # Return the plots as base64-encoded images
    return render_template('plot.html', plot1_base64=plot1_base64, plot2_base64=plot2_base64)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
