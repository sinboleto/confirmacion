import csv
from flask import Flask, render_template, request, Response, session
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
# app.secret_key = os.environ.get('SECRET_KEY')

# Credentials
account_sid = 'ACf01ddcd618830097852506cba7b428ef'
auth_token = '1b36553f5486a232a6edfa04db76cc66'
twilio_phone_number = '+12058391586'
app.secret_key = 'SB_2022'

# Create Twilio client
client = Client(account_sid, auth_token)


class Information(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.String(500), nullable=False)

    def __init__(self, phone_number, question, answer):
        self.phone_number = phone_number
        self.question = question
        self.answer = answer


# Inicio conversación
@app.route('/start', methods=['GET'])
def inicio_conversacion():
    
    message = client.messages.create(
        from_ = f'whatsapp:{twilio_phone_number}',
        body = 'Hello, we have a few questions for you to answer',
        to = 'whatsapp:+5215551078511'
        )
    
    return 'Inicio'

@app.route('/', methods=['POST'])
def webhook():

    questions = [
                'What is your name?',
                'What is your age?',
                'What is your favorite color?'
                ]

    incoming_message_body = request.values.get('Body', '').lower()
    incoming_phone_number = request.values.get('From', '').lower()

    # Retrieve the conversation state for the current phone number
    conversation_state = session.get('conversation_states', {})

    response = MessagingResponse()

    # Creates new first sessions
    if incoming_phone_number not in conversation_state:
        # First response for this phone number, initialize the conversation state
        conversation_state[incoming_phone_number] = {
            'questions': questions,
            'current_question_index': -1  # -1 indicates that we haven't asked the first question yet
        }

    # Get the user's answer
    user_answer = str(incoming_message_body)

    current_question_index = conversation_state[incoming_phone_number]['current_question_index']

    if current_question_index >= 0 and current_question_index <= len(questions) - 1:
        # We have asked a question, save the answer in the database
        current_question = questions[current_question_index]
        new_info = Information(incoming_phone_number, current_question, user_answer)
        db.session.add(new_info)
        db.session.commit()

    if current_question_index >= len(questions) - 1:
        # No more questions, end the conversation
        response.message('Thank you for answering all the questions')
    else:
        # Ask the next question
        current_question_index += 1
        conversation_state[incoming_phone_number]['current_question_index'] = current_question_index

        next_question = questions[current_question_index]
        response.message(next_question)

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
    session = db.session

    # Delete all records from the Information table
    session.query(Information).delete()

    # Commit the changes to the database
    session.commit()

    # Reset the conversation_state for all phone numbers
    conversation_state = session.get('conversation_states', {})
    conversation_state.clear()
    session['conversation_states'] = conversation_state

    return 'Database information has been deleted successfully'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
