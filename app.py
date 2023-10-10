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
global recipient_phone_numbers
global list_info_event
global dict_info_recipients
global conversation_states

dict_info_invitados = {'+5215551078511': {'nom_invitado': 'Santiago', 'num_boletos': 2},
                        # '+5215585308944': {'recipient_ID':'AMB_170823_003', 'recipient_name': 'Gerardo'},
                        # '+5215633521893': {'recipient_ID':'AMB_170823_002', 'recipient_name': 'Beatriz'},
                        # '+5215539001433': {'recipient_ID':'AMB_170823_001', 'recipient_name': 'Fernando'},
                        # '+5215585308944': {'recipient_name': 'Gerardo', 'tickets': 2},
                        # '+5215585487594':{'recipient_name':'Fernanda', 'tickets':2},
                        # '+5215554186584':{'recipient_name':'Maru', 'tickets':2},
                        # '+5215537139718':{'recipient_name':'Pablo', 'tickets':2},
                        # '+5215544907299':{'recipient_name':'Andrea', 'tickets':2}
                        }

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

        intro = f"""Hola {nom_invitado}
Te extendemos la invitación para la boda de Amaya y José Manuel que se celebrará el 9 de diciembre del 2023. Te agradeceríamos si nos pudieras confirmar tu asistencia"""

        message = client.messages.create(
            messaging_service_sid=messaging_service_sid,
            from_=f'whatsapp:{twilio_phone_number}',
            body=intro,
            to=f'whatsapp:{telefono_invitado}'
        )

        # Store the conversation SID and initial state for each recipient
        conversation_states[telefono_invitado] = {
            'conversation_sid': conversation.sid,
            'num_boletos': dict_info_recipients[telefono_invitado]['num_boletos'],
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

    if current_question_index == 0:
        if user_answer == 'si':
            time.sleep(2)
            response.message(f"Gracias. Te recuerdo que tu invitación es para {dict_info_invitados[incoming_phone_number]['num_boletos']}. Te agradecería si me pudieras confirmar cuantas personas asistirán (con número)")
            
            current_question_index += 1
            conversation_state['current_question_index'] = current_question_index

        if user_answer == 'no':
            time.sleep(2)
            response.message(f"{dict_info_invitados[incoming_phone_number]['nom_invitado']}, agradecemos mucho tu tiempo y tu respuesta. Que tengas un buen día")

            current_question_index = -1
            conversation_state['current_question_index'] = current_question_index
    
    elif current_question_index == 1:
        time.sleep(2)
        response.message(f"De acuerdo. ¿Algún invitado tiene alguna restricción alimentaria? Por favor, señala cuantas personas y que restricciones (vegetariano, vegano, alérgico, etc.) en el mismo mensaje")

        current_question_index += 1
        conversation_state['current_question_index'] = current_question_index   

    elif current_question_index == 2:
        
        msg = """Te compartimos información adicional del evento:
- La ceremonia religiosa se llevará a cabo en punto de las 13:30 hrs. en el Jardín de Eventos Amatus, después de la ceremonia lo esperamos en la recepción que se realizará en el mismo lugar

- El código de vestimenta es formal (Vestido largo o corto de día / traje sin corbata)

- Encuentra más información sobre la mesa de regalos, hoteles y salones de belleza en la página: www.amayayjosemanuel.com

Soy un chatbot. Si necesitas más información, haz click en el siguiente enlace: https://wa.link/rthr9k y mandanos un mensaje. ¡Muchas gracias y saludos!"""
        
        time.sleep(2)
        response.message(msg)

        current_question_index += 1
        conversation_state['current_question_index'] = current_question_index

    else:
        time.sleep(2)
        response.message(f'Hola, soy un chatbot y estoy programado para hacer confirmaciones y brindar información general de eventos. Cualquier otra duda, haz click en el siguiente enlace: https://wa.link/rthr9k y mandanos un mensaje. Gracias')





















    if current_question_index == 0 and user_answer == 'no':
        current_question_index = -1

    app.logger.info(f'current_question_index:{current_question_index}')

    if current_question_index >= 0 and current_question_index < len(messages):
        # Ask the next question
        next_message = messages[current_question_index]

        time.sleep(2)
        # response.message(next_message)

        content_SID = 'HXfd44cf82c32f0bd4ee0b96fc249fc1fb'  # Revisar

        content_variables = json.dumps({'2': recepient_ID})

        message = client.messages.create(
            messaging_service_sid=messaging_service_sid,
            from_=f'whatsapp:{twilio_phone_number}',
            content_sid=content_SID,
            content_variables=content_variables,
            to=f'whatsapp:{incoming_phone_number}',
        )

        time.sleep(1)

        message = client.messages.create(
            messaging_service_sid=messaging_service_sid,
            from_=f'whatsapp:{twilio_phone_number}',
            body='¿Lo recibiste?',
            to=f'whatsapp:{incoming_phone_number}'
        )

        current_question_index += 1
        conversation_state['current_question_index'] = current_question_index

    elif current_question_index == 1 and user_answer == 'no':
        message = client.messages.create(
            messaging_service_sid=messaging_service_sid,
            from_=f'whatsapp:{twilio_phone_number}',
            body='En un momento te reenviaremos el boleto por este medio',
            to=f'whatsapp:{incoming_phone_number}'
        )

        # No more questions, end the conversation
        date = f'{list_info_event[2]} de {list_info_event[3]} de {list_info_event[4]}'

        time.sleep(2)

        message = client.messages.create(
            messaging_service_sid=messaging_service_sid,
            from_=f'whatsapp:{twilio_phone_number}',
            body=f"""Finalmente, te compartimos la información general del evento:
Fecha y hora de inicio: {date} a las {list_info_event[6]}
Lugar: {list_info_event[7]}
Dirección: {list_info_event[8]} - {list_info_event[9]}""",
            to=f'whatsapp:{incoming_phone_number}'
        )

        time.sleep(2)

        message = client.messages.create(
            messaging_service_sid=messaging_service_sid,
            from_=f'whatsapp:{twilio_phone_number}',
            body=f'{dict_info_recipients[incoming_phone_number]["recipient_name"]}, agradecemos mucho tu tiempo y tu respuesta. Que tengas un buen día',
            to=f'whatsapp:{incoming_phone_number}'
        )

        current_question_index += 1
        conversation_state['current_question_index'] = current_question_index

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

        current_question_index += 1
        conversation_state['current_question_index'] = current_question_index

    elif current_question_index == -1:
        time.sleep(2)
        response.message(
            f'{dict_info_recipients[incoming_phone_number]["recipient_name"]}, agradecemos mucho tu tiempo y tu respuesta. Que tengas un buen día')

    else:
        time.sleep(2)
        response.message(
            f'Hola, soy un chatbot y estoy programado para hacer confirmaciones y brindar información general del evento. Cualquier otra duda, favor de comunicarse a este teléfono: {list_info_event[10]}. Gracias')

    # Update the conversation state in the global dictionary
    conversation_states[incoming_phone_number] = conversation_state

    return str(response)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
