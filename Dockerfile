# Python'un resmi imajını kullan
FROM python:3.9

# Çalışma dizinini oluştur
WORKDIR /app

# Gerekli dosyaları kopyala
COPY requirements.txt requirements.txt
COPY . .

# Google Cloud Run için 8080 portunu aç
EXPOSE 8080

# Bağımlılıkları yükle
RUN pip install --no-cache-dir -r requirements.txt

# Streamlit uygulamasını başlat
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false", "--server.address=0.0.0.0"]
