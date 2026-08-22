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
7. Sanatçı dosyalarının formatını ve yerel duplicate'lerini ağ kullanmadan kontrol edin: `.venv\Scripts\python.exe build_playlists.py --validate-format`. Kesin duplicate satırları için uygulama planı gösterilir; dosya yalnızca onay verirseniz değişir.
8. Sanatçıların YouTube Music'te gerçekten çözüldüğünü ve aynı channel ID'nin tekrarlanmadığını kontrol edin: `.venv\Scripts\python.exe build_playlists.py --validate-remote`. Bu komut OAuth/API kullanır ve TXT düzeltmelerinden önce ayrıca onay ister.
9. Playlistleri oluşturun/güncelleyin: `.venv\Scripts\python.exe build_playlists.py`.

Sanatçı dosyalarında düz isim, YouTube kanal URL'si veya ikisi birlikte kullanılabilir:

```text
Radiohead
https://music.youtube.com/@radiohead
Radiohead | https://music.youtube.com/channel/UCq19-LqvG35A-30oyAiPiqA
```

`channel/<id>` URL'si doğrudan kullanılır. `@handle` URL'si, handle ile sanatçı araması yapılarak çözülür. `isim | URL` formatında URL kaynak olarak önceliklidir; isim loglarda ve katalog sıralamasında görünen etiket olarak kullanılır.

Menüyle kullanmak için Windows'ta `run.bat` dosyasına çift tıklayın. Textual tabanlı arayüz OAuth durumunu, playlist özetini ve canlı işlem çıktısını gösterir. Ana ekranda `D` plan, `B` playlist oluşturma/güncelleme, `V` format doğrulama, `U` uzak doğrulama, `A` playlist editörü, `R` yenileme ve `Q` çıkış tuşlarıdır. `Ctrl+P` native command palette'i açar; ana işlemler ve Textual komutları buradan aranabilir. `V` ağ kullanmaz; güvenli duplicate silme planını gösterir. `U` API kullandığı için arayüzü geçici olarak kapatır, terminalde uzak doğrulama ve onay akışını çalıştırır. `Ctrl+Left` / `Ctrl+Right` sol paneli daraltır/genişletir, `Ctrl+0` varsayılan boyuta döner. Editörde `N` yeni playlist, `M` ad değiştirme, `P` playlist dosyası silme, `A` sanatçı ekleme, `E` düzenleme, `X` sanatçı silme, `S` kaydetme ve `R` diskten yükleme kısayollarıdır; aynı `Ctrl+Left` / `Ctrl+Right` / `Ctrl+0` kısayolları playlist panelini değiştirir. Playlist adı dosyanın uzantısız adıyla aynıdır; RAW adını istiyorsanız dosyayı örneğin `METAL - RAW.txt` olarak adlandırın. Editörden silmek yalnızca yerel `.txt` dosyasını kaldırır; YouTube Music'teki mevcut playlist otomatik silinmez. OAuth düğmesi, bloklayan Google akışı için arayüzü geçici olarak kapatır ve işlem bitince yeniden açar. Windows TUI'sinde mouse desteği yalnızca tıklama ve tekerlek olaylarını raporlar; pasif mouse hareketleri izlenmez. Terminalden aynı arayüz `.venv\Scripts\python.exe build_playlists.py --tui` ile açılır.

Tekrar çalıştırmak güvenlidir. `append_only` modu yeni parçaları ekler; YouTube Music'te manuel sildiğiniz parçaları state üzerinden geri eklemez. `state/build_state.json` çalışma durumunu, `logs/build.jsonl` olayları tutar; bu dosyalar Git'e alınmaz.

Sanatçı çözümleme sonuçları `state/build_state.json` içindeki `artist_aliases` alanında tutulur. `artist_cache_ttl_days` varsayılan olarak 30 gündür; `0` değeri kalıcı alias cache'ini devre dışı bırakır. Aynı playlistte aynı normalize edilmiş girdi veya aynı çözümlenmiş `channel_id` tekrar gelirse ikinci katalog çağrısı atlanır; farklı playlistlerde aynı sanatçı tutulur, ancak katalog verisi build boyunca bellekte paylaşılır. `--validate-format` ve `--validate-remote` TXT dosyalarını yalnızca kullanıcı onayından sonra değiştirir; normal build akışı validator çalıştırmaz ve TXT dosyalarına yazmaz.

Test: `python -m pytest --basetemp=work/pytest-tmp`.

## Dizinler

- `artists/`: Playlist adını ve sanatçı listesini taşıyan `.txt` dosyaları
- `src/`: Uygulama kodu
- `tests/`: Testler
- `state/`: Yerel çalışma durumu; Git'e alınmaz
- `cache/`: API önbelleği; Git'e alınmaz
- `logs/`: Çalışma logları; Git'e alınmaz
- `docs/`: Proje dokümantasyonu
