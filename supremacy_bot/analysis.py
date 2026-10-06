import json
import time
from typing import List, Dict, Tuple
from google import genai
from google.genai import types, errors

# MODELOS VALIDOS PARA LLAVES NUEVAS OCT 2026 (Free Tier = 3.x solamente)
# Tu screenshot de Rate Limit confirma 5 RPM para estos
MODEL_CANDIDATES = [
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
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
        for attempt in range(3):  # 3 reintentos por modelo para 503/429
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, image_part],
                    config=config,
                )
                text = response.text.strip()
                # Limpia markdown si viene con ```json
                if "```" in text:
                    try:
                        text = text.split("```")[1]
                        if text.strip().startswith("json"):
                            text = text.strip()[4:]
                    except:
                        pass
                # Extrae JSON
                start = text.find("{")
                end = text.rfind("}") + 1
                if start == -1 or end == 0:
                    raise ValueError(f"No JSON encontrado en respuesta: {text[:500]}")
                data = json.loads(text[start:end])
                return data
            except errors.ClientError as e:
                msg = str(e)
                last_error = e
                if "404" in msg or "NOT_FOUND" in msg:
                    # Modelo no existe para esta key, prueba siguiente
                    break
                if any(x in msg for x in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "high demand"]):
                    time.sleep(2 ** attempt + 1)  # 2s, 3s, 5s
                    continue
                time.sleep(1)
            except Exception as e:
                last_error = e
                time.sleep(1)
                continue

    raise RuntimeError(f"No se pudo completar tras probar {MODEL_CANDIDATES}. Último error: {last_error}. Revisa que tu key sea de AI Studio Free tier y que no hayas excedido 20 RPD en 3.8-flash.")
