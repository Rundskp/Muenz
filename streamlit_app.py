import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageEnhance
import json
import collections

# --- SETUP & SESSION STATE ---
st.set_page_config(page_title="MuenzID Pro - Ultra", layout="centered")
st.title("🪙 Münz-Detektiv: Universal-Prüfer + Feedback")

# Persistenten Speicher für Analyse-Ergebnisse initialisieren
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# API-Konfiguration
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- INPUT-BEREICH ---
st.sidebar.header("📏 Kalibrierung")
ppi = st.sidebar.slider("Handy-PPI", 100, 600, 160)
size = st.sidebar.slider("Kreisgröße", 50, 600, 125)
mm_wert = (size / ppi) * 25.4 # Durchmesser-Formel: $mm = \frac{size}{ppi} \cdot 25.4$

uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

def run_analysis(image, user_hint=None):
    """Führt die 5-fache Analyse durch, optional mit Korrektur-Hinweis."""
    results_pool = []
    
    # Vorbereitung für die KI
    processed_img = ImageEnhance.Contrast(image).enhance(1.6)
    processed_img = ImageEnhance.Sharpness(processed_img).enhance(2.0)
    
    hint_context = f"\nKRITISCHER HINWEIS VOM NUTZER: '{user_hint}'. Prüfe das Bild erneut mit Fokus auf diesen Hinweis!" if user_hint else ""

    with st.spinner("KI-Abgleich läuft..."):
        for i in range(5):
            prompt = f"""
            Du bist ein numismatischer Experte. Durchmesser: {mm_wert:.1f} mm. {hint_context}
            
            1. ANALYSE: Metall, Wappenfelder, Legende, Portrait.
            2. IDENTIFIKATION: Land, Herrscher, Ära, Nominal.
            3. VERIFIKATION: Erzeuge einen Google-Suchlink basierend auf deiner Bestimmung.

            Antworte STRENG im JSON-Format:
            {{
              "Bestimmung": "Land, Nominal, Herrscher",
              "Jahr": "Zeitraum",
              "Gelesen": "Transkription",
              "Link": "Google-Suchlink",
              "Begruendung": "Warum ist es dieses Stück?"
            }}
            """
            try:
                response = model.generate_content([prompt, processed_img])
                data = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                results_pool.append(data)
            except:
                continue
    return results_pool

# --- HAUPT-LOGIK ---
if uploaded_file:
    raw_img = Image.open(uploaded_file)
    st.image(raw_img, caption=f"Erfasste Münze ({mm_wert:.1f} mm)", use_container_width=True)

    # Erstanalyse
    if st.button("🔍 Analyse & Kontroll-Link generieren"):
        results = run_analysis(raw_img)
        if results:
            bestimmungen = [r['Bestimmung'] for r in results]
            most_common = collections.Counter(bestimmungen).most_common(1)[0]
            st.session_state.analysis_result = next(r for r in results if r['Bestimmung'] == most_common[0])

    # Anzeige der Ergebnisse (wenn vorhanden)
    if st.session_state.analysis_result:
        res = st.session_state.analysis_result
        st.divider()
        st.success(f"**Ergebnis:** {res['Bestimmung']} ({res['Jahr']})")
        st.info(f"**Analyse:** {res['Begruendung']}")
        
        # DER KONTROLL-LINK
        st.markdown(f"### 🔗 [HIER KLICKEN: Ergebnis auf Google prüfen]({res['Link']})")
        
        # KORREKTUR-BEREICH
        st.divider()
        st.subheader("🛠️ Korrektur-Modus")
        st.write("War das Ergebnis falsch? Gib der KI einen Tipp (z.B. den richtigen Herrscher) für eine präzisere Re-Analyse.")
        
        correction_hint = st.text_input("Dein Hinweis / Richtige Bestimmung:")
        if st.button("🔄 Re-Analyse mit Korrektur-Tipp"):
            if correction_hint:
                results = run_analysis(raw_img, user_hint=correction_hint)
                if results:
                    st.session_state.analysis_result = results[0] # Nehme direkt das Ergebnis der Korrektur
                    st.rerun()
            else:
                st.warning("Bitte gib einen Hinweis ein.")
