# 🚦 Trafik Anomalisi Analiz Sistemi (Traffic Anomaly Analysis)

Bu proje, trafik kameralarından alınan veya yüklenen videoları **NVIDIA Cosmos Embed1** (Multimodal Embedding Model) altyapısı kullanarak **sıfır-örnekli (zero-shot)** video sınıflandırma yöntemiyle analiz eden web tabanlı bir sistemdir.

Sistem; trafik kazaları, kavgalar, yoldaki engeller, şerit/kırmızı ışık ihlalleri veya normal trafik akışlarını herhangi bir özel model eğitimi gerektirmeden anlamsal (semantic) metin etiketleri ile video içeriklerini kıyaslayarak tespit eder.

---

## 🌟 Öne Çıkan Özellikler

- **Zero-Shot Multimodal Analiz:** NVIDIA'nın `nvidia/cosmos-embed1` modeli ile video karelerinden ve metin etiketlerinden embedding (vektör temsilleri) çıkarılarak kosinüs benzerliği (*cosine similarity*) hesaplanır.
- **Düzgün Kare Örnekleme (Uniform 8-Frame Sampling):** Videonun başından sonuna kadar eşit aralıklarla 8 kare çıkarılır, 336x336 boyutuna getirilerek Base64 formatında API'ye gönderilir.
- **İki Farklı Çalışma Modu:**
  - **Live Mode (Canlı API):** Gerçek NVIDIA Cloud API'sine bağlanarak canlı analiz yapar.
  - **Simulation Mode (Simülasyon):** API anahtarı olmadığında veya test aşamasında senaryoya göre gerçekçi skorlar üreten çevrimdışı mod.
- **Otomatik Test Videosu Üretimi:** Proje ilk kez çalıştırıldığında (`lifespan` handler ile) test için gereken sentetik videoları OpenCV vasıtasıyla otomatik oluşturur (`accident.mp4`, `fight.mp4`, `obstacle.mp4`, `violation.mp4`, `normal.mp4`).
- **Frontend Hata Günlüğü (Error Logging):** Tarayıcı tarafında oluşan JavaScript hataları sunucuya iletilerek terminale yazdırılır (`/api/log-error`).

---

## 📂 Proje Yapısı

```
.
├── static
│   ├── samples
│   │   ├── accident.mp4
│   │   ├── fight.mp4
│   │   ├── normal.mp4
│   │   ├── obstacle.mp4
│   │   └── violation.mp4
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── app.py
├── requirements.txt
└── video_generator.py
```

## 🛠️ Teknolojiler ve Bağımlılıklar
Backend Framework: FastAPI, Uvicorn, Pydantic

Görüntü & Video İşleme: OpenCV (opencv-python), NumPy

API & İletişim: Requests (NVIDIA API entegrasyonu için)

Frontend: HTML5, CSS3, JavaScript (Vanilla JS)

## 🚀 Kurulum ve Çalıştırma
1. Depoyu Klonlayın
git clone [https://github.com/kullanici-adi/trafik-anomalisi-analizi.git](https://github.com/kullanici-adi/trafik-anomalisi-analizi.git)
cd trafik-anomalisi-analizi

2. Sanal Ortam (Virtual Environment) Oluşturun ve Aktifleştirin
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate

3. Bağımlılıkları Yükleyin
pip install -r requirements.txt

4. NVIDIA API Anahtarını Tanımlayın (Opsiyonel)
Canlı API modunda çalışmak istiyorsanız NVIDIA Build üzerinden aldığınız API anahtarını ortam değişkeni olarak ekleyebilirsiniz:
# Windows (CMD)
set NVIDIA_API_KEY=nvapi-your-key-here

# Linux / macOS
export NVIDIA_API_KEY="nvapi-your-key-here"
(Not: API anahtarını tanımlamasanız dahi uygulama varsayılan olarak Simülasyon Modu'nda sorunsuz çalışacaktır).

5. Sunucuyu Başlatın
python app.py
Uygulama çalıştıktan sonra tarayıcınızdan http://127.0.0.1:8000 adresine giderek arayüzü kullanabilirsiniz.

## 📡 API Uç Noktaları (Endpoints)

- `GET /`
  Web arayüzünü (`static/index.html`) sunar.

- `GET /api/config`
  Mevcut konfigürasyonu (simülasyon modu, API anahtarı durumu, eşik değerleri) getirir.

- `POST /api/config`
  Simülasyon modunu, API endpoint'ini veya threshold değerlerini günceller.

- `POST /api/analyze`
  Yüklenen veya seçilen videoyu verilen etiketler ile analiz eder.

- `POST /api/generate-samples`
  Örnek sentetik videoları `video_generator.py` aracılığıyla yeniden oluşturur.

- `POST /api/log-error`
  Frontend tarafındaki JavaScript hatalarını sunucuya iletir.


## 🔬 Çalışma Prensibi
Girdi Alma: Kullanıcı bilgisayarından bir video yükler veya hazır örnek videolar arasından bir seçim yapar. Ayrıca sorgulamak istediği etiketleri girer (örneğin: kaza, kavga, normal akış).

Kare Çıkarma (Frame Extraction): Videodan eşit zaman aralıklarıyla 8 adet kare örneklenir. Çıkarılan her kare 336x336 piksel boyutuna dönüştürülüp JPEG olarak Base64 dizisine kodlanır.

Embedding Çıkarımı:

8 karelik video paketi nvidia/cosmos-embed1 modeline gönderilerek video embedding'i alınır.

Her bir metin etiketi için ayrı metin embedding'i elde edilir.

Benzerlik Hesabı: Video embedding'i ile metin embedding'leri arasındaki Kosinüs Benzerliği (Cosine Similarity) hesaplanır.

Sonuç: En yüksek benzerlik skoruna sahip etiket tespit edilerek istemciye döndürülür.






