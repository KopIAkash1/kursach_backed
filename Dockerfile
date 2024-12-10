FROM python:3.12
WORKDIR /var/www/html
COPY requirements.txt .
RUN python3.12 -m pip install --no-cache-dir -r requirements.txt
COPY ./aplication /var/www/html
EXPOSE 8000
CMD ["python3.12", "-m", "uvicorn", "app:app","--host","0.0.0.0","--port","8000"]
