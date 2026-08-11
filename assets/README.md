# 📁 Assets Klasörü

## Template Video

Bu klasöre **`story-template.mp4`** adında bir video eklemeniz gerekiyor.

### Video Özellikleri:
- **Boyut**: 1080x1920 (Instagram Story 9:16)
- **Süre**: 5-10 saniye
- **Format**: MP4 (H.264)
- **FPS**: 30

### Nasıl Hazırlanır?

#### Canva ile (Kolay):
1. https://www.canva.com adresine gidin
2. "Instagram Story" boyutu seçin
3. Animasyonlu şablon oluşturun:
   - Gradient arka plan
   - Ses dalgası animasyonu
   - Logo
   - Uygulama adı
4. MP4 olarak indirin
5. `story-template.mp4` olarak bu klasöre kaydedin

#### Örnek İçerik:
```
┌─────────────────────┐
│                     │
│    [LOGO]           │  ← Üst kısım
│                     │
│   ≈≈≈≈≈≈≈≈≈≈≈      │  ← Animasyonlu
│   ≈≈≈≈≈≈≈≈≈≈≈      │     ses dalgaları
│   ≈≈≈≈≈≈≈≈≈≈≈      │
│                     │
│  "Uygulama Adı"    │  ← Alt kısım
│                     │
└─────────────────────┘
```

### Dosya Yapısı:
```
backend/assets/
├── README.md (bu dosya)
└── story-template.mp4 (sizin eklemeniz gereken)
```

### Test Video:
Eğer hemen test etmek istiyorsanız, geçici olarak herhangi bir 9:16 video kullanabilirsiniz.

### Önemli Notlar:
- Video loop'lanacak (şarkı süresince tekrar edecek)
- Video üzerine müzik eklenecek
- Instagram Story formatında export edilecek
- Kaliteli bir video kullanın (minimum 1080p)
