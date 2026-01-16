FROM python:3.9-slim
WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc

RUN pip install fastapi uvicorn psycopg2-binary passlib[bcrypt] "bcrypt==4.0.1" python-jose[cryptography] python-multipart

COPY . /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
