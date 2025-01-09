import os
import json
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from charset_normalizer import detect
from googleapiclient.errors import HttpError
import datetime

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# Accede a las credenciales almacenadas en Streamlit Secrets
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
print(f"SERVICE_ACCOUNT_INFO es tipo: ",type(SERVICE_ACCOUNT_INFO))  # Debería imprimir "<class 'dict'>"
# Cargar las credenciales del archivo JSON desde los secrets
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=['https://www.googleapis.com/auth/spreadsheets'])

# Configuración de Google Sheets
SPREADSHEET_ID = '17JNssIIZDMUpspZl1F1HXMJLBehNQKFf9Ke4KD2WkT8'

# Configuración de las rutas
DORSO_PATH = "cards/Dorso.png"
CARPETA_CARTAS = "cards"

# Función para conectar con Google Sheets
def conectar_google_sheets():
    try:
        service = build('sheets', 'v4', credentials=creds)
        
        # Agregar un mensaje para confirmar que la autenticación fue exitosa
        print("Autenticación con Google Sheets exitosa.")
        
        return service
    except Exception as e:
        print(f"Error al conectar con Google Sheets: {e}")
        return None

# Función para leer datos de Google Sheets
def leer_datos_sheets(service, rango):
    try:
        # Utilizamos el servicio completo para acceder a la hoja de cálculo
        sheet = service.spreadsheets()
        print(f"Leyendo el rango: {rango} del archivo con ID: {SPREADSHEET_ID}")
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=rango).execute()
        values = result.get('values', [])

        if values:
            print(f"Datos obtenidos del rango {rango}: {values}")
            return values
        else:
            print(f"No se encontraron datos en el rango {rango}.")
            return []
    except HttpError as http_error:
        print(f"Error al leer los datos de Google Sheets: {http_error}")
        return []
    except Exception as e:
        print(f"Error inesperado: {e}")
        return []

def verificar_usuario(service, correo):
    # Leer los datos desde Google Sheets
    datos_existentes = leer_datos_sheets(service, "usuarios!A:D")  # Base de usuarios
    print(f"Datos obtenidos de Google Sheets: {datos_existentes}")

    # Convertir los datos obtenidos a un DataFrame de pandas
    datos_existentes_df = pd.DataFrame(datos_existentes, columns=["nombre_usuario", "email_usuario", "carta_que_le_toco","timestamp"])
    print(f"Datos convertidos a DataFrame:\n{datos_existentes_df}")

    # Filtrar el DataFrame para buscar el usuario por correo
    usuario = datos_existentes_df[datos_existentes_df["email_usuario"] == correo]
    if not usuario.empty:
        # Si el usuario existe, obtener el valor de la carta que le tocó
        carta_codigo = usuario.iloc[0]["carta_que_le_toco"]
        
        # Si la carta es un valor válido (no None o NaN), devolverlo
        if pd.notna(carta_codigo):
            return carta_codigo
    
    # Si no se encuentra el usuario o la carta, devolver None
    return None



# Escribir datos en Google Sheets utilizando append
def escribir_datos_sheets(service, rango, valores):
    body = {
        "values": valores
    }

    # Imprimir la llamada a la API antes de hacerla
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{rango}:append"
    params = {
        "valueInputOption": "RAW",  # Puedes usar "RAW" o "USER_ENTERED"
        "alt": "json"
    }
    print("Llamada a la API:")
    print(f"URL: {url}")
    print(f"Parámetros: {params}")
    print(f"Cuerpo: {body}")

    # Usamos append para agregar los datos al final de la hoja
    response = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=rango,
        valueInputOption="RAW",  # Puedes usar "RAW" o "USER_ENTERED"
        body=body
    ).execute()

    # Imprimir la respuesta de la API
    print("¡Datos añadidos al final de la hoja!")
    print("Respuesta de la API:")
    print(response)  # Esto imprimirá los detalles de la respuesta

# Validar correo electrónico
def validar_email(correo):
    import re
    patron = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(patron, correo) is not None

# Verificar imagen
def verificar_imagen(ruta):
    return os.path.exists(ruta)

