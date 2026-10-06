import json
import mimetypes
from typing import List, Dict, Tuple

from google import genai
from google.genai import types

MODEL_NAME = "gemini-2.0-flash"

# Esquema LIMPIO sin additional_properties / additionalProperties
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
    # Detecta mime simple
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
        transcript_block = "(No se proporcionaron transcripciones de video)"

    return f"""
Eres un analista experto de Supremacy 1914. No controlas el juego.
Analiza la captura del mapa y el contexto.

Contexto del jugador: {game_context or "No proporcionado"}

Transcripciones / notas:
{transcript_block}

Devuelve SOLO un JSON válido con esta estructura exacta:
- lectura_del_mapa: string con análisis de la situación visible
- plan_de_accion: array de strings (3-6 pasos)
- tacticas_de_los_videos: array de strings extraídas de las transcripciones
- riesgos_y_supuestos: array de strings
- confianza: string como "Alta", "Media", "Baja" con breve justificación

No añadas markdown, no añadas explicaciones fuera del JSON.
"""


def analyze_position(image_bytes: bytes, image_mime: str, transcripts: List[Dict], game_context: str, api_key: str) -> Dict:
    client = genai.Client(api_key=api_key)

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=image_mime)

    # FIX: Ya no usamos response_schema con additional_properties que rompe la API.
    # Usamos solo response_mime_type = application/json y parseamos manual.
    # Si quieres schema, usa types.Schema sin additionalProperties.
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.25,
        max_output_tokens=8192,
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[_build_prompt(transcripts, game_context), image_part],
        config=config,
    )

    text = response.text.strip()
    # Limpia posibles ```json envoltorios
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: intenta extraer JSON
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])

    # Validación mínima
    for key in _REPORT_SCHEMA["required"]:
        if key not in data:
            data[key] = [] if "array" in str(_REPORT_SCHEMA["properties"].get(key, {}).get("type")) else ""

    return data
