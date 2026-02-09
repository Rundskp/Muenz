import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- KONFIGURATION ---
st.set_page_config(page_title="CoinID Pro", layout="centered")
st.title("🪙 Münz-Detektiv")

# API-Key Check
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Hier nutzen wir den stabilen Namen ohne v1beta-Präfix
    model = genai.GenerativeModel('gemini-1.5-flash') 
else:
    st.warning("🔑 Bitte trage deinen API-Key in den Streamlit-Secrets ein.")
    st.stop()

# --- BILD-UPLOAD ---
uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="Deine Münze", use_container_width=True)

    if st.button("Münze analysieren"):
        with st.spinner("KI durchsucht die Datenbanken..."):
            try:
                # Spezial-Prompt für deine mittelalterliche Goldmünze
                prompt = """
                Analysiere diese Münze im Detail. Es scheint eine historische Goldmünze zu sein. 
                Gib mir:
                1. Herrscher/Land (z.B. Matthias Corvinus, Ungarn)
                2. Ungefähres Jahr/Epoche
                3. Nominal (z.B. Dukat oder Goldgulden)
                4. Beschreibung der Symbole (z.B. Madonna, Heiliger Ladislaus)
                """
                response = model.generate_content([prompt, img])
                st.success("Analyse erfolgreich!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Technischer Fehler: {e}")
                st.info("Tipp: Überprüfe, ob dein API-Key in Google AI Studio noch aktiv ist.")

    # --- DURCHMESSER ---
    st.divider()
    st.subheader("📏 Durchmesser bestimmen")
    ppi = st.slider("Display-Kalibrierung (PPI)", 100, 600, 450)
    size = st.slider("Kreisgröße", 50, 500, 250)
    mm = (size / ppi) * 25.4
    st.metric("Durchmesser", f"{mm:.1f} mm")
    st.markdown(f'<div style="width:{size}px; height:{size}px; border:4px solid gold; border-radius:50%; margin:auto;"></div>', unsafe_allow_html=True)
