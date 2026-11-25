FROM python:3.12-slim

ARG APP_VERSION=dev
ARG FAULT_ERROR_RATE=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_VERSION=${APP_VERSION} \
    FAULT_ERROR_RATE=${FAULT_ERROR_RATE}

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./

RUN useradd --uid 10001 --no-create-home app
USER 10001

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]