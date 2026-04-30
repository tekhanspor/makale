# 🥋 Taekwondo Makale Takip Agent

Her gün otomatik olarak PubMed, arXiv, Semantic Scholar ve DOAJ'dan taekwondo makalelerini tarar.

## Kurulum (10 dakika)

### 1. Bu repoyu fork et
GitHub'da sağ üstte **Fork** butonuna tıkla.

### 2. GitHub Pages'i aç
Repo → **Settings** → **Pages** → Source: `main` branch → `/public` klasörü → **Save**

### 3. Actions'ı etkinleştir
Repo → **Actions** sekmesi → **"I understand my workflows, enable them"**

### 4. İlk taramayı manuel başlat
Actions → **"Günlük Makale Tarama"** → **"Run workflow"** → **"Run workflow"**

### 5. Web sitene gir
`https://KULLANICI_ADIN.github.io/taekwondo-tracker`

---

## Özellikler

- ✅ Her gün saat 09:00 (TR saati) otomatik çalışır
- ✅ Görülen makaleler kaydedilir, tekrar gösterilmez
- ✅ PubMed, arXiv, Semantic Scholar, DOAJ
- ✅ Kaynak ve başlık filtresi
- ✅ Ücretsiz

## Anahtar Kelime Değiştirme

`scraper.py` dosyasında `KEYWORDS` listesini düzenle:

```python
KEYWORDS = [
    "taekwondo",
    "태권도",
    "taekwondo biomechanics",
    # istediğini ekle
]
```
