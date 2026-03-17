# Yapay Zeka Destekli İşletme Asistanı (Generic AI Agent)

Bu proje, herhangi bir işletmenin (restoran, klinik, kuaför, danışmanlık vb.) kendi PDF dokümanlarını okuyarak kurallarını otomatik olarak öğrenen ve bu kurallar çerçevesinde müşterilerle doğal dilde yazışıp **sipariş alan** ve **randevu oluşturan** yapay zeka tabanlı bir asistandır.

Proje, Google'ın gelişmiş Gemini altyapısı ve modern RAG (Retrieval-Augmented Generation) + LangGraph mimarisi kullanılarak geliştirilmiştir.

## 🚀 Öne Çıkan Özellikler

- **İşletme Bağımsız Mimari (Generic):** Kodun içine gömülü (hardcoded) kural yoktur. İşletmenin tüm menüsü, vergi oranları, çalışma saatleri, randevu süreleri ve teslimat ücretleri gibi bilgiler yüklenen PDF'ten otomatik olarak çekilir (Gemini Information Extraction).
- **Gelişmiş Hafıza ve Karar Alma (LangGraph):** Kullanıcının ne istediğini anlar (Sipariş mi? Randevu mu? Sadece soru mu?). Konuşma geçmişini (Session) hatırlar ve bağlama uygun cevaplar verir.
- **Dinamik RAG Modülü:** Kullanıcı işletme hakkında bir şey sorduğunda doğrudan FAISS vektör veritabanında arama yaparak PDF içerisinden en doğru cevabı verir uydurma (hallucination) yapmaz.
- **Hazır Araçlar (Tools):** Yapay zeka, eksik bilgi hissettiğinde sepeti güncelleyebilir, toplam tutarı hesaplayabilir ve veritabanına doğrudan kayıt atabilir.
- **Taşınabilir Veritabanı:** Kurulumu kolaylaştırmak için arka planda yerleşik SQLite kullanılmaktadır (Bulut veritabanı gereksinimi yoktur).

## 🛠 Teknik Altyapı
- **Backend Framekwork:** FastAPI (Python)
- **AI/LLM:** Google Gemini (1.5 Flash) ve Gemini Embeddings
- **Orkestrasyon & Chain:** LangChain ve LangGraph
- **Vektör Veritabanı:** FAISS
- **İlişkisel Veritabanı:** SQLite
- **Loglama:** Structlog

## 📦 Kurulum

1. **Python Kurulumu:** 
   Bilgisayarınızda Python (3.10 veya üzeri) kurulu olduğundan emin olun.

2. **Bağımlılıkların Yüklenmesi:**
   Proje dizininde terminali açın ve gerekli kütüphaneleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

3. **API Anahtarı Ayarları (Environment Variables):**
   - Proje ana dizininde bulunan `.env.example` veya `.env` dosyasını açın.
   - `GOOGLE_API_KEY` yazan kısma kendi Google Gemini API anahtarınızı girin.
   - Örnek kullanım: `GOOGLE_API_KEY=AIzaSyA...`

## ⚙️ Sistemi Çalıştırma

Projeyi başlatmak oldukça basittir. Proje ana dizinindeyken oluşturulmuş olan batch dosyasını çalıştırabilirsiniz:

```bash
run_system.bat
```

Veya doğrudan terminal üzerinden başlatmak için:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000
```
Sistem çalışmaya başladığında API dokümantasyonuna tarayıcınızdan http://localhost:5000/docs adresinden ulaşabilirsiniz.

## 📚 Kullanım Senaryosu

Sistem iki temel adımdan oluşur:
1. **İşletmeyi Sisteme Tanıtma:** 
   Her işletmenin kendi bilgilerini içeren PDF dokümanı sisteme `/business/load_pdf` endpoint'i üzerinden yüklenir.  Yükleme sırasında belge ayrıştırılır (chunking), vektörleştirilir (embedding) ve kuralları yapay zeka algoritmasıyla okunarak JSON formatında profile kaydedilir.
2. **Sohbet (Chat):**
   Sisteme işletme eklendikten sonra, `/agent/chat` endpoint'ine mesaj gönderilir (`session_id` ve `business_name` belirtilerek). Asistan, müşteri ne isterse işletmenin yeteneklerine göre yanıt verir ve işlemleri tamamlar.

## 🔒 Güvenlik Uyarıları
- **API Anahtarı Gizliliği:** Bu proje testlerden geçmiş olup Google API anahtarınız .env içerisine konumlandırılmıştır, gerçek sunucularda `.env` anahtarını güvende tutunuz. Kaynak kodlar direkt paylaşılırken anahtarın kaldırıldığından emin olunmuştur.

---
**Telif ve Yapım:** Bu mimari, tamamen ölçeklenebilir ve satılabilir bir altyapı olarak tasarlanmıştır. Tüm hakları ve kod yapısı işletmeye entegre edilmek üzere özelleştirilebilir.
