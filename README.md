# YouTube Music Playlist Builder

Sanatçı listelerinden düzenli RAW YouTube Music playlistleri oluşturmak için hazırlanmış kişisel otomasyon projesi.

Akış:

```text
Sanatçıları ekle → Albüm/single kataloglarını al → Filtrele ve sırala
→ RAW playlist oluştur → YouTube Music'te manuel ele → Telefona indir
```

İlk sürüm yalnızca playlist oluşturma ve organize etme işine odaklanır. Telefon indirmeleri YouTube Music uygulamasından yapılır.

## Kullanım

1. `requirements.txt` içindeki bağımlılıkları kurun.
2. `config.example.yaml` dosyasını `config.yaml` olarak kopyalayın.
3. `artists/*.txt` dosyalarına her satıra bir sanatçı gelecek şekilde isimleri yazın.
4. `auth/oauth.json` dosyasını [ytmusicapi authentication](https://ytmusicapi.readthedocs.io/en/stable/setup/authentication.html) yönergelerine göre hazırlayın.
5. Önce planı kontrol edin: `python build_playlists.py --dry-run`.
6. Playlistleri oluşturun/güncelleyin: `python build_playlists.py`.

Menüyle kullanmak için Windows'ta `run.bat` dosyasına çift tıklayın. Terminalden aynı menü `python build_playlists.py --tui` ile açılır.

Tekrar çalıştırmak güvenlidir. `append_only` modu yeni parçaları ekler; YouTube Music'te manuel sildiğiniz parçaları state üzerinden geri eklemez. `state/build_state.json` çalışma durumunu, `logs/build.jsonl` olayları tutar; bu dosyalar Git'e alınmaz.

Test: `python -m pytest --basetemp=work/pytest-tmp`.

## Dizinler

- `artists/`: Tür bazlı sanatçı listeleri
- `src/`: Uygulama kodu
- `tests/`: Testler
- `state/`: Yerel çalışma durumu; Git'e alınmaz
- `cache/`: API önbelleği; Git'e alınmaz
- `logs/`: Çalışma logları; Git'e alınmaz
- `docs/`: Proje dokümantasyonu
