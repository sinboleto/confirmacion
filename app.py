# Libraries

# Flask app
from flask import Flask, render_template, request, redirect, url_for, send_file

# Twilio
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

# System
from dotenv import load_dotenv
import os
import json
import re

# Delay
import time

# POSTGRES SQL
import psycopg2

# Graph
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
import numpy as np
import pandas as pd
import base64


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
POSTGRESQL_URI = os.environ.get('POSTGRESQL_URI')

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
conversation_states = {}

connection = psycopg2.connect(POSTGRESQL_URI)

# Table config
try:
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'CREATE TABLE confirmaciones (id_evento TEXT, sid TEXT, nom_invitado TEXT, telefono TEXT, boletos INT, respuesta_1 TEXT, respuesta_2 INT, respuesta_3 TEXT, respuesta_4 TEXT);')
except psycopg2.errors.DuplicateTable:
    pass


# Inicio conversación
@app.route('/start', methods=['GET'])
def inicio_conversacion():
    global intro
    global conversation_states
    global uploaded_file
    global dict_info_invitados
    
    if uploaded_file != '':
        for telefono_invitado in dict_info_invitados:

            conversation = conversations_client.conversations.create()
            # app.logger.info(conversation.sid)

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
                'id_evento': id_evento,
                'sid': conversation.sid,
                'nom_invitado': nom_invitado,
                'telefono': telefono_invitado,
                'boletos': dict_info_invitados[telefono_invitado]['num_boletos'],
                'current_question_index': 0,
                'respuestas': ['No', 0, 'No', 'Ninguna']
            }

        # app.logger.info(conversation_states)

        uploaded_file = ''
        dict_info_invitados = {}

        return 'Confirmación enviada'
    else:
       return 'Subir archivo de base de datos'
    

def carga_SQL(conversation_state):
    # Cargar datos en SQL
    with connection.cursor() as cursor:
        cursor.execute('INSERT INTO confirmaciones VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);',
            (str(conversation_state['id_evento']),  # id_evento
            str(conversation_state['sid']),  # sid
            # nom_invitado
            str(conversation_state['nom_invitado']),
            # telefono
            str(conversation_state['telefono']),
            int(conversation_state['boletos']),  # boletos
            # respuesta_1
            str(conversation_state['respuestas'][0]),
            # respuesta_2
            str(conversation_state['respuestas'][1]),
            # respuesta_3
            str(conversation_state['respuestas'][2]),
            # respuesta_4
            str(conversation_state['respuestas'][3])
            )
            )
        connection.commit()


