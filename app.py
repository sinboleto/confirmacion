# Libraries

# Flask app
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, jsonify

# Twilio
from twilio.twiml.messaging_response import MessagingResponse
from twilio.base.exceptions import TwilioRestException
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

# Fecha
from datetime import date


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
ngrok_auth_token = os.environ.get('NGROK_AUTH_TOKEN')

# Create Twilio client
client = Client(account_sid, auth_token)

# Twilio Conversations API client
conversations_client = client.conversations.v1.services(conversations_sid)

# Model inputs
global msg_conf
global messages
global dict_info_invitados
global conversation_states
global info_plantillas
global url_invitacion
global invitacion_carpeta

dict_info_invitados = {}
conversation_states = {}
info_plantillas = {}
url_invitacion = ''

connection = psycopg2.connect(POSTGRESQL_URI)
limite_msg = 17
lag_msg = 0.2

# Variables del evento
# content_SID = 'HX0a2d27a46cd78cb3b9534cad4fb9057d'  # Confirmación
# content_SID = 'HXec089fa6d686d8fc5531a7383c242734'  # Invitación
content_SID_std = 'HX973fe6a8e3741bf1d85209b5d16fb2f7'  # Save the date
content_SID_texto = 'HX1a0b4351bc03d158e998c95878d09761'  # Save the date
content_SID_texto_media = 'HX36e96191c5cc3066a336e7449269b1d5'  # Save the date

# nom_novia = 'Sofía'
# nom_novio = 'Benito'
# fecha_evento = '2 de diciembre de 2023'
# hora_inicio = '13:00 hrs'
# lugar_evento = 'Xochitepec, Morelos'
# lugar_ceremonia = 'el Jardín Paraíso'
# lugar_recepcion = 'en el mismo lugar'
# codigo_vestimenta = 'formal (guayabera blanca manga larga / vestido largo)'
# link_mesa_regalos = 'https://dagiftmx.com/'
# link_soporte = 'https://wa.link/tsi7us'
# pagina_web = 'https://www.sinboleto.com.mx'

nom_novia = 'Alejandra García'
nom_novio = 'Pedro Vaca'
fecha_evento = '7 de septiembre de 2024'
hora_inicio = '13:00 hrs'
lugar_evento = 'Tequisquiapan, Querétaro'
lugar_ceremonia = 'Hacienda Grande (https://maps.app.goo.gl/BcfhfmrGMJuLKKrz8)'
lugar_recepcion = 'en el mismo lugar'
codigo_vestimenta = 'formal'
link_mesa_regalos = 'https://dagiftmx.com/'
link_soporte = 'https://wa.link/9ncc9w'
pagina_web = 'https://www.sinboleto.com.mx'

# nom_novia = 'Julieta Rodríguez'
# nom_novio = 'Daniel Rosado'
# fecha_evento = '10 de febrero de 2024'
# hora_inicio = '17:30 hrs'
# lugar_evento = 'Mérida, Yucatán'
# lugar_ceremonia = 'la Rectoría de Nuestra Señora de Líbano'
# lugar_recepcion = 'en la Quinta Montes Molina'
# codigo_vestimenta = 'Mujeres - Formal | Hombres - Guayabera formal'
# link_mesa_regalos = 'https://dagiftmx.com/ver-evento?id=241&token'
# link_soporte = 'https://wa.link/pmx35g' # Revisar link
# pagina_web = 'https://www.theknot.com/us/julieta-rodriguez-and-daniel-rosado-feb-2024'

dict_variables_evento = {}

# Table config
try:
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'CREATE TABLE confirmaciones (id_evento TEXT, sid TEXT, nom_invitado TEXT, telefono TEXT, boletos INT, respuesta_1 TEXT, respuesta_2 INT, respuesta_3 TEXT, respuesta_4 TEXT);')
except psycopg2.errors.DuplicateTable:
    pass

try:
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'CREATE TABLE errores_confirmaciones (id_evento TEXT, nom_invitado TEXT, telefono TEXT, fecha DATE);')
except psycopg2.errors.DuplicateTable:
    pass

