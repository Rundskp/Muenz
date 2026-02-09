import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageEnhance
import io
import json
import collections

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro - Ultra", layout="centered")
st.title("🪙 Münz-Detektiv: Experten-Modus 2.0")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- BILD-VERARBEITUNG ---
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    
    # Automatische Bildverbesserung für die KI (Kontrast & Schärfe)
    enhancer = ImageEnhance.Contrast(img)
    enhanced_img = enhancer.enhance(1.5) 
    
    st.image(img, caption="Originalbild", use_container_width=True)

    if st.button("Präzise Konsens-Analyse (5-fach Check)"):
        results_pool = []
        max_tries = 5
        
        with st.spinner("KI-Abgleich läuft... Ich suche nach Übereinstimmungen."):
            status_area = st.empty()
            
            for i in range(max_tries):
                status_area.text(f"Versuch {i+1} von {max_attempts}...")
                
                # Prompt mit Fokus auf Identifikation statt "Blabla"
                prompt = """
                Numismatische Analyse. Antworte NUR im JSON-Format:
                {
                  "Land": "Name",
                  "Einheit": "z.B. Dukat",
                  "Herrscher": "Name",
                  "Jahr": "Jahr oder Zeitraum",
                  "Wert": "Schätzwert Euro",
                  "Details": "Kompakte Motivbeschreibung",
                  "Link": "Google-Suche Link für dieses Stück"
                }
                WICHTIG: Wenn das Jahr nicht exakt lesbar ist, gib das Jahrhundert an.
                """
                
                try:
                    # Wir senden das optimierte Bild an die KI
                    response = model.generate_content([prompt, enhanced_img])
                    raw_text = response.text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(raw_text)
                    
                    # Fingerabdruck: Wir gewichten Land + Herrscher stärker als das Jahr
                    fingerprint = f"{data['Land']}-{data['Herrscher']}".lower()
                    results_pool.append(data)
                except:
                    continue

            # Konsens-Logik: Welcher Herrscher/Land-Kombination kam am häufigsten vor?
            fps = [f"{r['Land']}-{r['Herrscher']}".lower() for r in results_pool]
            if fps:
                most_common_fp = collections.Counter(fps).most_common(1)[0]
                
                # Wir zeigen das Ergebnis an, wenn mindestens 2x derselbe Herrscher gefunden wurde
                if most_common_fp[1] >= 2:
                    # Nimm das erste Resultat, das zum häufigsten Fingerabdruck passt
                    final_data = next(r for r in results_pool if f"{r['Land']}-{r['Herrscher']}".lower() == most_common_fp[0])
                    
                    st.success(f"✅ Konsens gefunden ({most_common_fp[1]} von 5 Analysen stimmen überein)")
                    
                    # Saubere Kacheln für die Fakten
                    st.divider()
                    c1, c2 = st.columns(2)
                    c1.metric("Land", final_data['Land'])
                    c2.metric("Herrscher", final_data['Herrscher'])
                    
                    c3, c4 = st.columns(2)
                    c3.metric("Einheit", final_data['Einheit'])
                    c4.metric("Jahr/Epoche", final_data['Jahr'])
                    
                    st.info(f"💰 **Schätzwert:** {final_data['Wert']}")
                    st.markdown(f"🔗 [Direkt-Suche nach Vergleichsstücken](https://www.google.com/search?q=Münze+{final_data['Land']}+{final_data['Herrscher']}+{final_data['Einheit']})")
                    
                    with st.expander("🔍 Details zum Motiv einblenden"):
                        st.write(final_data['Details'])
                else:
                    st.warning("⚠️ Kein klarer Konsens. Hier ist die wahrscheinlichste Vermutung:")
                    st.json(results_pool[0])
            else:
                st.error("Keine Daten von der KI erhalten. API-Limit erreicht?")

    # --- DURCHMESSER (Deine Basis) ---
    st.divider()
    st.subheader("📏 Durchmesser")
    ppi = st.slider("Kalibrierung (Handy-PPI)", 100, 600, 160)
    size = st.slider("Kreisgröße", 50, 600, 125)
    mm = (size / ppi) * 25.4
    st.metric("Berechneter Durchmesser", f"{mm:.1f} mm")
    st.markdown(f'<div style="width:{size}px; height:{size}px; border:4px solid gold; border-radius:50%; margin:auto;"></div>', unsafe_allow_html=True)
