# Asistente de estrategia para Supremacy 1914

Aplicación local en Python para analizar capturas del mapa con Gemini, extraer tácticas de subtítulos públicos de YouTube y preparar un informe para compartir por WhatsApp.

## Cómo usarla

1. Añade `GEMINI_API_KEY` en **Secrets** del proyecto. La clave no se guarda en el código.
2. Inicia el workflow **Supremacy Strategy Assistant**.
3. En la vista de la aplicación, sube una captura PNG, JPEG o WebP.
4. Opcionalmente, añade hasta tres enlaces de YouTube (uno por línea), una transcripción manual y contexto de la partida.
5. Pulsa **Analizar captura y estrategias**. El informe muestra el plan, riesgos y las tácticas resumidas.
6. Pulsa **Abrir WhatsApp con el informe** para revisar el borrador, elegir un chat y confirmar el envío. También puedes descargar el informe completo en Markdown.

## Límites

- Solo lee la captura y subtítulos disponibles; no inicia sesión en el juego, no hace clic ni mueve unidades.
- YouTube debe ofrecer subtítulos accesibles. Si no, pega la transcripción en el campo de notas.
- Las imágenes y transcripciones se envían a Gemini para el análisis y no se guardan como archivos en la aplicación. El informe queda en la sesión actual. El uso se factura a la cuenta de Google asociada con tu clave.
- El botón de WhatsApp crea un borrador en `wa.me`; no envía mensajes automáticamente.
- Gemini puede interpretar mal detalles pequeños del mapa. Comprueba las observaciones y la confianza antes de actuar.

## Ejecutar manualmente

```bash
streamlit run main.py --server.port 5000 --server.address 0.0.0.0 --server.headless true
```

## Comprobación local

```bash
python -m unittest discover -s tests
```
