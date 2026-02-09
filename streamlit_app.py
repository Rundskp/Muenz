import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro", layout="centered")
st.title("🪙 Münz-Detektiv")

# Sicherstellen, dass der Key da ist
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Wir nutzen hier die stabilste Modell-Bezeichnung
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.error("🔑 API-Key fehlt in den Secrets!")
    st.stop()

# --- UPLOAD ---
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="Deine Münze", use_container_width=True)

    if st.button("Münze analysieren"):
        with st.spinner("KI identifiziert das Stück..."):
            try:
                # Ein extrem starker Prompt für historische Goldmünzen
                prompt = """
                Verhalte dich wie ein Experte für Numismatik. Identifiziere diese Münze präzise:
                1. Welcher Herrscher oder welches Land?
                2. Ungefähres Prägejahr oder Epoche?
                3. Nominal (z.B. Dukat, Gulden, Solidus)?
                4. Was für Motive sind auf den Bildern zu sehen?
                5. Schätze das Material (Gold/Silber/Kupfer).
                """
                response = model.generate_content([prompt, img])
                st.success("Analyse abgeschlossen!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Fehler: {e}")
                st.info("Falls der Fehler 404 bleibt, wurde die requirements.txt noch nicht fertig geladen.")

    # --- MESSEN ---
    st.divider()
    st.subheader("📏 Durchmesser")
    ppi = st.slider("Display-Kalibrierung (Handy-PPI)", 100, 600, 160)
    size = st.slider("Kreisgröße", 50, 600, 250)
    mm = (size / ppi) * 25.4
    st.metric("Berechneter Durchmesser", f"{mm:.1f} mm")
    st.markdown(f'<div style="width:{size}px; height:{size}px; border:4px solid gold; border-radius:50%; margin:auto;"></div>', unsafe_allow_html=True)
