# 🎬 HTML'i Video Olarak Kaydetme Talimatı

## 📋 Adım Adım Rehber

### 1️⃣ HTML'i Tarayıcıda Açın

```bash
# Terminal'de:
cd /Users/zece/Desktop/projects/Musician/backend/assets
open story-template.html
```

**VEYA**

- Finder'da `story-template.html` dosyasına çift tıklayın
- Chrome veya Safari'de açılacak

---

### 2️⃣ Tam Ekran Yapın

1. Tarayıcı penceresini **tam ekran** yapın (F11 veya Cmd+Ctrl+F)
2. Zoom seviyesini **%100** yapın (Cmd+0)
3. Pencere boyutu tam olarak **1080x1920** olmalı

**Kontrol:**
- Sağ tık → "Inspect" → Console'da yazın:
```javascript
console.log(window.innerWidth, window.innerHeight);
// Çıktı: 1080 1920 olmalı
```

---

### 3️⃣ Ekran Kaydı Yapın

#### **macOS (Önerilen):**

**Yöntem 1: QuickTime Player**
1. QuickTime Player'ı açın
2. File → New Screen Recording
3. Kayıt seçeneklerini ayarlayın:
   - Mikrofon: Kapalı
   - Kalite: Maksimum
4. Tarayıcı penceresini seçin
5. **8 saniye** kayıt yapın
6. Durdur ve kaydet: `story-template.mov`

**Yöntem 2: macOS Screenshot (Hızlı)**
1. `Cmd + Shift + 5` tuşlarına basın
2. "Record Selected Portion" seçin
3. Tarayıcı penceresini seçin
4. Kayda başlayın
5. **8 saniye** bekleyin
6. Menü bar'dan "Stop" tıklayın
7. Desktop'ta `Screen Recording.mov` olarak kaydedilir

#### **Windows:**

**Yöntem 1: Xbox Game Bar**
1. `Win + G` tuşlarına basın
2. Capture widget'ı açın
3. Kayıt butonuna tıklayın
4. **8 saniye** bekleyin
5. Durdur
6. Videos/Captures klasöründe bulun

**Yöntem 2: OBS Studio (Profesyonel)**
1. OBS Studio'yu indirin ve kurun
2. Source → Browser ekleyin
3. URL: `file:///path/to/story-template.html`
4. Width: 1080, Height: 1920
5. Start Recording
6. **8 saniye** bekleyin
7. Stop Recording

---

### 4️⃣ Video'yu Dönüştürün (MOV → MP4)

#### **macOS/Linux:**

```bash
# FFmpeg ile dönüştür
ffmpeg -i story-template.mov \
  -c:v libx264 \
  -preset fast \
  -crf 23 \
  -pix_fmt yuv420p \
  -an \
  story-template.mp4

# Dosya boyutunu kontrol et
ls -lh story-template.mp4
```

#### **Online Tool (Kolay):**

1. https://cloudconvert.com/mov-to-mp4
2. MOV dosyasını yükle
3. MP4'e dönüştür
4. İndir

---

### 5️⃣ Video'yu Kontrol Edin

**Özellikler:**
- ✅ Format: MP4
- ✅ Boyut: 1080x1920
- ✅ Süre: 8 saniye
- ✅ FPS: 30
- ✅ Ses: YOK (sadece görsel)
- ✅ Dosya boyutu: 5-15 MB

**Kontrol komutları:**

```bash
# Video bilgilerini görüntüle
ffprobe story-template.mp4

# Boyut kontrolü
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 story-template.mp4
# Çıktı: 1080x1920 olmalı

# Süre kontrolü
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 story-template.mp4
# Çıktı: 8.000000 civarı olmalı
```

---

### 6️⃣ Video'yu Yerleştirin

```bash
# Video'yu backend assets klasörüne kopyalayın
cp story-template.mp4 /Users/zece/Desktop/projects/Musician/backend/assets/

# Kontrol edin
ls -lh /Users/zece/Desktop/projects/Musician/backend/assets/story-template.mp4
```