@app.route('/', methods=['POST'])
def webhook():

    incoming_message_body = request.values.get('Body', '').lower()
    incoming_phone_number = request.values.get('From', '').lower()
    incoming_phone_number = incoming_phone_number.replace('whatsapp:', '')

    # app.logger.info(incoming_phone_number)

    # Get the conversation state for the current recipient
    conversation_state = conversation_states.get(incoming_phone_number, None)

    if not conversation_state:
        app.logger.info('Invalid recipient phone number')
        return 'Invalid recipient phone number'

    response = MessagingResponse()

    # Get the user's answer
    user_answer = str(incoming_message_body)
    
    num_user_answer = re.findall(r'\d+', user_answer)
    if num_user_answer:
        # Return the first number (index 0)
        num_user_answer = int(num_user_answer[0])
    else:
        num_user_answer = 'Sin número'

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
            response.message(
                f"Gracias. Te recuerdo que tu invitación es para *{conversation_states[incoming_phone_number]['boletos']} persona/s*. Te agradecería si me pudieras confirmar cuantas personas asistirán *(con número)*")

            current_question_index += 1
            conversation_state['current_question_index'] = current_question_index
            conversation_state['respuestas'][0] = 'Si'

        if user_answer == 'no':
            time.sleep(2)
            response.message(
                f"{conversation_states[incoming_phone_number]['nom_invitado']}, agradecemos mucho tu tiempo y tu respuesta. Que tengas un buen día")

            current_question_index = -1
            conversation_state['current_question_index'] = current_question_index
            conversation_state['respuestas'][0] = 'No'

            # Cargar datos en SQL
            carga_SQL(conversation_state)

    elif current_question_index == 1:
        if num_user_answer == 'Sin número' or num_user_answer <= conversation_states[incoming_phone_number]['boletos']:
            time.sleep(2)
            response.message(
                f"De acuerdo. ¿Algún invitado tiene alguna *restricción alimentaria* (vegetariano, vegano, alérgico a algo, etc.)?")
            conversation_state['respuestas'][1] = user_answer

            current_question_index += 1
            conversation_state['current_question_index'] = current_question_index
        else:
            time.sleep(2)
            mensaje_error = f"El número de invitados confirmados {num_user_answer} no coincide con los boletos de tu invitación {conversation_states[incoming_phone_number]['boletos']}. Te agradeceríamos si lo pudieras revisar"
            message = client.messages.create(
                messaging_service_sid=messaging_service_sid,
                from_=f'whatsapp:{twilio_phone_number}',
                body=mensaje_error,
                to=f'whatsapp:{incoming_phone_number}'
            )

            time.sleep(2)
            message = client.messages.create(
                messaging_service_sid=messaging_service_sid,
                from_=f'whatsapp:{twilio_phone_number}',
                body=f"De acuerdo. ¿Algún invitado tiene alguna *restricción alimentaria* (vegetariano, vegano, alérgico a algo, etc.)?",
                to=f'whatsapp:{incoming_phone_number}'
            )

    elif current_question_index == 2:
        if user_answer == 'si':
            time.sleep(2)
            response.message(
                f"Por favor, señala *cuantas personas (con número) y que restricciones (vegetariano, vegano, alérgico a algo, etc.)* en el mismo mensaje *(por ejemplo, 2 vegetarianos, 1 alérgico a los mariscos)*")

            current_question_index += 1
            conversation_state['current_question_index'] = current_question_index
            conversation_state['respuestas'][2] = 'Si'

        if user_answer == 'no':
            time.sleep(2)
            response.message(info_general)

            current_question_index = -1
            conversation_state['current_question_index'] = current_question_index
            conversation_state['respuestas'][2] = 'No'

            # Cargar datos en SQL
            carga_SQL(conversation_state)

    elif current_question_index == 3:
        time.sleep(2)
        response.message(info_general)

        current_question_index = -1
        conversation_state['current_question_index'] = current_question_index
        conversation_state['respuestas'][3] = user_answer

        # Cargar datos en SQL
        carga_SQL(conversation_state)

    else:
        time.sleep(2)
        response.message(f'*Hola, soy un chatbot* 🤖 y estoy programado para hacer confirmaciones y brindar información general de eventos. *Cualquier otra duda*, haz click en el siguiente enlace: https://wa.link/jh47gm y mandanos un mensaje. Gracias')

    # Update the conversation state in the global dictionary
    conversation_states[incoming_phone_number] = conversation_state

    return str(response)

@app.route('/conv_xlsx_json', methods=['POST'])
def conv_xlsx_json():
    if 'xlsx_file' in request.files:
        uploaded_file = request.files['xlsx_file']

        if uploaded_file.filename.endswith('.xlsx'):
            # Read the contents of the Excel file into a DataFrame
            try:
                df = pd.read_excel(uploaded_file, sheet_name='BD')

                dict_invitados = {}

                for index, row in df.iterrows():
                    telefono_modificado = f"+{row['telefono_modificado']}"
                    nom_invitado = row['nom_invitado']
                    num_boletos = row['num_boletos']

                    # Create a subdictionary
                    subdict = {"nom_invitado": nom_invitado, "num_boletos": num_boletos}

                    # Add the subdictionary to the main dictionary with telefono_modificado as the key
                    dict_invitados[telefono_modificado] = subdict

                # Convert the 'dict_invitados' dictionary to a JSON string
                json_string = json.dumps(dict_invitados, ensure_ascii=False)

                # Save the JSON string to a JSON file
                json_filename = 'lista_invitados_json.json'
                with open(json_filename, 'w') as json_file:
                    json_file.write(json_string)

                return send_file(json_filename, as_attachment=True, download_name=json_filename)

            except Exception as e:
                return f'Error en la lectura del archivo de Excel: {str(e)}'
        else:
            return 'Formato de archivo inválido. Favor de subir un archivo .xlsx.'
    return 'Ocurrió un error o no se subió un archivo.'

