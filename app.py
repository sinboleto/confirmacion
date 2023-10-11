# Libraries

# Flask app
from flask import Flask, render_template, request, Response, redirect, url_for

# Twilio
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

# System
from dotenv import load_dotenv
import os

# Delay
import time

import json


# Main script
app = Flask(__name__)

port = int(os.environ.get('PORT', 5000))

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

# Model inputs
global intro
global messages
global dict_info_invitados
global conversation_states

dict_info_invitados = {}

# dict_info_invitados = {'+5215551078511': {'nom_invitado': 'Bego�a Medrano', 'num_boletos': 2},
#                     #    '+5215585308944': {'nom_invitado': 'Gerardo Chavez', 'num_boletos': 2},
#                     #    '+5215630266977': {'nom_invitado': 'Amaya Medrano', 'num_boletos': 2},
#                     #    '+5215559658559': {'nom_invitado': 'José Manuel Santos', 'num_boletos': 2},
#                         }

conversation_states = {}


# Inicio conversación
@app.route('/start', methods=['GET'])
def inicio_conversacion():
    global intro
    global conversation_states

    for telefono_invitado in dict_info_invitados:

        conversation = conversations_client.conversations.create()
        app.logger.info(conversation.sid)

        # Get the recipient_name dynamically for each recipient_phone_number
        nom_invitado = dict_info_invitados[telefono_invitado]['nom_invitado']

        intro = f"""Hola *{nom_invitado}*,
Te extendemos la invitación para *la boda de Amaya y José Manuel* que se celebrará el *9 de diciembre de 2023*. Te agradeceríamos si nos pudieras confirmar tu asistencia"""

        message = client.messages.create(
            messaging_service_sid=messaging_service_sid,
            from_=f'whatsapp:{twilio_phone_number}',
            body=intro,
            to=f'whatsapp:{telefono_invitado}'
        )

        # Store the conversation SID and initial state for each recipient
        conversation_states[telefono_invitado] = {
            'conversation_sid': conversation.sid,
            'num_boletos': dict_info_invitados[telefono_invitado]['num_boletos'],
            'current_question_index': 0,
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

    current_question_index = conversation_state['current_question_index']

    info_general = """Agradecemos mucho tu respuesta y te compartimos información adicional del evento:
- La *ceremonia religiosa* se llevará a cabo *en punto de las 13:30 hrs. en el Jardín de Eventos Amatus*, después de la ceremonia lo esperamos en *la recepción* que se realizará *en el mismo lugar*

- El *código de vestimenta es formal* (Vestido largo o corto de día / traje sin corbata)

- Encuentra más información sobre *la mesa de regalos, hoteles y salones de belleza* en la página: www.amayayjosemanuel.com

*Soy un chatbot* 🤖. Si necesitas más información, haz click en el siguiente enlace: https://wa.link/jh47gm y mandanos un mensaje.

¡Muchas gracias y saludos!"""

    if current_question_index == 0:
        if user_answer == 'si, confirmo':
            time.sleep(2)
            response.message(f"Gracias. Te recuerdo que tu invitación es para *{dict_info_invitados[incoming_phone_number]['num_boletos']} persona/s*. Te agradecería si me pudieras confirmar cuantas personas asistirán *(con número)*")
            
            current_question_index += 1
            conversation_state['current_question_index'] = current_question_index

        if user_answer == 'no':
            time.sleep(2)
            response.message(f"{dict_info_invitados[incoming_phone_number]['nom_invitado']}, agradecemos mucho tu tiempo y tu respuesta. Que tengas un buen día")

            current_question_index = -1
            conversation_state['current_question_index'] = current_question_index
    
    elif current_question_index == 1:
        time.sleep(2)
        response.message(f"De acuerdo. ¿Algún invitado tiene alguna *restricción alimentaria*?")

        current_question_index += 1
        conversation_state['current_question_index'] = current_question_index

    elif current_question_index == 2:
        if user_answer == 'si':
            time.sleep(2)
            response.message(f"Por favor, señala *cuantas personas (con número) y que restricciones (vegetariano, vegano, alérgico, etc.)* en el mismo mensaje *(por ejemplo, 2 vegetarianos)*")

            current_question_index += 1
            conversation_state['current_question_index'] = current_question_index

        if user_answer == 'no':
            time.sleep(2)
            response.message(info_general)

            current_question_index = -1
            conversation_state['current_question_index'] = current_question_index

    elif current_question_index == 3:
        time.sleep(2)
        response.message(info_general)

        current_question_index = -1
        conversation_state['current_question_index'] = current_question_index

    else:
        time.sleep(2)
        response.message(f'*Hola, soy un chatbot* 🤖 y estoy programado para hacer confirmaciones y brindar información general de eventos. *Cualquier otra duda*, haz click en el siguiente enlace: https://wa.link/jh47gm y mandanos un mensaje. Gracias')

    # Update the conversation state in the global dictionary
    conversation_states[incoming_phone_number] = conversation_state

    return str(response)

# Add a new route to render the HTML form
@app.route('/upload', methods=['GET'])
def upload_form():
    return render_template('upload.html')

# Add a route to handle the uploaded JSON file
@app.route('/upload', methods=['POST'])
def upload_json_file():
    if 'json_file' in request.files:
        uploaded_file = request.files['json_file']
        if uploaded_file.filename != '':
            # You can process the uploaded file here
            data = uploaded_file.read()
            # Convert data to a dictionary if it's in JSON format
            try:
                json_data = json.loads(data)
                # Update dict_info_invitados with the uploaded JSON data
                for phone_number, info in json_data.items():
                    dict_info_invitados[phone_number] = info
                return 'File uploaded and data added to dict_info_invitados successfully.'
            except json.JSONDecodeError:
                return 'Invalid JSON file.'
    return 'No file uploaded or an error occurred.'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
