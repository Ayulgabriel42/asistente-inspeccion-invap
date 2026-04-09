from google import genai
import streamlit as st

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

print("--- CATALOGO REAL DE MODELOS INVAP ---")
try:
    modelos = client.models.list()
    for m in modelos:
        # Esto imprime el ID exacto que tenemos que poner en el código
        print(f"ID para el código: {m.name}")
except Exception as e:
    print(f"Falla al listar: {e}")