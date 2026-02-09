import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageEnhance
import json
import collections
import urllib.parse

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro - Ultra", layout="centered")
st.title("🪙 Münz-Detektiv: Profi-Handel & Wappen-Check")

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- PARAMETER ---
st.sidebar.header("📏 Kalibrierung")
ppi = st.sidebar.slider("Handy-PPI", 100, 600, 160)
size = st.sidebar.slider("Kreisgröße", 50, 600, 125)
mm_wert = (size / ppi) * 25.4

def run_pro_analysis(image, user_hint=None):
    # Silent Image Prep
    enhanced = ImageEnhance.Contrast(image).enhance(1.8)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(2.0)
    
    hint_context = f"\nKorrektur-Vorgabe: '{user_hint}'" if user_hint else ""

    prompt = f"""
    Du bist ein Experte für Münzhandel und Numismatik. Durchmesser: {mm_wert:.1f} mm. {hint_context}

    DEINE AUFGABE:
    1. WAPPEN-KARTE: Beschreibe das Wappen feldweise (Oben Links, Oben Rechts, etc.). 
       Nenne NUR was du siehst. Wenn du keinen Adler siehst, schreibe 'Kein Adler'.
    2. TEXT-TRANSKRIPTION: Suche nach Monogrammen (z.B. F-I, MT), Wertangaben (z.B. 3, 1) und Legenden.
    3. HANDELS-CHECK: Welches Nominal wird auf Profi-Seiten (Numista, MA-Shops) für diese Größe gehandelt?

    Antworte NUR als JSON:
    {{
      "Bestimmung": "Exaktes Land, Nominal, Herrscher",
      "Wappen_Analyse": "Feld-für-Feld Beschreibung",
      "Legende": "Gelesener Text",
      "Handels_Keywords": "Die 3-4 wichtigsten Begriffe für eine Fachsuche",
      "Begruendung": "Warum passt das Wappen zu diesem Herrscher?",
      "Konfidenz": "0-100%"
    }}
    """
    try:
        response = model.generate_content([prompt, enhanced])
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except:
        return None

# --- UI ---
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    st.image(raw_img, caption=f"Analyse-Objekt ({mm_wert:.1f} mm)", use_container_width=True)

    if st.button("🔍 Profi-Analyse starten"):
        result = run_pro_analysis(raw_img)
        if result:
            st.session_state.analysis_result = result

    if st.session_state.analysis_result:
        res = st.session_state.analysis_result
        st.divider()
        
        # Profi-Link Generator
        # Wir bauen den Link manuell, um sicherzugehen, dass er auf Fachseiten landet
        search_query = f"{res['Bestimmung']} {res['Handels_Keywords']} {mm_wert:.1f}mm"
        encoded_query = urllib.parse.quote(search_query)
        
        # Wir bieten Links zu den wichtigsten Profi-Plattformen an
        numista_link = f"https://en.numista.com/catalogue/index.php?q={encoded_query}"
        mashops_link = f"https://www.ma-shops.de/result.php?searchstr={encoded_query}"
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"**Ergebnis:** {res['Bestimmung']}")
            st.write(f"**Wappen:** {res['Wappen_Analyse']}")
        with col2:
            st.write(f"**Legende:** `{res['Legende']}`")
            st.write(f"**Konfidenz:** {res['Konfidenz']}")

        st.info(f"**Händler-Check:** {res['Begruendung']}")

        st.markdown("### 🏆 Profi-Kontroll-Links")
        st.markdown(f"👉 [Auf **Numista** prüfen (Weltgrößte Datenbank)]({numista_link})")
        st.markdown(f"👉 [Auf **MA-Shops** prüfen (Aktueller Handel)]({mashops_link})")

        # Korrektur
        with st.expander("🛠️ Wappen oder Name korrigieren"):
            hint = st.text_input("Was hat die KI übersehen? (z.B. 'Es ist ein Löwe, kein Adler')")
            if st.button("Re-Analyse mit Hinweis"):
                new_res = run_pro_analysis(raw_img, user_hint=hint)
                if new_res:
                    st.session_state.analysis_result = new_res
                    st.rerun()
