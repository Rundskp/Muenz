import streamlit as st
from google import genai
from PIL import Image, ImageEnhance, ImageOps # ImageOps ist neu
import json
import urllib.parse
import io

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro - Systematik", layout="wide")
st.title("🪙 Münz-Detektiv: Systematische Hierarchie")

# Gedächtnis & Client
if "ppi" not in st.session_state:
    st.session_state.ppi = 160.0
if "result" not in st.session_state:
    st.session_state.result = None

if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- 1. KALIBRIERUNG ---
st.header("📏 1. Kalibrierung & Messung")
st.info("Referenzmünze auflegen, Regler anpassen, Kalibrieren drücken.")

size_px = st.slider("Kreisgröße anpassen", 100, 800, 300)

c1, c2 = st.columns(2)
with c1:
    if st.button("📍 Kalibrieren 1 € (23.25 mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 23.25) * 25.4
        st.toast("Kalibriert auf 1 €!")
with c2:
    if st.button("📍 Kalibrieren 2 € (25.75 mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 25.75) * 25.4
        st.toast("Kalibriert auf 2 €!")

mm_ist = (size_px / st.session_state.ppi) * 25.4
st.metric("Messwert", f"{mm_ist:.2f} mm")

# Fixed-Center Messkreis
st.markdown(f"""
    <div style="display: flex; justify-content: center; padding: 40px; background: #0e1117; border-radius: 20px; border: 1px solid #333;">
        <div style="width:{size_px}px; height:{size_px}px; border:6px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center; position: relative;">
            <div style="width: 12px; height: 12px; background: #ff4b4b; border-radius: 50%; position: absolute;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 2. HIERARCHISCHE ANALYSE ---
st.header("🔍 2. Bild-Analyse")
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    st.image(raw_img, caption="Prüfobjekt", width=400)

    if st.button("🚀 Systematische Bestimmung starten", use_container_width=True):
        with st.status("Analysiere Details der Details...") as status:
            
            # --- NEU: Aggressive Bildvorbereitung für OCR ---
            # 1. In Graustufen umwandeln (entfernt Farbrauschen bei Kupfer)
            gray_img = ImageOps.grayscale(raw_img)
            # 2. Extreme Schärfung, um abgenutzte Kanten zu finden
            sharpened = ImageEnhance.Sharpness(gray_img).enhance(3.5)
            # 3. Moderater Kontrast auf das geschärfte Graubild
            final_processed_img = ImageEnhance.Contrast(sharpened).enhance(1.5)
            
            # --- NEU: Der Anti-Halluzinations-Prompt ---
            prompt = f"""
            Analysiere diese Münze streng hierarchisch. Durchmesser: {mm_ist:.1f} mm.
            
            REGEL NR. 1: Wenn du Text nicht klar lesen kannst, schreibe "[unleserlich]". Erfinde NIEMALS Buchstaben!

            STUFE 1: MOTIV & STRUKTUR
            - Was ist das zentrale Element? (z.B. Wappenschild, Zahl, Kopf).
            - Wie ist es aufgebaut? (z.B. "Gekrönter Schild mit einer großen '1' darin").

            STUFE 2: DETAIL DER DETAILS (Tiefenprüfung)
            - Wappen/Schild: Was ist EXAKT im Inneren zu sehen? Zähle Balken, Tiere, Zahlen.
            - Accessoires: Krone (Typ?), Zepter, Reichsapfel, Lorbeerkranz?

            STUFE 3: LEGENDE (Kritische OCR-Prüfung)
            - Lies die Umschrift. Sei extrem konservativ. Lies nur Fragmente, die sicher sind (z.B. "M.THER...").
            - Wenn abgenutzt, gib an, wo Text war, aber nicht mehr lesbar ist.

            STUFE 4: SYNTHESE
            - Bestimme die Münze primär anhand der visuellen Details aus Stufe 1&2 und dem Durchmesser, falls die Legende unleserlich ist.

            Antworte AUSSCHLIESSLICH im JSON-Format:
            {{
              "Bestimmung": "Land, Nominal, Herrscher/Republik",
              "Motiv_Struktur": "Klare Beschreibung des Hauptmotivs",
              "Fein_Details": "Liste der Accessoires und Schildinhalte",
              "Legende_Status": "Gelesene Fragmente oder '[unleserlich]'",
              "Handels_Keywords": "Präzise Suchbegriffe (visuell fokussiert)",
              "Analyse": "Begründung basierend auf Beweisen und Durchmesser"
            }}
            """
            try:
                # Wir senden jetzt das optimierte Graustufenbild
                response = client.models.generate_content(
                    model="gemma-3-27b-it",
                    contents=[prompt, final_processed_img]
                )
                
                txt = response.text
                start, end = txt.find('{'), txt.rfind('}') + 1
                st.session_state.result = json.loads(txt[start:end])
                status.update(label="Analyse abgeschlossen!", state="complete")
            except Exception as e:
                st.error(f"Fehler: {e}")
                st.write(response.text if 'response' in locals() else "Keine API-Antwort.")

# --- 3. ERGEBNIS-ANZEIGE ---
if st.session_state.result:
    res = st.session_state.result
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.success(f"**Bestimmung:** {res['Bestimmung']}")
        st.write(f"**Motiv & Struktur:** {res['Motiv_Struktur']}")
        st.write(f"**Details:** {res['Fein_Details']}")
    with col_b:
        # Anzeige ändert sich je nach Lesbarkeit
        if "[unleserlich]" in res['Legende_Status']:
             st.warning(f"**Legende (Abgenutzt):** `{res['Legende_Status']}`")
        else:
             st.write(f"**Legende (Gelesen):** `{res['Legende_Status']}`")
        st.info(f"**Beweisführung:** {res['Analyse']}")

    # Profi-Links
    st.subheader("🔗 Verifikation")
    search_q = f"{res['Bestimmung']} {res['Handels_Keywords']} {mm_ist:.1f}mm"
    q_enc = urllib.parse.quote(search_q)
    
    l1, l2, l3 = st.columns(3)
    l1.markdown(f"[📚 Numista Check](https://en.numista.com/catalogue/index.php?q={q_enc})")
    l2.markdown(f"[💰 MA-Shops Suche](https://www.ma-shops.de/result.php?searchstr={q_enc})")
    l3.markdown(f"[🖼️ Google Bilder](https://www.google.com/search?q={q_enc}&tbm=isch)")
    
    if st.button("🗑️ Neue Analyse starten"):
        st.session_state.result = None
        st.rerun()
