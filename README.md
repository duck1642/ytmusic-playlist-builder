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
3. Sanatçıları `artists/*.txt` dosyalarına yazın veya TUI içindeki `Sanatçıları düzenle` ekranını kullanın.
4. Google Cloud'dan indirdiğiniz OAuth client JSON dosyasını `auth/client_secret.json` olarak kaydedin.
5. OAuth tokenını oluşturun: `.venv\Scripts\python.exe build_playlists.py --setup-oauth`.
6. Önce planı kontrol edin: `.venv\Scripts\python.exe build_playlists.py --dry-run`.
7. Playlistleri oluşturun/güncelleyin: `.venv\Scripts\python.exe build_playlists.py`.

Menüyle kullanmak için Windows'ta `run.bat` dosyasına çift tıklayın. Textual tabanlı arayüz OAuth durumunu, kategori özetini ve canlı işlem çıktısını gösterir. `D` dry-run, `B` playlist oluşturma/güncelleme, `A` sanatçı listelerini düzenleme, `R` yenileme ve `Q` çıkış tuşlarıdır. Sanatçı editöründe kategori seçip sanatçı ekleyebilir, düzenleyebilir, silebilir ve `S` ile ilgili `artists/<kategori>.txt` dosyasına kaydedebilirsiniz. OAuth düğmesi, bloklayan Google akışı için arayüzü geçici olarak kapatır ve işlem bitince yeniden açar. Terminalden aynı arayüz `.venv\Scripts\python.exe build_playlists.py --tui` ile açılır.

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
