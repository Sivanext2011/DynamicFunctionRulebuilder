FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir flask

COPY src/ src/
COPY web/ web/
COPY cha_compile.py .
COPY examples/ examples/
COPY docs/GENAI_PROMPT_TEMPLATE.md docs/

EXPOSE 3002

CMD ["python", "web/app.py"]