try:
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'CREATE TABLE info_eventos (id_evento TEXT, nom_novia TEXT, nom_novio TEXT, fecha_evento TEXT, hora_inicio TEXT, lugar_evento TEXT, lugar_ceremonia TEXT, lugar_recepcion TEXT, codigo_vestimenta TEXT, pagina_web TEXT, link_mesa_regalos TEXT, link_soporte TEXT);')
except psycopg2.errors.DuplicateTable:
    pass

# Inicio conversación
@app.route('/start', methods=['GET'])
def inicio_conversacion():
    global msg_conf
    global conversation_states
    global uploaded_json_file
    global uploaded_invitation_file
    global dict_info_invitados
    global url_invitacion
    global invitacion_carpeta

    media_url = 'https://confirmacion-app-ffd9bb8202ec.herokuapp.com/render_invitation'

    if uploaded_json_file.filename != '':
        for telefono_invitado in dict_info_invitados:

            try:

                conversation = conversations_client.conversations.create()
                # https://www.twilio.com/docs/conversations/api/conversation-message-resource asociar mensajes a conversaciones

                # Get the recipient_name dynamically for each recipient_phone_number
                nom_invitado = dict_info_invitados[telefono_invitado]['nom_invitado']
                boletos = dict_info_invitados[telefono_invitado]['num_boletos']

                if uploaded_invitation_file.filename == '':

                    if invitacion_carpeta == 'si':

                        # content_variables = json.dumps({"1":nom_invitado,"2":str(boletos),"3":nom_novia,"4":nom_novio,"5":fecha_evento,"6":hora_inicio,"7":lugar_evento}) # msg_conf
                        # content_variables = json.dumps({"1":nom_invitado,"2":nom_novia,"3":nom_novio,"4":fecha_evento,"5":hora_inicio,"6":lugar_evento,"7":str(boletos)}) # msg_invitacion
                        content_variables = json.dumps({"1":nom_invitado,"2":nom_novia,"3":nom_novio,"4":fecha_evento,"5":lugar_evento}) # msg_std
                        app.logger.info(json.dumps(content_variables))

                        UPLOAD_FOLDER = f'files/{id_evento}'  # Folder where uploaded files will be stored
                        app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

                        url_invitacion = os.path.join(app.config['UPLOAD_FOLDER'], f'{nom_invitado}.pdf')
                        app.logger.info(url_invitacion)

                        message = client.messages.create(
                            messaging_service_sid=messaging_service_sid,
                            from_=f'whatsapp:{twilio_phone_number}',
                            body='',
                            content_sid=content_SID_std,
                            content_variables=content_variables,
                            media_url=media_url,
                            to=f'whatsapp:{telefono_invitado}',
                        )

                    else:

                        content_variables = json.dumps({"1":nom_invitado,"2":fecha_evento,"3":nom_novia,"4":nom_novio,"5":lugar_evento}) # msg_std
                        app.logger.info(json.dumps(content_variables))

                        message = client.messages.create(
                            messaging_service_sid=messaging_service_sid,
                            from_=f'whatsapp:{twilio_phone_number}',
                            body='',
                            content_sid=content_SID_std,
                            content_variables=content_variables,
                            to=f'whatsapp:{telefono_invitado}',
                        )

                else:
                    
                    # content_variables = json.dumps({"1":nom_invitado,"2":str(boletos),"3":nom_novia,"4":nom_novio,"5":fecha_evento,"6":hora_inicio,"7":lugar_evento}) # msg_conf
                    # content_variables = json.dumps({"1":nom_invitado,"2":nom_novia,"3":nom_novio,"4":fecha_evento,"5":hora_inicio,"6":lugar_evento,"7":str(boletos)}) # msg_invitacion
                    content_variables = json.dumps({"1":nom_invitado,"2":fecha_evento,"3":nom_novia,"4":nom_novio,"5":lugar_evento}) # msg_std
                    app.logger.info(json.dumps(content_variables))

                    message = client.messages.create(
                        messaging_service_sid=messaging_service_sid,
                        from_=f'whatsapp:{twilio_phone_number}',
                        body='',
                        content_sid=content_SID_std,
                        content_variables=content_variables,
                        media_url=media_url,
                        to=f'whatsapp:{telefono_invitado}',
                    )

            except TwilioRestException as e:
                carga_SQL_errores(id_evento, nom_invitado, telefono_invitado)
                app.logger.error(f"Failed to send message to {telefono_invitado}: {str(e)}")
                # Continue the loop if sending the message fails for any specific recipient
                continue

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

            time.sleep(lag_msg)

        uploaded_json_file = ''
        uploaded_invitation_file = ''
        dict_info_invitados = {}
        invitacion_carpeta = 'no'

        return 'Confirmación enviada'
    else:
        return 'Subir archivo de base de datos'


