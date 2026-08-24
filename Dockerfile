FROM python:3.11-slim

ENV PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1

# Optional pip index override for building on networks that block
# files.pythonhosted.org directly (e.g. corp proxies). CI/production
# builds leave this unset and use real PyPI.
ARG PIP_INDEX_URL
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

WORKDIR /app

ARG PIP_EXTRA_INDEX_URL
ENV PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL}

COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir --progress-bar off -r requirements.txt -r requirements-test.txt

COPY goodhvac/ goodhvac/
COPY tests/ tests/
COPY pyproject.toml .
COPY alembic.ini .
COPY alembic/ alembic/

EXPOSE 8080

CMD ["uvicorn", "goodhvac.main:app", "--host", "0.0.0.0", "--port", "8080"]
