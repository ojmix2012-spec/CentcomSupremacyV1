from typing import List, Dict, Optional, Union
import urllib.parse
import json

def _as_str(x):
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return x.get("texto") or x.get("descripcion") or x.get("paso") or x.get("tactic") or x.get("title") or str(x)
    if isinstance(x, list):
        return "\n".join([_as_str(i) for i in x])
    return str(x) if x is not None else ""

def _as_list_str(arr):
    if not arr:
        return []
    if isinstance(arr, str):
        return [arr]
    return [_as_str(i) for i in arr]

def build_markdown_report(result: Dict, transcripts: List[Dict], created_at: str) -> str:
    lectura = _as_str(result.get("lectura_del_mapa", "No disponible"))
    plan = _as_list_str(result.get("plan_de_accion", []))
    tacticas = _as_list_str(result.get("tacticas_de_los_videos", []))
    riesgos = _as_list_str(result.get("riesgos_y_supuestos", []))
    confianza = _as_str(result.get("confianza", "No definida"))
    modelo = result.get("_modelo_usado", "no registrado")

    sources = []
    for t in transcripts or []:
        if isinstance(t, dict):
            url = t.get("url") or t.get("label") or ""
            if url:
                sources.append(url)
        elif isinstance(t, str) and t:
            sources.append(t)

    source_lines = [f"- [{url}]({url})" for url in sources] if sources else ["- No se proporcionaron fuentes"]

    md = [
        "# Supremacy 1914 · Informe de estrategia",
        f"Generado: {created_at}",
        f"Modelo: {modelo} | Proyecto: inspiring-wares-250700 Free tier 5 RPM (ver screenshots Rate Limit)",
        "",
        "## Lectura del mapa",
        lectura,
        "",
        "## Plan de acción",
    ]
    for i, p in enumerate(plan, 1):
        if p.strip():
            md.append(f"{i}. {p}")
    if not plan:
        md.append("- No se generó plan")

    md += ["", "## Tácticas de los videos", ""]
    for t in tacticas:
        if t.strip():
            md.append(f"- {t}")
    if not tacticas:
        md.append("- No se extrajeron tácticas")

    md += ["", "## Riesgos y supuestos", ""]
    for r in riesgos:
        if r.strip():
            md.append(f"- {r}")
    if not riesgos:
        md.append("- No se identificaron riesgos")

    md += ["", f"**Confianza:** {confianza}", "", "## Fuentes", ""]
    md.extend(source_lines)
    md = [m if isinstance(m, str) else str(m) for m in md]
    return "\n".join(md)

def build_whatsapp_message(result: Union[Dict, str], transcripts: Optional[List[Dict]] = None, created_at: str = "") -> str:
    if isinstance(result, str):
        return result
    plan = _as_list_str(result.get("plan_de_accion", []))[:4]
    lectura = _as_str(result.get("lectura_del_mapa", ""))[:600]
    confianza = _as_str(result.get("confianza", ""))
    msg = f"*Supremacy 1914 - Informe*\n\n{lectura}\n\n*Plan:*\n"
    for i, p in enumerate(plan, 1):
        msg += f"{i}. {p}\n"
    msg += f"\n_Confianza: {confianza}_"
    if created_at:
        msg += f"\n{created_at}"
    return msg

def whatsapp_link(result_or_message: Union[Dict, str], phone: str = "") -> str:
    if isinstance(result_or_message, str):
        message = result_or_message
    else:
        message = build_whatsapp_message(result_or_message)
    encoded = urllib.parse.quote(message)
    if phone:
        return f"https://wa.me/{phone}?text={encoded}"
    return f"https://wa.me/?text={encoded}"

def build_whatsapp_link(result: Union[Dict, str], phone: str = "") -> str:
    return whatsapp_link(result, phone)

def build_export_bundle(result: Dict, transcripts: List[Dict], created_at: str, game_context: str, yt_links: List[str], image_meta: Dict, model_candidates: List[str]) -> Dict:
    """Paquete auditable para cualquier IA - usado por main.py export"""
    return {
        "app": "CentcomSupremacyV1",
        "repo": "https://github.com/ojmix2012-spec/CentcomSupremacyV1",
        "generated_at": created_at,
        "project": "Centcom App / inspiring-wares-250700",
        "billing_tier": "Free tier",
        "rate_limit_observed": {
            "screenshot_154648": "Gemini 3.5 Flash 3/5 RPM 1.05K/250K, Gemini 3.8 Flash 3/5 RPM 1.08K/250K",
            "screenshot_154633": "Gemini 3.1 Flash Lite 0/15 RPM, 3.5 Flash Lite 0/15 RPM, 3.6/3.7 Flash 0/5 RPM",
            "screenshot_154739": "Logs API storage OFF - GenerateContent not stored unless store:true",
        },
        "model_candidates_used": model_candidates,
        "model_final": result.get("_modelo_usado", "unknown"),
        "image": image_meta,
        "game_context": game_context,
        "youtube_links": yt_links,
        "transcripts": transcripts,
        "gemini_raw_result": result,
    }
