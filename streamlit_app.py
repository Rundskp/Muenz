import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- SETUP ---
st.set_page_config(page_title="CoinID - Münz-Erkennung", layout="wide")
st.title("🪙 Münz-Detektiv")

# API Key Eingabe (In Streamlit Cloud über "Secrets" lösen)
api_key = st.sidebar.text_input("Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash') # Schnell & gut für Bilder

# --- BILD UPLOAD ---
uploaded_file = st.file_uploader("Bild der Münze hochladen (Vorder- & Rückseite)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="Hochgeladene Münze", width=400)

    if st.button("Münze analysieren"):
        with st.spinner("KI durchsucht Datenbanken..."):
            # Prompt für die KI
            prompt = """
            Analysiere diese Münze (Vorder- und Rückseite). Gib folgende Infos im JSON-Format aus:
            - Material (Schätzung)
            - Jahr
            - Land
            - Nennwert
            - Motiv_Vorderseite
            - Motiv_Rückseite
            - Inschriften
            - Geschätzter_Typ (z.B. 'Umlaufmünze', 'Gedenkmünze')
            Suche nach Übereinstimmungen in Katalogen wie Numista.
            """
            response = model.generate_content([prompt, img])
            st.subheader("Ergebnis der Analyse")
            st.write(response.text)

    # --- DURCHMESSER-DETEKTION (TOUCH-SIMULATION) ---
    st.divider()
    st.subheader("📏 Durchmesser bestimmen")
    st.info("Lege die echte Münze auf das Display und passe den Kreis an.")
    
    # Kalibrierungs-Faktor (Pixel zu mm) - muss je nach Gerät angepasst werden
    ppi = st.number_input("Display-Kalibrierung (PPI deines Geräts)", value=450) 
    
    diameter_pixel = st.slider("Kreisgröße anpassen", 50, 800, 200)
    real_mm = (diameter_pixel / ppi) * 25.4
    
    # Ein einfacher Kreis via HTML/CSS
    st.markdown(f"""
        <div style="
            width: {diameter_pixel}px; 
            height: {diameter_pixel}px; 
            border: 5px solid gold; 
            border-radius: 50%; 
            margin: auto;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        ">
            {real_mm:.1f} mm
        </div>
    """, unsafe_allow_html=True)

    # --- SPEICHERN ---
    if st.button("Daten in Metadaten speichern & Bild downloaden"):
        # Hier würde die Pillow-Logik stehen, um EXIF-Daten zu schreiben
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        st.download_button("Bild mit Metadaten laden", buf.getvalue(), "muenze_erkannt.jpg")
