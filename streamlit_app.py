import streamlit as st
from google import genai
from PIL import Image, ImageStat, ImageOps
import json
import urllib.parse

# --- SETUP ---
st.set_page_config(page_title="MuenzID - Bulletproof", layout="wide")
st.title("🪙 Münz-Detektiv: Bulletproof Edition")

if "result" not in st.session_state:
    st.session_state.result = None
if "raw_text" not in st.session_state:
    st.session_state.raw_text = None

# API Setup
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- 1. VERBESSERTE MATERIAL-MATHEMATIK ---
def analyze_material_center(img):
    # Wir schneiden 30% vom Rand weg, um den blauen Hintergrund zu ignorieren
    width, height = img.size
    left = width * 0.3
    top = height * 0.3
    right = width * 0.7
    bottom = height * 0.7
    
    center_crop = img.crop((left, top, right, bottom))
    hsv = center_crop.convert("HSV")
    stat = ImageStat.Stat(hsv)
    
    avg_sat = stat.mean[1] # Sättigung
    avg_hue = stat.mean[0] # Farbton
    
    # Debug-Werte (damit wir sehen, was passiert)
    debug_info = f"(H:{avg_hue:.1f}, S:{avg_sat:.1f})"
    
    if avg_sat < 45: 
        return "Silber / Zink (Grau)", "Silver", debug_info
    if 20 < avg_hue < 50:
        return "Gold / Messing", "Gold", debug_info
    if avg_hue < 15 or avg_hue > 230:
        return "Kupfer / Bronze", "Copper", debug_info
        
    return "Unbestimmtes Metall", "", debug_info

# --- UI ---
st.header("Analyse")
uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    
    # Material-Check mit Center-Crop
    mat_name, mat_eng, debug = analyze_material_center(raw_img)
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.image(raw_img, caption="Original", width=200)
    with c2:
        if mat_eng == "Silver":
            st.success(f"🧬 **Material:** {mat_name} {debug}")
        elif mat_eng == "Gold":
            st.warning(f"🧬 **Material:** {mat_name} {debug}")
        else:
            st.info(f"🧬 **Material:** {mat_name} {debug}")
            
    if st.button("🚀 Scannen (Erzwinge Ausgabe)", use_container_width=True):
        with st.status("Lese Text & bestimme...") as status:
            prompt = f"""
            Du bist ein OCR-Scanner. Ignoriere das Metall, das ist bekannt ({mat_name}).
            
            AUFGABE:
            1. Lies ALLE Buchstaben auf der Münze (Umschrift/Legende). Sei präzise!
            2. Beschreibe das Motiv in 3 Worten (z.B. "Adler im Wappen").
            3. Erstelle einen Suchstring für Numista.

            Antworte als JSON:
            {{
                "Gelesener_Text": "Der Text auf der Münze",
                "Motiv": "Kurzbeschreibung",
                "Such_String": "Text + Motiv (z.B. 'ARCHID AVST Wappen')"
            }}
            """
            try:
                response = client.models.generate_content(
                    model="gemma-3-27b-it", 
                    contents=[prompt, raw_img]
                )
                
                txt = response.text
                # Speichere Roh-Text falls JSON fehlschlägt
                st.session_state.raw_text = txt
                
                # JSON Versuch
                clean_txt = txt.replace("```json", "").replace("```", "")
                start = clean_txt.find('{')
                end = clean_txt.rfind('}') + 1
                
                if start != -1 and end != -1:
                    st.session_state.result = json.loads(clean_txt[start:end])
                else:
                    # Fallback: Wir basteln ein "Notfall-Ergebnis" aus dem Text
                    st.session_state.result = {
                        "Gelesener_Text": "Siehe Rohdaten",
                        "Motiv": "Unbekannt",
                        "Such_String": "Coin unidentified" 
                    }
                
                status.update(label="Fertig!", state="complete")
                
            except Exception as e:
                st.error(f"Fehler: {e}")

# --- ANZEIGE (Immer sichtbar) ---
if st.session_state.result:
    res = st.session_state.result
    st.divider()
    
    st.subheader("🔍 Ergebnisse")
    st.write(f"**Text:** `{res.get('Gelesener_Text')}`")
    st.write(f"**Motiv:** {res.get('Motiv')}")
    
    # Fallback Anzeige, falls JSON kaputt war
    if st.session_state.raw_text and "Siehe Rohdaten" in res.get('Gelesener_Text'):
        with st.expander("⚠️ KI-Rohdaten anzeigen (Parsing fehlgeschlagen)"):
            st.write(st.session_state.raw_text)

    # DER LINK
    keyword = res.get('Such_String', 'Coin')
    # Wir fügen das mathematisch bestimmte Material hinzu!
    final_query = f'site:en.numista.com "{keyword}" {mat_eng}'
    link = f"https://www.google.com/search?q={urllib.parse.quote(final_query)}"
    
    st.success("👇 Hier klicken für Datenbank-Abgleich:")
    st.markdown(f"### 👉 [**Ergebnisse auf Numista anzeigen**]({link})")
    
    st.caption(f"Such-Logik: `{final_query}`")
    
    if st.button("Neu"):
        st.session_state.result = None
        st.session_state.raw_text = None
        st.rerun()
