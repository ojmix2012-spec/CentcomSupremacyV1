import os
from datetime import datetime, timezone

import streamlit as st

from supremacy_bot.analysis import analyze_position, inspect_image
from supremacy_bot.reporting import build_markdown_report, build_whatsapp_message, whatsapp_link
from supremacy_bot.youtube import fetch_transcript, parse_video_links


st.set_page_config(
    page_title="Supremacy 1914 · Asistente de estrategia",
    page_icon="S",
    layout="wide",
)

st.title("Supremacy 1914 · Asistente de estrategia")
st.caption(
    "Analiza una captura, contrasta tácticas de videos y prepara un informe para WhatsApp. "
    "No controla el juego ni ejecuta movimientos."
)

with st.form("strategy_analysis", clear_on_submit=False):
    screenshot = st.file_uploader(
        "Captura del mapa",
        type=["png", "jpg", "jpeg", "webp"],
        help="Sube una captura nítida del mapa. El archivo se procesa en memoria y no se guarda en el proyecto.",
    )
    video_urls_text = st.text_area(
        "Videos de YouTube (hasta 3 enlaces, uno por línea)",
        placeholder="https://www.youtube.com/watch?v=...",
        height=100,
    )
    manual_transcript = st.text_area(
        "Transcripción o notas (opcional)",
        placeholder="Úsalo si un video no tiene subtítulos disponibles o para añadir contexto.",
        height=120,
    )
    game_context = st.text_area(
        "Contexto del mapa (opcional)",
        placeholder="País que juegas, día de partida, objetivo o situación que no se ve en la captura.",
        height=80,
    )
    transcript_language = st.selectbox(
        "Idioma preferido de subtítulos",
        options=[("Español", "es"), ("Inglés", "en")],
        format_func=lambda option: option[0],
    )[1]
    submitted = st.form_submit_button(
        "Analizar captura y estrategias",
        type="primary",
        use_container_width=True,
    )

if submitted:
  api_key = st.secrets.get("GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    import streamlit as st
import google.generativeai as genai
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Falta GEMINI_API_KEY. Ve a Settings > Secrets en Streamlit y agrégala")
    st.stop()
    
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")
    elif screenshot is None:
        st.error("Sube una captura del mapa para iniciar el análisis.")
    else:
        try:
            image_bytes, image_mime = inspect_image(screenshot.getvalue())
            video_urls = parse_video_links(video_urls_text)
            transcripts = []
            transcript_errors = []

            with st.status("Preparando la captura y las fuentes…", expanded=True) as progress:
                for url in video_urls:
                    progress.write(f"Buscando subtítulos: {url}")
                    try:
                        transcripts.append(fetch_transcript(url, [transcript_language, "en", "es"]))
                    except Exception:
                        transcript_errors.append(url)

                if manual_transcript.strip():
                    transcripts.append(
                        {
                            "url": "",
                            "language": "aportada por el usuario",
                            "is_generated": False,
                            "text": manual_transcript.strip()[:20000],
                            "label": "Transcripción o notas manuales",
                        }
                    )

                progress.update(label="Analizando con Gemini…", state="running")
                result = analyze_position(
                    image_bytes=image_bytes,
                    image_mime=image_mime,
                    transcripts=transcripts,
                    game_context=game_context.strip(),
                    api_key=api_key,
                )
                progress.update(label="Informe listo", state="complete")

            st.session_state["supremacy_report"] = {
                "result": result,
                "transcripts": transcripts,
                "transcript_errors": transcript_errors,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            }
        except ValueError as exc:
            st.error(str(exc))
       except Exception as exc:
    st.error(f"No se pudo completar el análisis: {exc}")
    st.exception(exc)

report_state = st.session_state.get("supremacy_report")
if report_state:
    result = report_state["result"]
    report_markdown = build_markdown_report(
        result,
        report_state["transcripts"],
        report_state["created_at"],
    )
    message = build_whatsapp_message(result, report_state["transcripts"])

    st.divider()
    st.subheader("Lectura de la situación")
    st.write(result["lectura_del_mapa"])

    left, right = st.columns(2)
    with left:
        st.markdown("#### Plan recomendado")
        if result["plan_de_accion"]:
            for item in result["plan_de_accion"]:
                st.markdown(f"- {item}")
        else:
            st.write("No se generaron pasos concretos.")
    with right:
        st.markdown("#### Tácticas de los videos")
        if result["tacticas_de_los_videos"]:
            for item in result["tacticas_de_los_videos"]:
                st.markdown(f"- {item}")
        else:
            st.write("No se proporcionó una transcripción de video.")

    st.markdown("#### Riesgos y supuestos")
    for item in result["riesgos_y_supuestos"]:
        st.markdown(f"- {item}")
    st.caption(f"Confianza estimada: {result['confianza']}")

    if report_state["transcript_errors"]:
        st.warning(
            "No se pudieron obtener subtítulos de estos videos: "
            + ", ".join(report_state["transcript_errors"])
            + ". Si tienen transcripción, pégala en el campo de notas y vuelve a analizar."
        )

    st.markdown("#### Informe para WhatsApp")
    st.text_area("Mensaje listo para revisar y compartir", value=message, height=150)
    share, download = st.columns(2)
    with share:
        st.link_button(
            "Abrir WhatsApp con el informe",
            whatsapp_link(message),
            use_container_width=True,
        )
    with download:
        st.download_button(
            "Descargar informe completo",
            data=report_markdown,
            file_name="informe_supremacy_1914.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with st.expander("Ver informe completo y fuentes"):
        st.markdown(report_markdown)
    st.caption(
        "El informe no se envía automáticamente: WhatsApp abre un borrador para que elijas el chat y confirmes el envío."
    )

st.divider()
st.caption(
    "Los subtítulos públicos pueden no estar disponibles para todos los videos. "
    "El análisis se basa solo en lo que se ve en la captura y en el texto proporcionado. "
    "Las llamadas a Gemini se facturan a la cuenta vinculada a tu clave."
)



