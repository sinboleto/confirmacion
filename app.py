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
import string

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

# Quitar acentos
from unidecode import unidecode


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
global msg_conf
global messages
global dict_info_invitados
global conversation_states

dict_info_invitados = {}
conversation_states = {}

connection = psycopg2.connect(POSTGRESQL_URI)
limite_msg = 15
lag_msg = 1

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
    global msg_conf
    global conversation_states
    global uploaded_file
    global dict_info_invitados

    if uploaded_file != '':
        for telefono_invitado in dict_info_invitados:

            conversation = conversations_client.conversations.create()

            # Get the recipient_name dynamically for each recipient_phone_number
            nom_invitado = dict_info_invitados[telefono_invitado]['nom_invitado']

            msg_conf = f"""Hola *{nom_invitado}*,
Te escribimos para confirmar tu asistencia a *la boda de Monse Cascajares y Diego Grimaldi* que se celebrará el *16 de diciembre de 2023 a las 13:30 hrs. en la Hacienda San Miguel Country Club, ubicada en Av. Juárez 120, San Mateo Tecoloapan, Estado de México* (favor de usar los botones)"""

            message = client.messages.create(
                messaging_service_sid=messaging_service_sid,
                from_=f'whatsapp:{twilio_phone_number}',
                body=msg_conf,
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
        num_user_answer = [int(i) for i in num_user_answer]
        num_user_answer = sum(num_user_answer)
    else:
        num_user_answer = 'Sin número'

    current_question_index = conversation_state['current_question_index']
    app.logger.info(current_question_index)

    # Variables de user
    nombre = conversation_states[incoming_phone_number]['nom_invitado']
    boletos = conversation_states[incoming_phone_number]['boletos']
    link_soporte = 'https://wa.link/30lobt'

    # Mensajes
    # Reconfirmación de asistencia
    msg_reconf = f"""*Disculpa, soy un chatbot* 🤖 y estoy programado únicamente para hacer confirmaciones y brindar información general de eventos. Te agradecería si pudieras contestar el cuestionario o en caso de tener *cualquier otra duda* haz click en el siguiente enlace: {link_soporte} y mandanos un mensaje.

Te agradeceríamos si nos pudieras confirmar tu asistencia *(favor de usar los botones)*"""

    # Número de asistentes
    # msg_conf_num = f"Gracias. Te recuerdo que tu invitación es para *{boletos} persona/s*. Te agradecería si me pudieras confirmar cuantas personas asistirán *(con número)*"
    msg_conf_num = f"Gracias. Vemos que tu invitación es para *{boletos} persona/s*. Te agradecería si me pudieras confirmar cuantas personas asistirán *(con número)*"
    msg_reconf_num = f"""*Disculpa, soy un chatbot* 🤖 y estoy programado únicamente para hacer confirmaciones y brindar información general de eventos. Te agradecería si pudieras contestar el cuestionario o en caso de tener *cualquier otra duda* haz click en el siguiente enlace: {link_soporte} y mandanos un mensaje. 

Vemos que tu invitación es para *{boletos} persona/s*. Te agradecería si me pudieras confirmar cuantas personas asistirán *(con número)*"""

    msg_error_num_conf = f"""El número de *invitados confirmados ({num_user_answer})* no coincide con los *boletos de tu invitación ({boletos})*. Te agradeceríamos si lo pudieras modificar

Vemos que tu invitación es para *{boletos} persona/s*. Te agradecería si me pudieras confirmar cuantas personas asistirán *(con número)*"""

    # No confirma
    msg_no_conf = f"{nombre}, agradecemos mucho tu tiempo y tu respuesta. Que tengas un buen día"

    # Restricción alimentaria
    msg_conf_rest = "De acuerdo. ¿Algún invitado tiene alguna *restricción alimentaria* (vegano, alérgico a algo, etc.)? *(favor de usar los botones)*"
    msg_reconf_rest = f"""*Disculpa, soy un chatbot* 🤖 y estoy programado únicamente para hacer confirmaciones y brindar información general de eventos. Te agradecería si pudieras contestar el cuestionario o en caso de tener *cualquier otra duda* haz click en el siguiente enlace: {link_soporte} y mandanos un mensaje. 

¿Algún invitado tiene alguna *restricción alimentaria* (vegano, alérgico a algo, etc.)? *(favor de usar los botones)*"""

    # Número de restricciones
    msg_conf_num_rest = f"Por favor, señala *cuantas personas (con número) y que restricciones (vegano, alérgico a algo, etc.)* en el mismo mensaje *(por ejemplo, 2 veganos, 1 alérgico a los mariscos)*"
    msg_reconf_num_rest = f"""*Disculpa, soy un chatbot* 🤖 y estoy programado únicamente para hacer confirmaciones y brindar información general de eventos. Te agradecería si pudieras contestar el cuestionario o en caso de tener *cualquier otra duda* haz click en el siguiente enlace: {link_soporte} y mandanos un mensaje.

Por favor, señala *cuantas personas (con número) y que restricciones (vegano, alérgico a algo, etc.)* en el mismo mensaje *(por ejemplo, 2 veganos, 1 alérgico a los mariscos)*"""

    msg_error_num_rest = f"""El número de *invitados con restricciones ({num_user_answer})* no coincide con los *boletos de tu invitación ({boletos})*. Te agradeceríamos si lo pudieras modificar

Por favor, señala *cuantas personas (con número) y que restricciones (vegano, alérgico a algo, etc.)* en el mismo mensaje *(por ejemplo, 2 veganos, 1 alérgico a los mariscos)*"""

    # Información general
    msg_info_general = f"""Agradecemos mucho tu respuesta y te compartimos información adicional del evento:
- La *ceremonia religiosa* se llevará a cabo *en punto de las 13:30 hrs. en la Hacienda San Miguel*, después de la ceremonia los esperamos en *la recepción* que se realizará *en el mismo lugar*

- El *código de vestimenta es formal* (Vestido largo / traje)

- *Mesas de regalos*
   • Liverpool: https://mesaderegalos.liverpool.com.mx/milistaderegalos/51214657
   • Amazon: https://www.amazon.com.mx/wedding/monse-cascajares-diego-grimaldi-ciudad-de-meacutexico-december-2023/registry/2R7ZD760O0QOH

*Confirmamos su asistencia* y estamos emocionados por verte el próximo sábado 16 de diciembre. ¡Saludos!

*Soy un chatbot* 🤖. Si necesitas más información, haz click en el siguiente enlace: {link_soporte} y mandanos un mensaje"""

    msg_default = f'*Hola, soy un chatbot* 🤖 y estoy programado para hacer confirmaciones y brindar información general de eventos. *Cualquier otra duda*, haz click en el siguiente enlace: {link_soporte} y mandanos un mensaje. Gracias'

    if current_question_index == 0:
        if len(user_answer) < limite_msg:  # Verifica si hay choro
            if user_answer == 'si, confirmo' or user_answer == 'si':
                time.sleep(lag_msg)
                response.message(msg_conf_num)

                current_question_index += 1
                conversation_state['current_question_index'] = current_question_index
                conversation_state['respuestas'][0] = 'Si'

            elif user_answer == 'no':
                time.sleep(lag_msg)
                response.message(msg_no_conf)

                current_question_index = -2
                conversation_state['current_question_index'] = current_question_index
                conversation_state['respuestas'][0] = 'No'

                # Cargar datos en SQL
                carga_SQL(conversation_state)

            else:
                time.sleep(lag_msg)
                message = client.messages.create(
                    messaging_service_sid=messaging_service_sid,
                    from_=f'whatsapp:{twilio_phone_number}',
                    body=msg_reconf,
                    to=f'whatsapp:{incoming_phone_number}'
                )

            conversation_state['current_question_index'] = current_question_index

        else:
            # Si hay choro, manda el mensaje de revisión para referir al cliente a un operador
            time.sleep(lag_msg)
            message = client.messages.create(
                messaging_service_sid=messaging_service_sid,
                from_=f'whatsapp:{twilio_phone_number}',
                body=msg_reconf,
                to=f'whatsapp:{incoming_phone_number}'
            )

            conversation_state['current_question_index'] = current_question_index

    elif current_question_index == 1:
        if len(user_answer) < limite_msg:  # Verifica si hay choro
            if user_answer.isnumeric() and num_user_answer != 'Sin número' and num_user_answer <= conversation_states[incoming_phone_number]['boletos']:
                time.sleep(lag_msg)
                response.message(msg_conf_rest)
                conversation_state['respuestas'][1] = user_answer

                current_question_index += 1
                conversation_state['current_question_index'] = current_question_index

            else:
                time.sleep(lag_msg)
                message = client.messages.create(
                    messaging_service_sid=messaging_service_sid,
                    from_=f'whatsapp:{twilio_phone_number}',
                    body=msg_error_num_conf,
                    to=f'whatsapp:{incoming_phone_number}'
                )
                conversation_state['current_question_index'] = current_question_index

        else:
            time.sleep(lag_msg)
            message = client.messages.create(
                messaging_service_sid=messaging_service_sid,
                from_=f'whatsapp:{twilio_phone_number}',
                body=msg_reconf_num,
                to=f'whatsapp:{incoming_phone_number}'
            )

            conversation_state['current_question_index'] = current_question_index

    elif current_question_index == 2:
        if len(user_answer) < limite_msg:  # Verifica si hay choro
            if user_answer == 'si':
                time.sleep(lag_msg)
                response.message(msg_conf_num_rest)

                current_question_index += 1
                conversation_state['current_question_index'] = current_question_index
                conversation_state['respuestas'][2] = 'Si'

            elif user_answer == 'no':
                time.sleep(lag_msg)
                response.message(msg_info_general)

                current_question_index = -2
                conversation_state['current_question_index'] = current_question_index
                conversation_state['respuestas'][2] = 'No'

                # Cargar datos en SQL
                carga_SQL(conversation_state)

            else:
                time.sleep(lag_msg)
                message = client.messages.create(
                    messaging_service_sid=messaging_service_sid,
                    from_=f'whatsapp:{twilio_phone_number}',
                    body=msg_reconf_rest,
                    to=f'whatsapp:{incoming_phone_number}'
                )

                conversation_state['current_question_index'] = current_question_index

        else:
            time.sleep(lag_msg)
            message = client.messages.create(
                messaging_service_sid=messaging_service_sid,
                from_=f'whatsapp:{twilio_phone_number}',
                body=msg_reconf_rest,
                to=f'whatsapp:{incoming_phone_number}'
            )

            conversation_state['current_question_index'] = current_question_index

    elif current_question_index == 3:
        if num_user_answer == 'Sin número' or num_user_answer <= conversation_states[incoming_phone_number]['boletos']:
            time.sleep(lag_msg)
            response.message(msg_info_general)

            current_question_index = -2
            conversation_state['current_question_index'] = current_question_index
            conversation_state['respuestas'][3] = user_answer

            # Cargar datos en SQL
            carga_SQL(conversation_state)

        else:
            time.sleep(lag_msg)
            boletos = conversation_states[incoming_phone_number]['boletos']
            message = client.messages.create(
                messaging_service_sid=messaging_service_sid,
                from_=f'whatsapp:{twilio_phone_number}',
                body=msg_error_num_rest,
                to=f'whatsapp:{incoming_phone_number}'
            )
            conversation_state['current_question_index'] = current_question_index

    else:
        time.sleep(lag_msg)
        response.message(msg_default)

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
                    nom_invitado = row['nom_invitado'].strip()
                    num_boletos = row['num_boletos']

                    # Create a subdictionary
                    subdict = {"nom_invitado": nom_invitado,
                               "num_boletos": num_boletos}

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
    global dict_info_invitados
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
                dict_info_invitados = {}
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


def split_string(text, dict_equivalencias):
    # Step 1: Remove Spanish articles and conjunctions
    articles = ['el', 'la', 'los', 'las', 'un',
                'una', 'unos', 'unas', 'lo', 'al', 'del']
    conjunctions = ['y', 'e', 'ni', 'que', 'o', 'u', 'pero', 'aunque',
                    'sin embargo', 'por lo tanto', 'así que', 'porque', 'ya que']
    pattern = r'\b(?:' + '|'.join(articles + conjunctions) + r')\b'
    text_without_articles_conjunctions = re.sub(
        pattern, '', text, flags=re.IGNORECASE)

    # Step 2: Remove punctuation marks
    text_without_punctuation = text_without_articles_conjunctions.translate(
        str.maketrans('', '', string.punctuation))

    # Step 3: Split the text before a second number is encountered
    substrings = re.split(r'(?= \d+\D|$)', text_without_punctuation)

    # Step 4: Process each substring in the list
    for i, substring in enumerate(substrings):
        # Step 4a: Remove accents
        substrings[i] = unidecode(substring).strip()

        # Step 4b: If there is a number but no text, add 'no especificado'
        if re.search(r'\b\d+\b', substrings[i]) and not re.search(r'\b(?!\d+\b)\w+\b', substrings[i]):
            substrings[i] = f'{substrings[i]} no especificado'

        # Step 4c: If restriction not found in dict_equivalencias, add 'otros'
        encontrado = 0
        for category in dict_equivalencias.keys():
            if category in substrings[i]:
                encontrado = 1

        if encontrado == 0:
            num_rest = re.search(r'\b\d+\b', substrings[i])
            if num_rest:
                substrings[i] = f'{num_rest[0]} otro'

    return substrings


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
    if confirmed > 0:
        plt.text(0, confirmed / 2, str(confirmed),
                 ha='center', va='center', fontsize=12, color='black')

    if not_confirmed > 0:
        plt.text(1, not_confirmed / 2, str(not_confirmed),
                 ha='center', va='center', fontsize=12, color='black')

    plt.box(False)
    plt.yticks([])

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
    if attending > 0:
        plt.text(0, attending / 2, str(attending),
                 ha='center', va='center', fontsize=12, color='black')

    if not_attending > 0:
        plt.text(1, not_attending / 2, str(not_attending),
                 ha='center', va='center', fontsize=12, color='black')

    plt.box(False)
    plt.yticks([])

    # Save the plot to a bytes buffer and encode it in base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    plot2_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Create the third graph
    df_restricciones = df[df['respuesta_3'] == 'Si'].drop(columns=['id_evento', 'nom_invitado', 'telefono', 'boletos',
                                                                   'respuesta_1', 'respuesta_2', 'respuesta_3'])

    # Equivalencias
    dict_equivalencias = {'alergi': 'Alérgico',
                          'vegan': 'Vegano',
                          'vegetarian': 'Vegetariano',
                          'celiac': 'Celiaco',
                          'no especificado': 'No especificado',
                          'otro': 'Otro'
                          }

    df_restricciones['tipo_restricciones'] = df_restricciones['respuesta_4'].apply(
        lambda x: split_string(x, dict_equivalencias))

    lista_restricciones = df_restricciones['tipo_restricciones'].explode(
    ).tolist()
    lista_restricciones = [e for e in lista_restricciones if e != '']

    cuentas = []

    for categoria in dict_equivalencias.keys():
        cuenta = 0
        for restriccion in lista_restricciones:
            if categoria in restriccion:
                cuenta += sum([int(s)
                               for s in re.findall(r'\b\d+\b', restriccion)])
        cuentas.append(cuenta)

    resumen_restricciones = dict(zip(dict_equivalencias.values(), cuentas))
    resumen_restricciones = {key: value for key,
                             value in resumen_restricciones.items() if value != 0}

    # Gráfica
    categories = list(resumen_restricciones.keys())
    values = list(resumen_restricciones.values())

    plt.figure()
    bottom = np.zeros(len(categories))

    altura = 0
    colors = ['#9FBCD1', '#759FBC', '#5082A5', '#3C617C', '#284153', '#142029']
    colors = colors[:len(categories)]

    for category, weight_count, color in zip(categories, np.array(values), colors):
        p = plt.bar(0, weight_count, label=category,
                    bottom=bottom, color=color)
        p = plt.bar(1, 0, label=category,
                    bottom=bottom, color=color)
        bottom += weight_count
        altura += weight_count
        if weight_count > 0:
            plt.text(0, altura - weight_count / 2, str(weight_count),
                     ha='center', va='center', fontsize=12, color='black')

    plt.title('Restricciones alimentarias')
    plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.0f}'))

    # Create a legend
    legend_labels = [f"{category}" for category in categories]
    plt.legend(legend_labels, loc='upper right', title='Categorias',
               bbox_to_anchor=(1, 0.9), borderaxespad=0.)

    plt.axis('off')

    # Save the plot to a bytes buffer and encode it in base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    plot3_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render_template('dashboard.html', id_evento_values=id_evento_values, data=data, plot1_base64=plot1_base64, plot2_base64=plot2_base64, plot3_base64=plot3_base64)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
