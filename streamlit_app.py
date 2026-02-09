import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import json
import collections

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro", layout="centered")
st.title("🪙 Münz-Detektiv: Experten-Modus")

# API-Key Check
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Wir nutzen deine funktionierende Basis: gemini-2.5-flash
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.error("🔑 API-Key fehlt in den Secrets!")
    st.stop()

# --- UPLOAD ---
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="Deine Münze", use_container_width=True)

    if st.button("Münze präzise analysieren"):
        results_pool = []
        found_consensus = False
        max_tries = 5 # Maximal 5 Anfragen, um Kosten/Zeit zu sparen

        with st.spinner("Suche nach mehrmaliger Übereinstimmung (Konsens-Prüfung)..."):
            status_area = st.empty()
            
            for i in range(max_tries):
                status_area.text(f"Durchgang {i+1}: Analysiere Details...")
                
                # Strenger Prompt für minimales "Blabla" und JSON-Struktur
                prompt = """
                Verhalte dich wie ein präziser Numismatiker. Antworte NUR im JSON-Format:
                {
                  "Land": "Name",
                  "Einheit": "z.B. Dukat",
                  "Herrscher": "Name",
                  "Jahr": "Exaktes Jahr oder Epoche",
                  "Wert": "Schätzwert in Euro",
                  "Motiv_Details": "Was ist exakt zu sehen?",
                  "Link": "URL zu Numista oder ähnlicher Referenz"
                }
                Kein Smalltalk. Falls Motiv unklar, beschreibe nur sichtbare Elemente.
                """
                
                try:
                    response = model.generate_content([prompt, img])
                    # JSON aus Markdown-Block extrahieren
                    raw_text = response.text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(raw_text)
                    
                    # Fingerabdruck für den Vergleich erstellen
                    fingerprint = f"{data['Land']}-{data['Einheit']}-{data['Jahr']}"
                    results_pool.append((fingerprint, data))
                    
                    # Prüfen, ob wir dieses Ergebnis schon einmal hatten
                    counts = collections.Counter([r[0] for r in results_pool])
                    for fp, count in counts.items():
                        if count >= 2:
                            # Konsens gefunden!
                            final_data = next(item[1] for item in results_pool if item[0] == fp)
                            found_consensus = True
                            break
                    
                    if found_consensus:
                        break
                except:
                    continue

        if found_consensus:
            st.success("✅ Übereinstimmendes Ergebnis gefunden!")
            
            # Die 4 Kernpunkte klar darlegen
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Land", final_data['Land'])
            c2.metric("Einheit", final_data['Einheit'])
            c3.metric("Herrscher", final_data['Herrscher'])
            c4.metric("Jahr", final_data['Jahr'])
            
            st.write(f"**Geschätzter Wert:** {final_data['Wert']}")
            st.markdown(f"[🔗 Referenz im Internet prüfen]({final_data['Link']})")
            
            # Details nur bei Bestätigung/Wunsch
            with st.expander("🔍 Details zum Motiv & Analyse"):
                st.write(final_data['Motiv_Details'])
                st.info("Dieses Ergebnis wurde durch mindestens zwei identische KI-Analysen bestätigt.")
        else:
            st.error("❌ Kein Konsens möglich. Die KI liefert zu unterschiedliche Ergebnisse. Bitte Foto verbessern.")

    # --- MESSEN (Dein funktionierender Code) ---
    st.divider()
    st.subheader("📏 Durchmesser")
    ppi = st.slider("Display-Kalibrierung (Handy-PPI)", 100, 600, 160)
    size = st.slider("Kreisgröße", 50, 600, 250)
    mm = (size / ppi) * 25.4
    st.metric("Berechneter Durchmesser", f"{mm:.1f} mm")
    st.markdown(f'<div style="width:{size}px; height:{size}px; border:4px solid gold; border-radius:50%; margin:auto;"></div>', unsafe_allow_html=True)
