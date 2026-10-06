import json
from io import BytesIO
from typing import Any

from google import genai
from google.genai import types
from PIL import Image, UnidentifiedImageError

MODEL_NAME = "gemini-2.0-flash"
MAX_IMAGE_BYTES = 18 * 1024 * 1024

_REPORT_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "lectura_del_mapa": types.Schema(type=types.Type.STRING),
        "plan_de_accion": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "tacticas_de_los_videos": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "riesgos_y_supuestos": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "confianza": types.Schema(type=types.Type.STRING),
        "resumen_whatsapp": types.Schema(type=types.Type.STRING),
    },
    required=["lectura_del_mapa","plan_de_accion","tacticas_de_los_videos","riesgos_y_supuestos","confianza","resumen_whatsapp"],
    additional_properties=False,
)

def inspect_image(image_bytes: bytes) -> tuple[bytes, str]:
    if not image_bytes: raise ValueError("El archivo de imagen está vacío.")
    if len(image_bytes) > MAX_IMAGE_BYTES: raise ValueError("La captura supera el límite de 18 MB.")
    try:
        with Image.open(BytesIO(image_bytes)) as image: image.verify()
        with Image.open(BytesIO(image_bytes)) as image: image_format = (image.format or "").upper()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("El archivo no parece ser una imagen PNG, JPEG o WebP válida.") from exc
    mime_types = {"PNG": "image/png","JPEG": "image/jpeg","WEBP": "image/webp"}
    mime_type = mime_types.get(image_format)
    if not mime_type: raise ValueError("Usa una imagen PNG, JPEG o WebP.")
    return image_bytes, mime_type

def _format_transcripts(transcripts):
    if not transcripts: return "No se proporcionaron videos ni transcripciones."
    sections = []
    for i, t in enumerate(transcripts, start=1):
        sections.append(f"[{i}] {t.get('label') or f'Video {i}'}\nURL: {t.get('url','')}\nIdioma: {t.get('language','')}\nTexto:\n{t.get('text','')[:20000]}")
    return "\n\n".join(sections)

def _build_prompt(transcripts, game_context):
    context = game_context or "El usuario no añadió contexto adicional."
    video_material = _format_transcripts(transcripts)
    return f"""Eres un asesor de estrategia para Supremacy 1914. Analiza la captura adjunta. Responde en español.
Contexto: {context[:4000]}
Transcripciones: {video_material}
Devuelve JSON con: lectura_del_mapa, plan_de_accion, tacticas_de_los_videos, riesgos_y_supuestos, confianza, resumen_whatsapp""".strip()

def analyze_position(image_bytes, image_mime, transcripts, game_context, api_key):
    if not api_key.strip(): raise ValueError("Falta GEMINI_API_KEY.")
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=image_mime)
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[_build_prompt(transcripts, game_context), image_part],
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=_REPORT_SCHEMA, temperature=0.25, max_output_tokens=8192),
    )
    text = response.text
    if not text: raise ValueError("Gemini devolvió una respuesta vacía.")
    parsed = json.loads(text)
    if not isinstance(parsed, dict): raise ValueError("Gemini devolvió un informe con formato no válido.")
    return {
        "lectura_del_mapa": parsed.get("lectura_del_mapa","").strip(),
        "plan_de_accion": [x.strip() for x in parsed.get("plan_de_accion",[]) if isinstance(x,str)],
        "tacticas_de_los_videos": [x.strip() for x in parsed.get("tacticas_de_los_videos",[]) if isinstance(x,str)],
        "riesgos_y_supuestos": [x.strip() for x in parsed.get("riesgos_y_supuestos",[]) if isinstance(x,str)],
        "confianza": parsed.get("confianza","").strip() or "No estimada",
        "resumen_whatsapp": parsed.get("resumen_whatsapp","").strip(),
    }