# Guardar datos del usuario en Google Sheets
def guardar_datos_usuario(service, nombre, correo, carta):
    # Obtener los datos de la hoja de cálculo (como lista)
    datos_existentes = leer_datos_sheets(service, "usuarios!A:D")  # Cambiar rango a A:D (para incluir la nueva columna)
    
    # Convertir los datos a DataFrame
    if datos_existentes:
        df = pd.DataFrame(datos_existentes[1:], columns=datos_existentes[0])  # Usa la primera fila como columnas
        
        # Verificar si el DataFrame no está vacío y si el correo ya existe
        if not df.empty and correo in df["email_usuario"].values:
            return  # El correo ya está registrado
    
    # Si el correo no está registrado, agregar el nuevo usuario con el timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Obtener el timestamp actual
    nuevo_usuario = [nombre, correo, carta, timestamp]  # Añadir el timestamp como cuarta columna
    values = [nuevo_usuario]
    
    # Escribir los datos del nuevo usuario en la hoja
    escribir_datos_sheets(service, "usuarios!A:D", values)  # Actualizar el rango para incluir la nueva columna




# Función para eliminar el registro de un usuario en Google Sheets (por correo)
def eliminar_registro_usuario(sheet, correo):
    # Leer los datos desde Google Sheets
    datos_existentes = leer_datos_sheets(sheet, "usuarios!A:C")
    
    # Convertir los datos obtenidos a un DataFrame de pandas
    datos_existentes_df = pd.DataFrame(datos_existentes, columns=["nombre_usuario", "email_usuario", "carta_que_le_toco"])
    
    # Filtrar el DataFrame para encontrar el registro del usuario
    datos_actualizados_df = datos_existentes_df[datos_existentes_df["email_usuario"] != correo]
    
    # Convertir de nuevo a una lista de listas (sin el registro del usuario)
    datos_actualizados = datos_actualizados_df.values.tolist()
    
    # Escribir los datos actualizados en Google Sheets, eliminando el registro
    escribir_datos_sheets(sheet, "usuarios!A:C", datos_actualizados)
    print(f"El registro del usuario {correo} ha sido eliminado.")

# Detectar codificacion del csv
def detectar_codificacion(filepath):
    with open(filepath, 'rb') as f:
        result = detect(f.read())
    return result['encoding']
# Cargar datos del tarot
def cargar_tarot():
    data_path = "cartas_bdd.csv"
    if os.path.exists(data_path):
        return pd.read_csv(data_path, delimiter=";", encoding=detectar_codificacion(data_path))
    else:
        st.error("No se encontró el archivo de datos del tarot.")
        return None

def obtener_carta_por_codigo(df, codigo):
     # Asegura que el código sea del mismo tipo que el de la columna
    codigo = str(codigo)  # Convierte el código a string, si es necesario
    # Filtra el DataFrame para obtener la fila con el código
    carta = df[df["codigo"].astype(str) == codigo]
    
    # Si la carta fue encontrada
    if not carta.empty:
        # Accede a la primera fila con iloc (en caso de que haya múltiples coincidencias)
        carta = carta.iloc[0]
        return carta
    else:
        return None

