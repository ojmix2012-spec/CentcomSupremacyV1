import json, time
from typing import List, Dict, Tuple
from google import genai
from google.genai import types, errors

# CATÁLOGO VÁLIDO OCT 2026 - solo 3.x para llaves nuevas
MODEL_CANDIDATES = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]

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
    return f"Eres analista experto de Supremacy 1914. Contexto: {game_context or 'No proporcionado'} Transcripciones: {transcript_block} Devuelve SOLO JSON con lectura_del_mapa, plan_de_accion, tacticas_de_los_videos, riesgos_y_supuestos, confianza"

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
    prompt = _build_prompt(transcripts, game_context)
    last_error = None
    for model_name in MODEL_CANDIDATES:
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=model_name, contents=[prompt, image_part], config=config)
                text = response.text.strip()
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                data = json.loads(text[text.find("{"):text.rfind("}")+1])
                return data
            except errors.ClientError as e:
                msg = str(e)
                if "404" in msg or "NOT_FOUND" in msg:
                    last_error = e
                    break
                if "503" in msg or "UNAVAILABLE" in msg or "429" in msg or "high demand" in msg:
                    last_error = e
                    time.sleep(2 ** attempt)
                    continue
                last_error = e
                time.sleep(1)
            except Exception as e:
                last_error = e
                time.sleep(1)
                continue
    raise RuntimeError(f"Fallo tras probar {MODEL_CANDIDATES}. Último: {last_error}")
