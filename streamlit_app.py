import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- KONFIGURATION ---
st.set_page_config(page_title="CoinID Pro", layout="centered")
st.title("🪙 Münz-Detektiv")

# Sicherer Abruf des API-Keys aus den Streamlit Secrets
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.warning("🔑 Bitte hinterlege den GOOGLE_API_KEY in den Streamlit Secrets.")
    st.stop()

# --- BILD-UPLOAD ---
uploaded_file = st.file_uploader("Bild der Münze (Vorder- & Rückseite)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # Bild laden
    img = Image.open(uploaded_file)
    st.image(img, caption="Deine Münze", use_container_width=True)

    # --- ANALYSE ---
    if st.button("Münze analysieren"):
        with st.spinner("KI identifiziert die Münze..."):
            try:
                # Der Prompt sagt der KI exakt, was sie tun soll
                prompt = """
                Analysiere diese Münze. Gib mir folgende Infos als Liste:
                - Land & Epoche
                - Jahr
                - Nennwert
                - Material (Schätzung)
                - Kurze Beschreibung des Motivs
                """
                response = model.generate_content([prompt, img])
                
                st.success("Analyse fertig!")
                st.subheader("Ergebnis:")
                st.write(response.text)
                
                # Merken der Daten für den Download (simpel gelöst)
                st.session_state['last_analysis'] = response.text
                
            except Exception as e:
                st.error(f"Fehler bei der Anfrage: {e}")

    # --- DURCHMESSER & EXPORT ---
    st.divider()
    st.subheader("📏 Durchmesser & Metadaten")
    
    col1, col2 = st.columns(2)
    with col1:
        ppi = st.number_input("Kalibrierung (PPI deines Handys)", value=450)
        size = st.slider("Kreis anpassen", 50, 600, 250)
    
    with col2:
        mm = (size / ppi) * 25.4
        st.metric("Durchmesser", f"{mm:.1f} mm")

    # Der virtuelle Messkreis
    st.markdown(f"""
        <div style="width:{size}px; height:{size}px; border:4px solid gold; border-radius:50%; margin:20px auto;"></div>
    """, unsafe_allow_html=True)

    if st.button("Ergebnis als Bild mit Info speichern"):
        # Wir speichern das Bild einfach neu ab
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        st.download_button(
            label="Download: Münze_mit_Daten.jpg",
            data=buf.getvalue(),
            file_name="muenze_identifiziert.jpg",
            mime="image/jpeg"
        )