---

## 🎯 Hızlı Yöntem (5 Dakika)

### **En Basit: Chrome Extension**

1. **Extension Kurun:**
   - Chrome Web Store'dan "Screen Recorder" ara
   - Önerilen: "Awesome Screenshot & Screen Recorder"
   - Kur

2. **Kayıt Yapın:**
   - HTML'i Chrome'da aç
   - Extension ikonuna tıkla
   - "Record Desktop" → "Current Tab" seç
   - 8 saniye kaydet
   - İndir (MP4 olarak)

3. **Yerleştir:**
   - İndirilen dosyayı `story-template.mp4` olarak yeniden adlandır
   - Backend assets klasörüne kopyala

---

## 🎨 Kalite Ayarları

### **Optimal Ayarlar:**

```bash
# Yüksek kalite (önerilen)
ffmpeg -i input.mov \
  -c:v libx264 \
  -preset slow \
  -crf 18 \
  -pix_fmt yuv420p \
  -vf "scale=1080:1920:flags=lanczos" \
  -an \
  story-template.mp4

# Orta kalite (hızlı)
ffmpeg -i input.mov \
  -c:v libx264 \
  -preset fast \
  -crf 23 \
  -pix_fmt yuv420p \
  -an \
  story-template.mp4

# Düşük boyut (mobil için)
ffmpeg -i input.mov \
  -c:v libx264 \
  -preset fast \
  -crf 28 \
  -pix_fmt yuv420p \
  -an \
  story-template.mp4
```

---

## ⚠️ Önemli Notlar

1. **Ses Olmamalı:**
   - Video'da ses olmamalı (müzik backend'de eklenecek)
   - `-an` parametresi ses'i kaldırır

2. **Boyut:**
   - Tam olarak 1080x1920 olmalı
   - Farklı boyutlar Instagram Story'de sorun çıkarır

3. **Süre:**
   - 8 saniye ideal
   - Daha kısa: Çok hızlı loop (dikkat dağıtıcı)
   - Daha uzun: Dosya boyutu artar

4. **Loop:**
   - Animasyonlar smooth loop yapmalı
   - Başlangıç = Bitiş olmalı

5. **Kalite:**
   - CRF 18-23 arası ideal
   - CRF 18: Yüksek kalite, büyük dosya
   - CRF 23: İyi kalite, orta dosya
   - CRF 28: Düşük kalite, küçük dosya

---

## 🐛 Sorun Giderme

### **Video çok büyük (>20 MB):**
```bash
# Sıkıştır
ffmpeg -i story-template.mp4 \
  -c:v libx264 \
  -crf 28 \
  -preset fast \
  story-template-compressed.mp4
```

### **Boyut yanlış:**
```bash
# Yeniden boyutlandır
ffmpeg -i story-template.mp4 \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" \
  story-template-resized.mp4
```

### **FPS çok yüksek:**
```bash
# FPS'i 30'a düşür
ffmpeg -i story-template.mp4 \
  -r 30 \
  story-template-30fps.mp4
```

---

## ✅ Son Kontrol

Video hazır olduğunda:

- [ ] Dosya adı: `story-template.mp4`
- [ ] Konum: `backend/assets/story-template.mp4`
- [ ] Boyut: 1080x1920
- [ ] Süre: 8 saniye
- [ ] Format: MP4 (H.264)
- [ ] Ses: YOK
- [ ] Dosya boyutu: 5-15 MB
- [ ] Animasyonlar smooth loop

**Test:**
```bash
# Backend'i başlat
cd /Users/zece/Desktop/projects/Musician/backend
python test_server.py

# Uygulamayı başlat
cd /Users/zece/Desktop/projects/Musician
npm start

# Story butonunu test et!
```

---

## 🎉 Tamamlandı!

Video hazır olduğunda backend otomatik olarak kullanacak! 🚀
