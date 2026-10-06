import json
import time
from typing import List, Dict, Tuple
from google import genai
from google.genai import types, errors

# OPTIMIZADO SEGÚN TUS SCREENSHOTS 2026-10-06 15:46
# Proyecto: inspiring-wares-250700 (Centcom v1)
# Screenshot 154648: 3.5 Flash 3/5 RPM, 3.8 Flash 3/5 RPM
# Screenshot 154633: 3.1 Flash Lite 0/15 RPM, 3.5 Flash Lite 0/15 RPM, 3.6 Flash 0/5, 3.7 Flash 0/5
# -> Los Lite tienen 3x más cuota (15 RPM vs 5 RPM) y 500 RPD vs 20 RPD
MODEL_CANDIDATES = [
    "gemini-3.8-flash",       # Principal - 5 RPM / 20 RPD / 250K TPM - más potente
    "gemini-3.5-flash",       # Secundario - 5 RPM / 20 RPD
    "gemini-3.5-flash-lite",  # Salvavidas 1 - 15 RPM / 500 RPD - 3x cuota
    "gemini-3.1-flash-lite",  # Salvavidas 2 - 15 RPM / 500 RPD - 3x cuota
    "gemini-3.6-flash",       # Fallback - 5 RPM
    "gemini-3.7-flash",       # Fallback - 5 RPM
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
    elif image_bytes[:1] == b"G":
        mime = "image/gif"
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
Eres analista experto de Supremacy 1914. Analiza la captura del mapa del norte de Canadá, Día 46.

Contexto del jugador: {game_context or "No proporcionado"}

Transcripciones de videos de estrategia:
{transcript_block}

Devuelve SOLO JSON válido con esta estructura exacta:
{{
  "lectura_del_mapa": "descripcion detallada de lo que ves",
  "plan_de_accion": ["paso 1", "paso 2", "paso 3"],
  "tacticas_de_los_videos": ["táctica 1", "táctica 2"],
  "riesgos_y_supuestos": ["riesgo 1", "riesgo 2"],
  "confianza": "Alta/Media/Baja + justificación"
}}
"""

def analyze_position(image_bytes: bytes, image_mime: str, transcripts: List[Dict], game_context: str, api_key: str) -> Dict:
    client = genai.Client(api_key=api_key)
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=image_mime)
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.3,
        max_output_tokens=8192,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(mode="NONE")),
    )
    prompt = _build_prompt(transcripts, game_context)
    last_error = None

    for model_name in MODEL_CANDIDATES:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, image_part],
                    config=config,
                )
                text = response.text.strip()
                if "```" in text:
                    try:
                        text = text.split("```")[1]
                        if text.strip().startswith("json"):
                            text = text.strip()[4:]
                    except:
                        pass
                start = text.find("{")
                end = text.rfind("}") + 1
                if start == -1 or end == 0:
                    raise ValueError(f"No JSON encontrado: {text[:500]}")
                data = json.loads(text[start:end])
                # Agrega metadata del modelo usado para el paquete auditable
                data["_modelo_usado"] = model_name
                data["_rate_limit_snapshot"] = "Free tier - 3/5 RPM para Flash, 0/15 RPM para Lite (screenshots 2026-10-06)"
                return data
            except errors.ClientError as e:
                msg = str(e)
                last_error = e
                if "404" in msg or "NOT_FOUND" in msg:
                    break
                if any(x in msg for x in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "high demand"]):
                    time.sleep(2 ** attempt + 1)
                    continue
                time.sleep(1)
            except Exception as e:
                last_error = e
                time.sleep(1)
                continue

    raise RuntimeError(f"No se pudo completar tras probar {MODEL_CANDIDATES}. Último error: {last_error}. Tu proyecto {MODEL_CANDIDATES[0]} está en 3/5 RPM según screenshot 154648 - espera 1 min y reintenta, o caerá a Lite 15 RPM.")
