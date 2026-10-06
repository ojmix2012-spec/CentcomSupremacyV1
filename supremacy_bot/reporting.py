from typing import List, Dict

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
    result = []
    for i in arr:
        result.append(_as_str(i))
    return result

def build_markdown_report(result: Dict, transcripts: List[Dict], created_at: str) -> str:
    lectura = _as_str(result.get("lectura_del_mapa", "No disponible"))
    plan = _as_list_str(result.get("plan_de_accion", []))
    tacticas = _as_list_str(result.get("tacticas_de_los_videos", []))
    riesgos = _as_list_str(result.get("riesgos_y_supuestos", []))
    confianza = _as_str(result.get("confianza", "No definida"))

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
        md.append("- No se extrajeron tácticas (agrega links de YouTube para mejorar)")

    md += ["", "## Riesgos y supuestos", ""]
    for r in riesgos:
        if r.strip():
            md.append(f"- {r}")
    if not riesgos:
        md.append("- No se identificaron riesgos")

    md += ["", f"**Confianza:** {confianza}", "", "## Fuentes", ""]
    md.extend(source_lines)

    # Filtra cualquier dict que se haya colado
    md = [m if isinstance(m, str) else str(m) for m in md]
    return "\n".join(md)

def build_whatsapp_message(result: Dict) -> str:
    plan = _as_list_str(result.get("plan_de_accion", []))[:4]
    lectura = _as_str(result.get("lectura_del_mapa", ""))[:500]
    confianza = _as_str(result.get("confianza", ""))

    msg = f"*Supremacy 1914 - Informe*\n\n{lectura}\n\n*Plan:*\n"
    for i, p in enumerate(plan, 1):
        msg += f"{i}. {p}\n"
    msg += f"\n_Confianza: {confianza}_"
    return msg