def carga_SQL_confirmaciones(conversation_state):
    # Cargar datos en SQL
    with connection.cursor() as cursor:
        cursor.execute('INSERT INTO confirmaciones VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);',
                       (str(conversation_state['id_evento']),  # id_evento
                        str(conversation_state['sid']),  # sid
                        str(conversation_state['nom_invitado']), # nom_invitado
                        str(conversation_state['telefono']), # telefono
                        int(conversation_state['boletos']),  # boletos
                        str(conversation_state['respuestas'][0]), # respuesta_1
                        str(conversation_state['respuestas'][1]), # respuesta_2
                        str(conversation_state['respuestas'][2]), # respuesta_3
                        str(conversation_state['respuestas'][3]) # respuesta_4
                        )
                       )
        connection.commit()


def carga_SQL_errores(id_evento, nom_invitado, telefono):
    # Cargar datos en SQL
    with connection.cursor() as cursor:
        cursor.execute('INSERT INTO errores_confirmaciones VALUES (%s, %s, %s, %s);',
                       (str(id_evento),  # id_evento
                        str(nom_invitado), # nom_invitado
                        str(telefono), # telefono
                        date.today() # fecha
                        )
                       )
        connection.commit()

def carga_SQL_info_eventos(id_evento, nom_novia, nom_novio, fecha_evento, hora_inicio, lugar_evento, lugar_ceremonia, lugar_recepcion, codigo_vestimenta, pagina_web, link_mesa_regalos, link_soporte):
    # Cargar datos en SQL
    with connection.cursor() as cursor:
        cursor.execute('INSERT INTO info_eventos VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);',
                       (str(id_evento),
                        str(nom_novia),
                        str(nom_novio),
                        str(fecha_evento),
                        str(hora_inicio),
                        str(lugar_evento),
                        str(lugar_ceremonia),
                        str(lugar_recepcion),
                        str(codigo_vestimenta),
                        str(pagina_web),
                        str(link_mesa_regalos),
                        str(link_soporte)
                        )
                       )
        connection.commit()

