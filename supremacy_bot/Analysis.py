import json
from typing import List, Dict, Tuple
from google import genai
from google.genai import types

# VERIFICADO 2026-10-06: 2.5 ya no va para llaves nuevas
# Usa 3.8-flash que es el GA actual desde 2026-09-02
MODEL_NAME = "gemini-3.8-flash"

_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "lectura_del_mapa": {"type": "string"},
        "plan_de_accion": {"type": "array", "items": {"type": "string"}},
        "tacticas_de_los_videos": {"type": "array", "items": {"type": "string"}},
        "riesgos_y_supuestos": {"type": "array", "items": {"type": "string"}},
        "confianza": {"type": "string"},
    },
    "required": ["lectura_del_mapa", "plan_de_accion", "tacticas_de_los_videos", "riesgos_y_supuestos", "confianza"],
}

def inspect_image(image_bytes: bytes) -> Tuple[bytes, str]:
    if not image_bytes:
        raise ValueError("La imagen está vacía")
    mime = "image/png"
    if image_bytes[:2] == b"\xff\xd8":
        mime = "image/jpeg"
    elif image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif image_bytes[:4] == b"RIFF":
        mime = "image/webp"
    return image_bytes, mime

def _build_prompt(transcripts: List[Dict], game_context: str) -> str:
    transcript_block = ""
    for t in transcripts:
        label = t.get("label") or t.get("url") or "fuente"
        text = t.get("text", "")[:15000]
        transcript_block += f"\n--- Fuente: {label} ---\n{text}\n"
    if not transcript_block:
        transcript_block = "(No se proporcionaron transcripciones)"
    return f"""
Eres analista experto de Supremacy 1914. Analiza la captura.
Contexto: {game_context or "No proporcionado"}
Transcripciones:
{transcript_block}
Devuelve SOLO JSON con: lectura_del_mapa, plan_de_accion, tacticas_de_los_videos, riesgos_y_supuestos, confianza
"""

def analyze_position(image_bytes: bytes, image_mime: str, transcripts: List[Dict], game_context: str, api_key: str) -> Dict:
    client = genai.Client(api_key=api_key)
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=image_mime)
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.25,
        max_output_tokens=8192,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(mode="NONE")),
    )
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[_build_prompt(transcripts, game_context), image_part],
        config=config,
    )
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        data = json.loads(text)
    except:
        data = json.loads(text[text.find("{"):text.rfind("}")+1])
    return data
