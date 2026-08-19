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
3. TUI içindeki `Playlistleri düzenle` ekranından playlist oluşturun; her playlist için aynı adla bir `artists/<playlist adı>.txt` dosyası oluşturulur. Sanatçıları bu ekrandan da yönetebilirsiniz.
4. Google Cloud'dan indirdiğiniz OAuth client JSON dosyasını `auth/client_secret.json` olarak kaydedin.
5. OAuth tokenını oluşturun: `.venv\Scripts\python.exe build_playlists.py --setup-oauth`.
6. Önce planı kontrol edin: `.venv\Scripts\python.exe build_playlists.py --dry-run`.
7. Playlistleri oluşturun/güncelleyin: `.venv\Scripts\python.exe build_playlists.py`.

Menüyle kullanmak için Windows'ta `run.bat` dosyasına çift tıklayın. Textual tabanlı arayüz OAuth durumunu, playlist özetini ve canlı işlem çıktısını gösterir. `D` dry-run, `B` playlist oluşturma/güncelleme, `A` playlist editörü, `R` yenileme ve `Q` çıkış tuşlarıdır. Editörde `N` yeni playlist, `M` ad değiştirme, `P` playlist dosyası silme, `A` sanatçı ekleme, `E` düzenleme, `X` sanatçı silme, `S` kaydetme ve `R` diskten yükleme kısayollarıdır. Playlist adı dosyanın uzantısız adıyla aynıdır; RAW adını istiyorsanız dosyayı örneğin `METAL - RAW.txt` olarak adlandırın. Editörden silmek yalnızca yerel `.txt` dosyasını kaldırır; YouTube Music'teki mevcut playlist otomatik silinmez. OAuth düğmesi, bloklayan Google akışı için arayüzü geçici olarak kapatır ve işlem bitince yeniden açar. Terminalden aynı arayüz `.venv\Scripts\python.exe build_playlists.py --tui` ile açılır.

Tekrar çalıştırmak güvenlidir. `append_only` modu yeni parçaları ekler; YouTube Music'te manuel sildiğiniz parçaları state üzerinden geri eklemez. `state/build_state.json` çalışma durumunu, `logs/build.jsonl` olayları tutar; bu dosyalar Git'e alınmaz.

Test: `python -m pytest --basetemp=work/pytest-tmp`.

## Dizinler

- `artists/`: Playlist adını ve sanatçı listesini taşıyan `.txt` dosyaları
- `src/`: Uygulama kodu
- `tests/`: Testler
- `state/`: Yerel çalışma durumu; Git'e alınmaz
- `cache/`: API önbelleği; Git'e alınmaz
- `logs/`: Çalışma logları; Git'e alınmaz
- `docs/`: Proje dokümantasyonu
