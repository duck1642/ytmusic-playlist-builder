# YouTube Music Playlist Builder

Sanatçı listelerinden düzenli RAW YouTube Music playlistleri oluşturmak için hazırlanacak kişisel otomasyon projesi.

Akış:

```text
Sanatçıları ekle → Albüm/single kataloglarını al → Filtrele ve sırala
→ RAW playlist oluştur → YouTube Music'te manuel ele → Telefona indir
```

İlk sürüm yalnızca playlist oluşturma ve organize etme işine odaklanır. Telefon indirmeleri YouTube Music uygulamasından yapılır.

## Dizinler

- `artists/`: Tür bazlı sanatçı listeleri
- `src/`: Uygulama kodu
- `tests/`: Testler
- `state/`: Yerel çalışma durumu; Git'e alınmaz
- `cache/`: API önbelleği; Git'e alınmaz
- `logs/`: Çalışma logları; Git'e alınmaz
- `docs/`: Proje dokümantasyonu
