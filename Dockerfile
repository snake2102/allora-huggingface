FROM python:3.11-slim

WORKDIR /app

# Copiar requirements.txt antes de copiar todo, para aprovechar cache
COPY requirements.txt /app

# Instalar dependencias
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la app
COPY . /app

EXPOSE 8000

CMD ["gunicorn", "-b", ":8000", "app:app"]