# Add a new route to render the HTML form
@app.route('/upload', methods=['GET'])
def upload_form():
    return render_template('upload.html')


# Add a route to handle the uploaded JSON file
@app.route('/upload', methods=['POST'])
def upload_json_file():
    global id_evento
    global uploaded_file
    id_evento = request.form.get('id_evento')  # Get the id_evento input value

    # Check if id_evento is empty
    if not id_evento:
        return 'El ID del evento es necesario. Favor de proporcionar un ID del evento y tratar de nuevo.'

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
                return redirect(url_for('upload_form'))
            except json.JSONDecodeError:
                return 'Archivo JSON no válido.'
    return 'Ocurrió un error o no se subió un archivo.'


# Function to retrieve data from the database
def get_data(query):
    data = []
    connection = psycopg2.connect(POSTGRESQL_URI)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            data = cursor.fetchall()
    return data


# Dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():

    # Get distinct values of id_evento from the database
    connection = psycopg2.connect(POSTGRESQL_URI)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT DISTINCT id_evento FROM confirmaciones;')
            id_evento_values = [row[0] for row in cursor.fetchall()]
            id_evento_values = sorted(id_evento_values)

    selected_id_evento = request.form.get('selected_id_evento')
    if selected_id_evento:
        # Filter data based on the selected id_evento
        data = get_data(
            f"SELECT id_evento, nom_invitado, telefono, boletos, respuesta_1, respuesta_2, respuesta_3, respuesta_4 FROM confirmaciones WHERE id_evento ='{selected_id_evento}' ORDER BY id_evento;")

    else:
        # Get all data if no filter is applied
        data = get_data(
            "SELECT id_evento, nom_invitado, telefono, boletos, respuesta_1, respuesta_2, respuesta_3, respuesta_4 FROM confirmaciones ORDER BY id_evento;")

    columnas = ['id_evento', 'nom_invitado', 'telefono', 'boletos',
                'respuesta_1', 'respuesta_2', 'respuesta_3', 'respuesta_4']
    df = pd.DataFrame(data, columns=columnas)

    # Create the first graph
    plt.figure()
    confirmed = len(df[df['respuesta_1'] == 'Si'])
    not_confirmed = len(df[df['respuesta_1'] == 'No'])
    plt.bar(['Si', 'No'], [confirmed, not_confirmed],
            color=['#9524D6', '#D62466'])
    plt.title('Invitados confirmados')
    plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.0f}'))

    # Add total numbers to the graph
    plt.text(0, confirmed * 1.1, str(confirmed),
             ha='center', fontsize=12, color='black')
    plt.text(1, not_confirmed * 1.1, str(not_confirmed),
             ha='center', fontsize=12, color='black')

    # Save the plot to a bytes buffer and encode it in base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    plot1_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Create the second graph
    plt.figure()
    attending = df[df['respuesta_1'] == 'Si']['respuesta_2'].sum()
    not_attending = df[df['respuesta_1'] == 'No']['boletos'].sum()
    plt.bar(['Si', 'No'], [attending, not_attending],
            color=['#9524D6', '#D62466'])
    plt.title('Personas que asistirán')
    plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.0f}'))

    # Add total numbers to the graph
    plt.text(0, attending * 1.1, str(attending),
             ha='center', fontsize=12, color='black')
    plt.text(1, not_attending * 1.1, str(not_attending),
             ha='center', fontsize=12, color='black')

    # Save the plot to a bytes buffer and encode it in base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    plot2_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render_template('dashboard.html', id_evento_values=id_evento_values, data=data, plot1_base64=plot1_base64, plot2_base64=plot2_base64)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