def send_response(messaging_service_sid, content_sid, content_variables, media_url):

    # Create a response message
    response_message = {
        'messaging_service_sid': messaging_service_sid,
        'content_sid': content_sid,
        'content_variables': content_variables,
        'media_url': media_url
    }

    # Return the response as JSON
    return jsonify(response_message)

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
        num_user_answer = 'sin número'

    current_question_index = conversation_state['current_question_index']
    app.logger.info(current_question_index)

    msg_default = f'*Hola, soy un chatbot* 🤖 y estoy programado para hacer confirmaciones y brindar información general de eventos. *Cualquier otra duda*, haz click en el siguiente enlace: {link_soporte} y mandanos un mensaje. Gracias'

    if current_question_index == 0:
        if len(user_answer) < limite_msg:  # Verifica si hay choro
            if user_answer == 'si, confirmo' or user_answer == 'si':
                

                time.sleep(lag_msg)
                link_gc = 'https://calendar.google.com/calendar/event?action=TEMPLATE&tmeid=MDFmcWtiODFqNmNpZ3JrNXFmdmpuZjBzcmQgY181ZjQ1NTlhMjk1ZTIyNjAyNmQ5NzhjMzQzZmRkMWI4ZTVjYTBjODk5MjhhN2JlYjJjNzg2ZDNmN2E2MDA4ZTFkQGc&tmsrc=c_5f4559a295e226026d978c343fdd1b8e5ca0c89928a7beb2c786d3f7a6008e1d%40group.calendar.google.com'
                
                respuesta = f"""Muchas gracias por tu respuesta. Da click en el archivo enviado para agregarlo a tu calendario

También, te sugerimos los siguientes hoteles en caso de que desees hacer tu reservación:

- https://www.hotelsancarlostx.com/
- https://www.regalodelalma.com.mx/

Saludos
    """         
                UPLOAD_FOLDER = 'files'  # Folder where uploaded files will be stored
                app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

                filename = 'boda_A&P.ics'
                url_archivo = render_file()

                # app.logger.info(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                # media_url = 'https://confirmacion-app-ffd9bb8202ec.herokuapp.com/render_invitation'
                content_variables = json.dumps({"1":respuesta}) # msg_std

                # contenido_respuesta = {
                #     'content_sid': content_SID_texto_media,
                #     'content_variables': content_variables,
                #     'media_url': media_url,
                # }

                message = client.messages.create(
                        messaging_service_sid=messaging_service_sid,
                        from_=f'whatsapp:{twilio_phone_number}',
                        body='',
                        content_sid=content_SID_texto_media,
                        content_variables=content_variables,
                        media_url=url_archivo,
                        to=request.values.get('From', '').lower(),
                    )

                # response.message(str(jsonify(contenido_respuesta)))

                # response.message(f'content_sid: {content_SID_texto_media}')
                # response.message(f'content_variables: {content_variables}')
                # response.message(f'media_url: {media_url}')

                current_question_index += 1
                conversation_state['current_question_index'] = current_question_index

                conversation_state['current_question_index'] = current_question_index
                

            else:
                response.message('Muchas gracias por tu respuesta, que tengas un lindo día')

                current_question_index += 1
                conversation_state['current_question_index'] = current_question_index

                conversation_state['current_question_index'] = current_question_index

        else:
            # Si hay choro, manda el mensaje de revisión para referir al cliente a un operador
            time.sleep(lag_msg)
            message = client.messages.create(
                messaging_service_sid=messaging_service_sid,
                from_=f'whatsapp:{twilio_phone_number}',
                body=msg_default,
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

@app.route('/validacion_telefonos', methods=['POST'])
def validacion_telefonos():
    if 'xlsx_file' in request.files:
        uploaded_file = request.files['xlsx_file']

        if uploaded_file.filename.endswith('.xlsx'):
            # Read the contents of the Excel file into a DataFrame
            try:
                telefono_modificado = []
                df = pd.read_excel(uploaded_file, sheet_name='BD')

                for telefono in df['telefono']:
                    
                    if len(str(telefono)) == 10:
                        telefono_validado = f'+521{telefono}'
                        info_telefono = client.lookups.v2.phone_numbers(f'{telefono_validado}').fetch()
                    else:
                        info_telefono = client.lookups.v2.phone_numbers(f'+{telefono}').fetch()

                    if info_telefono.valid:
                        telefono_modificado.append(info_telefono.phone_number)
                    else:
                        telefono_modificado.append('Revisar número')


                df['telefono_modificado'] = telefono_modificado

                # Save the modified DataFrame to a new Excel file
                xlsx_filename = 'lista_invitados_validada.xlsx'
                df.to_excel(xlsx_filename, index=False)

                return send_file(xlsx_filename, as_attachment=True, download_name=xlsx_filename)

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
def upload_files():
    global id_evento
    global invitacion_carpeta
    global uploaded_json_file
    global uploaded_invitation_file
    global dict_info_invitados
    global url_invitacion
    global invitacion_carpeta

    id_evento = request.form.get('id_evento')  # Get the id_evento input value

    # if id_evento:
    #     data_evento = get_data(f"SELECT * FROM confirmaciones WHERE id_evento = {id_evento};")

    #     nom_novia = data_evento[0]
    #     nom_novio = data_evento[1]
    #     fecha_evento = data_evento[2]
    #     hora_inicio = data_evento[3]
    #     lugar_evento = data_evento[4]
    #     lugar_ceremonia = data_evento[5]
    #     lugar_recepcion = data_evento[6]
    #     codigo_vestimenta = data_evento[7]
    #     pagina_web = data_evento[8]
    #     link_mesa_regalos = data_evento[9]
    #     link_soporte = data_evento[10]

    # else:

    #     carga_SQL_info_eventos(id_evento, nom_novia, nom_novio, fecha_evento, hora_inicio, lugar_evento, lugar_ceremonia, lugar_recepcion, codigo_vestimenta, pagina_web, link_mesa_regalos, link_soporte)

    #     id_evento = request.form.get('id_evento')
    #     nom_novia = request.form.get('nom_novia_input')
    #     nom_novio = request.form.get('nom_novio_input')
    #     fecha_evento = request.form.get('fecha_evento_input')
    #     hora_inicio = request.form.get('hora_inicio_input')
    #     lugar_evento = request.form.get('lugar_evento_input')
    #     lugar_ceremonia = request.form.get('lugar_ceremonia_input')
    #     lugar_recepcion = request.form.get('lugar_recepcion_input')
    #     codigo_vestimenta = request.form.get('codigo_vestimenta_input')
    #     pagina_web = request.form.get('pagina_web_input')
    #     link_mesa_regalos = request.form.get('link_mesa_regalos_input')
    #     link_soporte = request.form.get('link_soporte_input')

    invitacion_carpeta = request.form.get('invitacion_carpeta')  # Get the id_evento input value
    app.logger.info(invitacion_carpeta)

    # Check if id_evento is empty
    if not id_evento:
        return 'El ID del evento es necesario. Favor de proporcionar un ID del evento y tratar de nuevo.'
    
    app.logger.info(request.files)

    for archivo in request.files:

        app.logger.info(archivo)

        if 'json_file' in archivo:
            uploaded_json_file = request.files['json_file']
            app.logger.info(uploaded_json_file)
            if uploaded_json_file.filename != '':
                # You can process the uploaded file here
                data = uploaded_json_file.read()
                # Convert data to a dictionary if it's in JSON format
                try:
                    json_data = json.loads(data)
                    # Update dict_info_invitados with the uploaded JSON data
                    dict_info_invitados = {}
                    for phone_number, info in json_data.items():
                        dict_info_invitados[phone_number] = info
                    app.logger.info(json.dumps(dict_info_invitados))
                except json.JSONDecodeError:
                    return 'Archivo JSON no válido.'
                
        if 'invitation_file' in archivo:
            uploaded_invitation_file = request.files['invitation_file']
            app.logger.info(uploaded_invitation_file)
            if uploaded_invitation_file.filename != '':

                UPLOAD_FOLDER = 'files'  # Folder where uploaded files will be stored
                app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

                file_extension = os.path.splitext(uploaded_invitation_file.filename)[1]
                filename = f'invitacion_{id_evento}{file_extension}'
                app.logger.info(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                uploaded_invitation_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                # Generating URL for the uploaded text file
                url_invitacion = url_for('get_uploaded_file', filename=filename) # Ver si esto es necesario
                app.logger.info(url_invitacion)
    
    return redirect(url_for('upload_form'))

@app.route('/uploaded_file/<filename>')
def get_uploaded_file(filename):
    # Your logic to handle the uploaded text file and return a response
    return f'Text file: {filename}'

@app.route('/render_invitation')
def render_invitation():
    global url_invitacion
    # Assuming 'UPLOAD_FOLDER' is the directory where the files are uploaded
    # Extracting the filename from the URL (assuming it's the last part of the URL)
    filename = url_invitacion.rsplit('/', 1)[-1]
    
    # Send the file from the directory to the client
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def render_file(filename):
    # Assuming 'UPLOAD_FOLDER' is the directory where the files are uploaded
    # Assuming 'get_uploaded_file' is a valid route to serve the file
    url_file = url_for('get_uploaded_file', filename=filename)
    
    # Send the file from the directory to the client
    send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    return url_file

# Function to retrieve data from the database
def get_data(query):
    data = []
    connection = psycopg2.connect(POSTGRESQL_URI)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            data = cursor.fetchall()
    return data

def clean_text(text):
    articles = ['el', 'la', 'los', 'las', 'un',
                'una', 'unos', 'unas', 'lo', 'al', 'del']
    conjunctions = ['y', 'e', 'ni', 'que', 'o', 'u', 'pero', 'aunque',
                    'sin embargo', 'por lo tanto', 'así que', 'porque', 'ya que']
    pattern = r'\b(?:' + '|'.join(articles + conjunctions) + r')\b'
    text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    text = text.translate(str.maketrans('', '', string.punctuation))
    
    numbers_to_replace = {
        'una': '1', 'uno': '1', 'dos': '2', 'tres': '3', 'cuatro': '4',
        'cinco': '5', 'seis': '6', 'siete': '7', 'ocho': '8', 'nueve': '9',
    }
    
    for word, digit in numbers_to_replace.items():
        text = re.sub(r'\b' + word + r'\b', digit, text, flags=re.IGNORECASE)

    return unidecode(text).strip()

def process_restriction(text, dict_equivalencias):
    text = clean_text(text)
    substrings = re.split(r'\b(?=\d+\D|$)', text)
    substrings = [s for s in substrings if s != '']
    processed_substrings = []

    for substring in substrings:
        if re.search(r'\b\d+\b', substring) and not re.search(r'\b(?!\d+\b)\w+\b', substring):
            substring = f'{substring} no especificado'

        num_encontrados = sum([1 for category in dict_equivalencias.keys() if category in substring])
        
        if num_encontrados > 1:
            substring = '1 varios'
        elif num_encontrados == 1 and not re.search(r'\b\d+\b', substring):
            substring = f'1 {substring}'
        elif num_encontrados == 0:
            substring = '1 otro'

        processed_substrings.append(substring)

    return processed_substrings


def summarize_restrictions(df_restricciones, dict_equivalencias):
    df_restricciones['tipo_restricciones'] = df_restricciones['respuesta_4'].apply(
        lambda x: process_restriction(x, dict_equivalencias))

    lista_restricciones = df_restricciones['tipo_restricciones'].explode().tolist()
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
    resumen_restricciones = {key: value for key, value in resumen_restricciones.items() if value != 0}

    return resumen_restricciones

def visualize_summary(summary):
    categories = list(summary.keys())
    values = list(summary.values())
    width = 0.25

    plt.figure()
    bottom = np.zeros(len(categories))
    altura = 0
    colors = ['#5C80A0','#6A8EAC','#759FBC','#80ACCA','#8EBAD6','#9EC8E2','#ADC6D9','#B7D3E6']
    colors = colors[0:len(categories)]

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
    plot_base64 = base64.b64encode(buffer.getvalue()).decode()

    return plot_base64
    

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
    dict_equivalencias = {
        'alergi': 'Alérgico',
        'vegan': 'Vegano',
        'vegetarian': 'Vegetariano',
        'celiac': 'Celiaco', 
        'intol':'Intolerante',
        'no especificado': 
        'No especificado',
        'otro': 'Otro', 
        'varios':'+1 restricción',
    }

    summary = summarize_restrictions(df_restricciones, dict_equivalencias)
    plot3_base64 = visualize_summary(summary)

    return render_template('dashboard.html', id_evento_values=id_evento_values, data=data, plot1_base64=plot1_base64, plot2_base64=plot2_base64, plot3_base64=plot3_base64)

# Dashboard
@app.route('/dashboard_eventos/<id_evento>', methods=['GET', 'POST'])
def dashboard_eventos(id_evento):

    data = get_data(
            f"SELECT id_evento, nom_invitado, boletos, respuesta_1, respuesta_2, respuesta_3, respuesta_4 FROM confirmaciones WHERE id_evento ='{id_evento}' ORDER BY id_evento;")

    columnas = ['id_evento', 'nom_invitado', 'boletos',
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
    df_restricciones = df[df['respuesta_3'] == 'Si'].drop(columns=['id_evento', 'nom_invitado', 'boletos',
                                                                   'respuesta_1', 'respuesta_2', 'respuesta_3'])

    # Equivalencias
    dict_equivalencias = {
        'alergi': 'Alérgico',
        'vegan': 'Vegano',
        'vegetarian': 'Vegetariano',
        'celiac': 'Celiaco', 
        'intol':'Intolerante',
        'no especificado': 
        'No especificado',
        'otro': 'Otro', 
        'varios':'+1 restricción',
    }

    summary = summarize_restrictions(df_restricciones, dict_equivalencias)
    plot3_base64 = visualize_summary(summary)

    return render_template('dashboard_eventos.html', data=data, plot1_base64=plot1_base64, plot2_base64=plot2_base64, plot3_base64=plot3_base64)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
