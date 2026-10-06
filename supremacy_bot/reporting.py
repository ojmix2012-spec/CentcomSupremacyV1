from urllib.parse import quote


def _bullets(items: list[str], empty_text: str) -> str:
    if not items:
        return f"- {empty_text}"
    return "\n".join(f"- {item}" for item in items)


def build_markdown_report(
    result: dict,
    transcripts: list[dict],
    created_at: str,
) -> str:
    sources = []
    for transcript in transcripts:
        url = transcript.get("url")
        if url and url not in sources:
            sources.append(url)
    source_lines = [f"- [{url}]({url})" for url in sources] or ["- No se adjuntaron videos."]

    return "\n".join(
        [
            "# Supremacy 1914 · Informe de estrategia",
            f"Generado: {created_at}",
            "",
            "## Lectura del mapa",
            result.get("lectura_del_mapa", ""),
            "",
            "## Plan recomendado",
            _bullets(result.get("plan_de_accion", []), "No se generaron pasos concretos."),
            "",
            "## Tácticas extraídas de los videos",
            _bullets(result.get("tacticas_de_los_videos", []), "No se proporcionaron transcripciones."),
            "",
            "## Riesgos y supuestos",
            _bullets(result.get("riesgos_y_supuestos", []), "No se señalaron riesgos específicos."),
            "",
            f"**Confianza:** {result.get('confianza', 'No estimada')}",
            "",
            "## Fuentes",
            *source_lines,
            "",
            "_Informe de apoyo; verifica la situación en el juego antes de actuar._",
        ]
    )


def build_whatsapp_message(result: dict, transcripts: list[dict]) -> str:
    summary = (result.get("resumen_whatsapp") or "").strip()
    if not summary:
        priorities = result.get("plan_de_accion", [])[:3]
        summary = result.get("lectura_del_mapa", "Análisis de partida")
        if priorities:
            summary += "\n\nPrioridades:\n" + "\n".join(f"• {item}" for item in priorities)

    sources = []
    for transcript in transcripts:
        url = transcript.get("url")
        if url and url not in sources:
            sources.append(url)

    message = "*Supremacy 1914 · Informe de estrategia*\n\n" + summary
    if sources:
        message += "\n\nVideos:\n" + "\n".join(sources[:3])
    if len(message) > 1200:
        message = message[:1197].rstrip() + "…"
    return message


def whatsapp_link(message: str) -> str:
    return f"https://wa.me/?text={quote(message, safe='')}"
