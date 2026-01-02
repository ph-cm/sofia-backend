# 1. Imagem base com Python
FROM python:3.11-slim

# 2. Evita criação de arquivos .pyc e ativa logs imediatos
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Diretório de trabalho dentro do container
WORKDIR /app

# 4. Copia o requirements.txt primeiro (cache inteligente)
COPY requirements.txt .

# 5. Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copia TODO o código do projeto
COPY . .

# 7. Expõe a porta do FastAPI
EXPOSE 8000

# 8. Comando para rodar a aplicação
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