# Función principal de la aplicación
def main():
    st.title("\u2728 Lectura de Tarot \u2728")
    service=conectar_google_sheets()
    tarot_data = cargar_tarot()

    if tarot_data is not None:
        if "cartas_seleccionadas" not in st.session_state:
            st.session_state["cartas_seleccionadas"] = []
            st.session_state["cartas_volteadas"] = [False, False, False]
            st.session_state["cartas_mostradas"] = [True, True, True]
            st.session_state["card_chosen"] = None
            st.session_state["nombre"] = ""
            st.session_state["correo"] = ""
            st.session_state["show_form"] = True
            st.session_state["email_valido"] = False
            st.session_state["carta_seleccionada"] = False
            print("Este es el inicio, aqui las cartas seleccionadas son: ",st.session_state["cartas_seleccionadas"])

        if st.session_state["show_form"]:
            st.write("Por favor ingresa tu nombre y dirección de correo:")

            nombre = st.text_input("Nombre", value=st.session_state["nombre"])
            correo = st.text_input("Correo electrónico", value=st.session_state["correo"])

            if correo and not validar_email(correo):
                st.error("Email inválido, ingresa un email válido.")
                st.session_state["email_valido"] = False
            else:
                st.session_state["email_valido"] = True

            if nombre and correo and st.session_state["email_valido"]:
                habilitar_boton = True
            else:
                habilitar_boton = False

            if st.button("Consultar el tarot", disabled=not habilitar_boton):
                st.session_state["nombre"] = nombre
                st.session_state["correo"] = correo
                carta_asignada = verificar_usuario(service, correo)
                print(f"La carta asignada es: ",carta_asignada)

                if carta_asignada:
                    print(f'Este es el 1.5, aqui la carta asginada es: ',carta_asignada)
                    st.session_state["cartas_seleccionadas"] = tarot_data[
                        tarot_data["codigo"].astype(str) == str(carta_asignada)
                    ][["codigo", "carta_esp", "descrip", "como_afecta_year"]].to_dict(orient="records")
                    st.session_state["cartas_volteadas"] = [True]
                    st.session_state["cartas_mostradas"] = [True]
                    st.session_state["card_chosen"] = carta_asignada
                    st.session_state["carta_seleccionada"] = True
                    print("Este es el segundo, aqui las cartas seleccionadas son: ",st.session_state["cartas_seleccionadas"])
                    print("y la carta asignada aqui es :", carta_asignada)
                    print(tarot_data)
                else:
                    seleccionadas = tarot_data.sample(3)
                    st.session_state["cartas_seleccionadas"] = seleccionadas[
                        ["codigo", "carta_esp", "descrip", "como_afecta_year"]
                    ].to_dict(orient="records")
                    st.session_state["cartas_volteadas"] = [False, False, False]
                    st.session_state["cartas_mostradas"] = [True, True, True]
                    st.session_state["card_chosen"] = None
                    st.session_state["carta_seleccionada"] = False
                    print("Este es el tercero, aqui las cartas seleccionadas son: ",st.session_state["cartas_seleccionadas"])

                st.session_state["show_form"] = False
                st.rerun()

        if not st.session_state["show_form"]:
            if not st.session_state["carta_seleccionada"]:
                st.subheader("Elige una carta para verla")

            cols = st.columns(3)
            for i, carta in enumerate(st.session_state["cartas_seleccionadas"]):
                with cols[i]:
                    if st.session_state["cartas_mostradas"][i]:
                        if not st.session_state["cartas_volteadas"][i]:
                            if st.button(f"Voltear carta {i+1}", key=f"voltear_{i}"):
                                st.session_state["cartas_volteadas"][i] = True
                                st.session_state["cartas_mostradas"] = [False, False, False]
                                st.session_state["cartas_mostradas"][i] = True
                                st.session_state["card_chosen"] = carta["codigo"]
                                st.session_state["carta_seleccionada"] = True
                                st.rerun()
                                print("Este es el cuarto, aqui las cartas seleccionadas son: ",st.session_state["cartas_seleccionadas"])
                            if verificar_imagen(DORSO_PATH):
                                st.image(DORSO_PATH, use_container_width=True, caption=f"Carta {i+1}")

            if st.session_state["card_chosen"]:
                print("Las cartas seleccionadas son: ")
                print(st.session_state["cartas_seleccionadas"])
                print("Las card_chosen son: ")
                print(st.session_state["card_chosen"])
                carta_seleccionada = next(
                    c for c in st.session_state["cartas_seleccionadas"] if str(c["codigo"]) == str(st.session_state["card_chosen"])
                )
                cols = st.columns([2, 2])

                with cols[0]:
                    ruta_carta = os.path.join(CARPETA_CARTAS, f"{carta_seleccionada['codigo']}.png")
                    if verificar_imagen(ruta_carta):
                        st.image(ruta_carta, width=int(300 * 0.7))

                with cols[1]:
                    print(f"Carta seleccionada: ", carta_seleccionada)
                    st.markdown(f"### **{carta_seleccionada['carta_esp']}**")
                    st.write(f"**Descripción:** {carta_seleccionada['descrip']}")
                    st.write(f"**¿Cómo afecta este año?:** {carta_seleccionada['como_afecta_year']}")

                if not verificar_usuario(service,st.session_state["correo"]):
                    guardar_datos_usuario(service,
                        st.session_state["nombre"], st.session_state["correo"], st.session_state["card_chosen"]
                    )
 
# Ejecutar la aplicación
if __name__ == "__main__":
    main()
