# Docker-SDK Hugging Face Space for the carbon-style dashboard (web/).
# The default Gradio Space uses app.py + README frontmatter (sdk: gradio) and
# ignores this file; only the dedicated Docker Space builds from it.
FROM python:3.11-slim

WORKDIR /app

# Install the clinical_agent package + web deps first (better layer caching).
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY web/requirements.txt ./web/requirements.txt
RUN pip install --no-cache-dir -r web/requirements.txt \
 && pip install --no-cache-dir .

# App code + data (corpus, writable analytics dir).
COPY web/ ./web/
COPY data/ ./data/

ENV PORT=7860
EXPOSE 7860

# --app-dir web puts web/ on sys.path so `server:app` resolves; clinical_agent
# is imported from the installed package.
CMD ["uvicorn", "server:app", "--app-dir", "web", "--host", "0.0.0.0", "--port", "7860"]
