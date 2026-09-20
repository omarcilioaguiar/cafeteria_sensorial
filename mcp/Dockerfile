FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home app
COPY server.py rest_client.py tools_graos.py tools_metodos.py tools_degustacoes.py ./
USER app
EXPOSE 8000
CMD ["python", "server.py"]
