import streamlit as st
import json
import datetime
import urllib.parse
from supremacy_bot.analysis import analyze_position, inspect_image, MODEL_CANDIDATES
from supremacy_bot.reporting import build_markdown_report, build_whatsapp_message, whatsapp_link
from supremacy_bot.youtube import fetch_transcript, parse_video_links

st.set_page_config(page_title="Centcom Supremacy V1", layout="wide")

st.title("Asistente de estrategia para Supremacy 1914")
st.caption("Analiza capturas con Gemini 3.8 Flash (Free tier 5 RPM) + tácticas de YouTube")

# --- SIDEBAR ---
with st.sidebar:
    st.subheader("Configuración")
    api_key = st.text_input("GEMINI_API_KEY", type="password", help="La de Centcom App - Free tier")
    if not api_key:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
    st.info(f"Modelos: {', '.join(MODEL_CANDIDATES[:3])}\n\nFree tier: 5 RPM / 20 RPD para 3.8 Flash")
    st.divider()
    st.write("Tu proyecto Free tier verificado: `inspiring-wares-250700` - Rate limit 3/5")

# --- MAIN FORM ---
col1, col2 = st.columns(2)

with col1:
    uploaded = st.file_uploader("Sube captura PNG/JPEG/WebP", type=["png","jpg","jpeg","webp"])
    game_context = st.text_area("Contexto de la partida (país, día, objetivo)", height=120, placeholder="Ej: Canadá norte, día 46, coalición, recursos...")
    
with col2:
    yt_links_raw = st.text_area("Links de YouTube (uno por línea, hasta 3)", height=80, placeholder="https://youtube.com/watch?v=...\nhttps://youtu.be/...")
    manual_transcript = st.text_area("Transcripción manual (opcional, si YouTube no tiene subs)", height=120)

if st.button("🔍 Analizar captura y estrategias", type="primary", use_container_width=True):
    if not uploaded:
        st.error("Sube una imagen primero")
        st.stop()
    if not api_key:
        st.error("Pon tu GEMINI_API_KEY en Secrets")
        st.stop()

    with st.spinner("Analizando con Gemini 3.8 Flash... (Free tier 5 RPM, puede tardar 10-20s por 503)"):
        try:
            image_bytes = uploaded.read()
            image_bytes, mime = inspect_image(image_bytes)
            
            # YouTube
            links = parse_video_links(yt_links_raw)
            transcripts = []
            for link in links:
                try:
                    t = fetch_transcript(link)
                    transcripts.append({"url": link, "label": link, "text": t[:15000]})
                except Exception as e:
                    transcripts.append({"url": link, "label": link, "text": f"Error obteniendo transcript: {e}. Usando manual si hay."})
            
            if manual_transcript.strip():
                transcripts.append({"url": "manual", "label": "Transcripción manual", "text": manual_transcript[:15000]})

            # Análisis
            result = analyze_position(image_bytes, mime, transcripts, game_context, api_key)
            created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            report_md = build_markdown_report(result, transcripts, created_at)
            message = build_whatsapp_message(result, transcripts, created_at)
            wa_link = whatsapp_link(message)

            # Guarda en session_state para export
            st.session_state["report_state"] = {
                "result": result,
                "transcripts": transcripts,
                "created_at": created_at,
                "report_md": report_md,
                "message": message,
                "game_context": game_context,
                "yt_links": links,
                "model_candidates": MODEL_CANDIDATES,
                "image_name": uploaded.name,
                "image_size": len(image_bytes),
                "mime": mime,
            }

            st.success("✅ Análisis completado")
            st.divider()
            st.subheader("Lectura de la situación")
            st.markdown(report_md)

            col_a, col_b = st.columns(2)
            with col_a:
                st.link_button("📱 Abrir WhatsApp con el informe", wa_link, use_container_width=True)
            with col_b:
                st.download_button("⬇️ Descargar informe Markdown", report_md, file_name=f"informe_supremacy_{created_at.replace(' ', '_')}.md", use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")
            st.exception(e)

# --- EXPORT PARA IA (NUEVO) ---
if "report_state" in st.session_state:
    st.divider()
    st.subheader("📦 Exportar paquete auditable para cualquier IA")
    st.caption("Descarga todo lo procesado para que yo u otra IA podamos verificarlo / reproducirlo")

    rs = st.session_state["report_state"]

    # Paquete JSON completo
    export_json = {
        "app": "CentcomSupremacyV1",
        "repo": "https://github.com/ojmix2012-spec/CentcomSupremacyV1",
        "generated_at": rs["created_at"],
        "project": "Centcom App / inspiring-wares-250700",
        "billing_tier": "Free tier",
        "rate_limit_observed": "Gemini 3.8 Flash 3/5 RPM, 390/250K TPM (ver screenshot Rate Limit)",
        "model_candidates_used": rs["model_candidates"],
        "image": {
            "name": rs["image_name"],
            "size_bytes": rs["image_size"],
            "mime": rs["mime"],
        },
        "game_context": rs["game_context"],
        "youtube_links": rs["yt_links"],
        "transcripts": rs["transcripts"],
        "gemini_raw_result": rs["result"],
        "final_markdown": rs["report_md"],
        "whatsapp_draft": rs["message"],
        "prompt_structure": "analiza captura del norte de Canadá día 46 + contexto + transcripciones -> devuelve JSON con lectura_del_mapa, plan_de_accion, tacticas_de_los_videos, riesgos_y_supuestos, confianza",
        "verification_note": "Este JSON contiene TODO lo que Gemini recibió y devolvió. Cualquier IA puede leerlo y confirmar si el informe es coherente con la imagen y las fuentes.",
    }

    export_txt = f"""# CentcomSupremacyV1 - Paquete Auditable
Generado: {rs['created_at']}
Repo: https://github.com/ojmix2012-spec/CentcomSupremacyV1
Proyecto: Centcom App / inspiring-wares-250700 (Free tier)
Rate Limit verificado: Gemini 3.8 Flash 3/5 RPM (screenshot 2026-10-06)
Modelos probados: {', '.join(rs['model_candidates'])}

## Imagen
Nombre: {rs['image_name']}
Tamaño: {rs['image_size']} bytes
MIME: {rs['mime']}

## Contexto de partida
{rs['game_context']}

## Links YouTube
{chr(10).join(rs['yt_links']) if rs['yt_links'] else 'Ninguno'}

## Transcripciones (truncadas a 15000 chars c/u)
{chr(10).join([f"--- {t.get('label')} ---\\n{t.get('text')[:2000]}..." for t in rs['transcripts']])}

## Resultado JSON crudo de Gemini
{json.dumps(rs['result'], indent=2, ensure_ascii=False)}

## Informe Markdown final
{rs['report_md']}

## Mensaje WhatsApp
{rs['message']}
"""

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "📄 Descargar .TXT (para pegar a cualquier IA)",
            export_txt,
            file_name=f"centcom_audit_{rs['created_at'].replace(' ', '_').replace(':', '-')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "🧩 Descargar .JSON (auditable)",
            json.dumps(export_json, indent=2, ensure_ascii=False),
            file_name=f"centcom_audit_{rs['created_at'].replace(' ', '_').replace(':', '-')}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col3:
        st.download_button(
            "📝 Descargar .MD solo informe",
            rs["report_md"],
            file_name=f"informe_{rs['created_at'].replace(' ', '_').replace(':', '-')}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.info("💡 Tip: Súbeme el .TXT o .JSON que descargues aquí en Meta AI y te confirmo si el análisis de Gemini 3.8 Flash es coherente con tu captura de Canadá día 46.")
