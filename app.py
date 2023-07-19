import csv
from flask import Flask, render_template, request, Response, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

from dotenv import load_dotenv
import os

import time
import json

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

# Create Twilio client
client = Client(account_sid, auth_token)

# Twilio Conversations API client
conversations_client = client.conversations.v1.services(conversations_sid)

class Information(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_sid = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    answer_1 = db.Column(db.String(500), nullable=False)
    answer_2 = db.Column(db.String(500), nullable=False)
    answer_3 = db.Column(db.String(500), nullable=False)

    def __init__(self, conversation_sid, phone_number, answer_1, answer_2, answer_3):
        self.conversation_sid = conversation_sid
        self.phone_number = phone_number
        self.answer_1 = answer_1
        self.answer_2 = answer_2
        self.answer_3 = answer_3

# Model inputs
global questions
global recepient_phone_numbers

questions = [
    'What is your name?',
    'What is your age?',
    'What is your favorite color?'
]

# recepient_phone_numbers = ['+5215551078511',
#                            '+5215585308944',
#                            '+5215585487594',
#                            '+5215554186584',
#                            '+5215537139718']

recepient_phone_numbers = ['+5215551078511']

# Inicio conversación
@app.route('/start', methods=['GET'])
def inicio_conversacion():
    conversation = conversations_client.conversations.create()
    
    global new_conversation_sid
    new_conversation_sid = conversation.sid
    
    app.logger.info(conversation.sid)

    for recepient_phone_number in recepient_phone_numbers:

        message = client.messages.create(
            from_=f'whatsapp:{twilio_phone_number}',
            body='Hello, we have a few questions for you to answer',
            to=f'whatsapp:{recepient_phone_number}',
        )

        time.sleep(2)

        message = client.messages.create(
            from_=f'whatsapp:{twilio_phone_number}',
            body=f'{questions[0]}',
            to=f'whatsapp:{recepient_phone_number}',
        )

    return 'Inicio'

@app.route('/', methods=['POST'])
def webhook():

    incoming_message_body = request.values.get('Body', '').lower()
    incoming_phone_number = request.values.get('From', '').lower()

    # Retrieve the conversation state for the current phone number
    conversation_state = session.get('conversation_states', {})

    response = MessagingResponse()

    # Get the user's answer
    user_answer = str(incoming_message_body)

    # Creates new first sessions
    if new_conversation_sid not in conversation_state:
        # First response for this phone number, initialize the conversation state
        conversation_state[new_conversation_sid] = {
            'current_question_index': 0,
            'answers':[],
        }

    conversation_state[new_conversation_sid]['answers'].append(user_answer)

    current_question_index = conversation_state[new_conversation_sid]['current_question_index']
    app.logger.info(f'current_question_index:{current_question_index}')
      
    if current_question_index == 0:
        current_question_index += 1
        time.sleep(2)
    
    elif current_question_index < len(questions):
    # Ask the next question
        next_question = questions[current_question_index]
        time.sleep(2)
        response.message(next_question)

        current_question_index += 1
        conversation_state[new_conversation_sid]['current_question_index'] = current_question_index
    
    elif current_question_index == len(questions):
        # No more questions, end the conversation
        response.message('Thank you for answering all the questions')
        
        answers = [str(answer) for answer in conversation_state[new_conversation_sid]['answers']]
        
        # We have asked all the question, save the answer in the database
        new_info = Information(new_conversation_sid, incoming_phone_number, answers[0], answers[1], answers[2])
        db.session.add(new_info)
        db.session.commit()

        current_question_index += 1
        conversation_state[new_conversation_sid]['current_question_index'] = current_question_index

        session.clear()

    else:
        response.message('Thank you for answering all the questions')

    # Save the updated conversation state back to the session
    session['conversation_states'] = conversation_state

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
