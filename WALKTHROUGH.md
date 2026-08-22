# WALKTHROUGH.md

## Project
YouTube Music için tür bazlı RAW playlistler oluşturan bir otomasyon sistemi. Amaç, sanatçıların albüm ve single kataloglarını hızlıca playlistlere eklemek ve sonrasında YouTube Music içinde manuel eleme yaparak telefona indirmektir.

## Current State
Yerel config, sanatçı listesi okuma, JSON state ve JSONL event log, `ytmusicapi` adaptörü, katalog dönüşümü, append-only playlist yazma, minimal CLI ve küçük interaktif TUI hazır. Proje içi `.venv`, `ytmusicapi`/`PyYAML` bağımlılıkları ve Git dışı `config.yaml` hazır. Windows launcher `.venv` Python'unu kullanıyor. OAuth dosyası ve canlı hesap/auth smoke testi henüz yapılmadı.

## Important Decisions
- Script yalnızca YouTube Music playlistlerini oluşturur ve düzenler; telefona indirme resmi YouTube Music uygulamasında yapılır.
- Akış: sanatçı ekleme → albüm/single toplama → sıralama ve filtreleme → RAW playlist → manuel eleme → telefona indirme.
- RAW playlistler müzik keşfi için değil, hızlı manuel eleme için hazırlanır.
- Sıralama: sanatçı alfabetik, albüm eskiden yeniye, parça albümdeki orijinal sıra.
- Türler gereksiz şekilde bölünmez; yaklaşık 500–600 parçayı aşan listeler bölünür.
- İlk sürümde filtreleme deterministik ve isteğe bağlı olur; live, remix, karaoke gibi sürümler başlık kurallarıyla filtrelenebilir.
- Duplicate temizliğinin varsayılan seviyesi exact `videoId` eşleşmesidir; farklı sürümler için canonical eşleştirme yapılmaz.
- Çekirdek katalog işleme mantığı dış API’den bağımsız tutulur ve ağsız unit testlerle doğrulanır.
- State dosyası güvenli yazım için geçici dosya üzerinden atomik olarak güncellenir.
- Planlanan teknoloji Python ve `ytmusicapi`dir.

---

## History

### 2026-08-17T11:45+03:00

#### Task
Windows launcher'ın proje içindeki sanal ortamı kullanmasını sağlamak.

#### Summary
`run.bat`, UTF-8 kod sayfasını ve Python UTF-8 modunu ayarlayıp `.venv\Scripts\python.exe` varsa onu kullanacak şekilde güncellendi; böylece çift tıklamayla açılan TUI Türkçe menüyü doğru gösteriyor ve kurulan bağımlılıkları buluyor. Komut satırı kullanım örnekleri de sanal ortam Python'una göre güncellendi.

#### Affected Files
- `run.bat`
- `README.md`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions
- Sistem Python'unu değiştirmek yerine proje içi `.venv` kullanılmaya devam ediyor.
- Paket sürümü bu düzeltme commit'i ile `0.0.8` olarak hizalandı.

#### Notes
- Verification: `.venv\Scripts\python.exe` mevcut ve `ytmusicapi 1.12.2`/`PyYAML 6.0.3` kurulu.

### 2026-08-17T11:43+03:00

#### Task
İlk canlı deneme öncesi yerel Python ortamını ve config dosyasını hazırlamak.

#### Summary
Proje içinde `.venv` oluşturuldu ve `requirements.txt` kuruldu. Kurulu sürümler `ytmusicapi 1.12.2` ve `PyYAML 6.0.3`. `config.example.yaml` temel alınarak Git dışında tutulacak `config.yaml` oluşturuldu. OAuth dosyası oluşturulmadı.

#### Affected Files
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`
- Git dışı `config.yaml`
- Git dışı `.venv/`

#### Decisions
- Bağımlılıklar sistem Python'una değil, proje içindeki `.venv` ortamına kuruldu.
- Yerel config ve auth verileri Git'e alınmayacak.
- Paket sürümü bu hazırlık commit'i ile `0.0.7` olarak hizalandı.

#### Notes
- Verification: `.venv` içinden `ytmusicapi 1.12.2`, `PyYAML 6.0.3` import edildi.
- Verification: `config.yaml` başarıyla yüklendi; `max_tracks=550` ve `auth/oauth.json` yolu doğrulandı.

### 2026-08-17T11:04+03:00

#### Task
CLI komutunu her seferinde yazma ihtiyacını azaltacak küçük bir terminal menüsü eklemek.

#### Summary
`--tui` seçeneği ve Windows'ta çift tıklanabilir `run.bat` giriş noktası eklendi. Menü dry-run planını gösterme, playlist oluşturma/güncelleme ve çıkış seçeneklerini sunuyor. Harici TUI kütüphanesi eklenmedi; standart input/output ile çalışıyor.

#### Affected Files
- `src/playlist_builder/tui.py`
- `src/playlist_builder/cli.py`
- `src/playlist_builder/__init__.py`
- `build_playlists.py`
- `run.bat`
- `tests/test_tui.py`
- `README.md`
- `WALKTHROUGH.md`

#### Decisions
- Mevcut doğrudan CLI davranışı korunuyor; TUI ayrı olarak `--tui` ile açılıyor.
- Menü test edilebilirlik için çalıştırma fonksiyonunu dependency injection ile alıyor; testler ağ çağrısı yapmıyor.
- Paket sürümü bu commit ile `0.0.6` olarak hizalandı.

#### Notes
- Verification: `python -m pytest --basetemp=work/pytest-tmp` → `27 passed`.
- Verification: `python build_playlists.py --help` içinde `--tui` görünüyor.

### 2026-08-17T02:17+03:00

#### Task
RAW playlist oluşturma/güncelleme akışını ve kullanılabilir minimal CLI'yi tamamlamak.

#### Summary
Playlist writer; mevcut playlist'i başlıkla buluyor, yoksa oluşturuyor, varsa yalnızca yeni video ID'lerini ekliyor. Önceki state'te üretilmiş olup YouTube Music'te manuel silinen parçalar `removed_video_ids` içinde tutuluyor ve tekrar eklenmiyor. Tür başına 550 parçalık chunk'lar için `GENRE - RAW` ve gerektiğinde numaralı playlist adları kullanılıyor. `build_playlists.py` üzerinden config, artist listeleri, katalog işleme, playlist güncelleme, state ve JSONL log akışı bağlandı.

#### Affected Files
- `src/playlist_builder/ytmusic.py`
- `src/playlist_builder/playlists.py`
- `src/playlist_builder/cli.py`
- `src/playlist_builder/__init__.py`
- `build_playlists.py`
- `tests/test_playlists.py`
- `README.md`
- `WALKTHROUGH.md`

#### Decisions
- Playlist yazma için `ytmusicapi`nin `get_library_playlists`, `get_playlist`, `create_playlist` ve `add_playlist_items` çağrıları adaptörün arkasında tutuluyor.
- Reconcile/silme/move davranışı eklenmedi; manuel eleme append-only state ile korunuyor.
- CLI yalnızca gerekli `--config` ve `--dry-run` seçeneklerini sunuyor; tekrar çalıştırma zaten idempotent/append-only akışla yapılabiliyor.
- Paket sürümü bu commit ile `0.0.5` olarak hizalandı.

#### Notes
- Verification: `python -m pytest --basetemp=work/pytest-tmp` → `25 passed`.
- Verification: `python build_playlists.py --help` başarılı.
- Canlı çağrı denemesi yapılmadı; mevcut çalışma ortamında `ytmusicapi` kurulu değil ve auth dosyası yok. Kontrollü hata mesajı doğrulandı.

### 2026-08-17T02:10+03:00

#### Task
`ytmusicapi` için küçük bir API sınırı ve sanatçı katalog toplama katmanı eklemek.

#### Summary
Sanatçı adını exact eşleşmeyle kanal ID'sine çözümleyen, sanatçının albüm ve single bölümlerinden tam release listesini alan ve albüm parçalarını `Track` modeline dönüştüren adaptör eklendi. `ytmusicapi` importu canlı erişim kurulana kadar erteleniyor; unit testler sahte istemciyle ağsız çalışıyor.

#### Affected Files
- `src/playlist_builder/ytmusic.py`
- `src/playlist_builder/catalog.py`
- `src/playlist_builder/__init__.py`
- `state/.gitkeep`
- `tests/test_ytmusic.py`
- `tests/test_catalog.py`
- `WALKTHROUGH.md`

#### Decisions
- Yanlış sanatçı seçme riskini azaltmak için yalnızca exact normalize edilmiş isim eşleşmesi kabul ediliyor; sıfır veya birden fazla eşleşme hata veriyor.
- Albüm ve single release'leri `get_artist_albums(..., limit=None)` ile alınmaya çalışılıyor; release ID'leri tekrardan arındırılıyor.
- Albüm içindeki API parça sırası korunuyor; global sıralama sonraki processing katmanında uygulanıyor.
- Paket sürümü bu commit ile `0.0.4` olarak hizalandı.

#### Notes
- Verification: `python -m pytest --basetemp=work/pytest-tmp` → `22 passed`.
- Canlı YouTube Music çağrısı ve `ytmusicapi` kurulumu bu adımda yapılmadı.

### 2026-08-17T02:02+03:00

#### Task
Yerel yapılandırma, sanatçı listeleri, state ve olay logu altyapısını eklemek.

#### Summary
YAML config yükleme ve doğrulama, tür dosyalarından sanatçı okuma, JSON build state kaydetme/yükleme ve JSONL event log yazma eklendi. Config dışındaki yerel `config.yaml` Git dışında bırakıldı. Testler sandbox’a uygun proje içi geçici dizinle çalıştırıldı.

#### Affected Files
- `.gitignore`
- `config.example.yaml`
- `src/playlist_builder/artists.py`
- `src/playlist_builder/config.py`
- `src/playlist_builder/state.py`
- `src/playlist_builder/events.py`
- `tests/test_artists.py`
- `tests/test_config.py`
- `tests/test_state.py`
- `tests/test_events.py`
- `WALKTHROUGH.md`

#### Decisions
- Sadece `append_only` update mode destekleniyor; reconcile davranışı ilk sürüme alınmadı.
- Config yolları config dosyasının bulunduğu dizine göre çözümleniyor.
- State dosyası eksikse boş state ile başlanıyor; bozuk state sessizce sıfırlanmıyor.

#### Notes
- Verification: `python -m pytest --basetemp=work/pytest-tmp` → `18 passed`.
- Gerçek YouTube Music çağrısı henüz yapılmadı.

### 2026-08-17T01:58+03:00

#### Task
İlk kod sürümünü, saf katalog işleme mantığıyla başlatmak.

#### Summary
`Track` ve filtre config modelleri ile sanatçı/albüm/parça sıralama, başlık/albüm bazlı isteğe bağlı filtreleme, exact `videoId` duplicate temizliği ve max parça sayısına göre bölme fonksiyonları eklendi. Ağsız pytest kapsamı 7 test ve tamamı başarılı.

#### Affected Files
- `pyproject.toml`
- `src/playlist_builder/__init__.py`
- `src/playlist_builder/models.py`
- `src/playlist_builder/processing.py`
- `tests/test_processing.py`
- `WALKTHROUGH.md`

#### Decisions
- İlk implementasyon sürümü `v0.0.2` olarak belirlendi; mevcut iskelet `v0.0.1` başlangıcıdır.
- Track sırası; sanatçı, release tarihi/yılı, albüm ve track number üzerinden deterministik üretilir.
- Track number yoksa albümden gelen giriş sırası korunur.

#### Notes
- Verification: `python -m pytest` → `7 passed`.
- Henüz gerçek YouTube Music isteği yapılmadı.

### 2026-08-17T01:41+03:00

#### Task
Proje altyapısını, Git deposunu ve başlangıç dosya yapısını hazırlamak.

#### Summary
Python/ytmusicapi tabanlı MVP için klasör yapısı, örnek config, bağımlılık listesi, README ve Git ignore kuralları oluşturuldu. Git deposu `main` dalında başlatıldı ve initial commit yapıldı.

#### Affected Files
- `.gitignore`
- `README.md`
- `config.example.yaml`
- `requirements.txt`
- `artists/*.txt`
- `src/.gitkeep`
- `tests/.gitkeep`
- `state/.gitkeep`
- `cache/.gitkeep`
- `logs/.gitkeep`
- `docs/.gitkeep`
- `.git/`

#### Decisions
- Proje yerel çalışan bir CLI uygulaması olarak başlayacak; sunucu ve veritabanı kullanılmayacak.
- Sonraki güncellemelerde `append_only` yaklaşımı kullanılacak.
- Auth, state, cache, log ve Codex çalışma dosyaları Git dışında tutulacak.

#### Notes
- Initial commit: `10f66d7 chore: initialize playlist builder project`
- Uygulama kodu ve testler henüz yazılmadı.

### 2026-08-17T01:26+03:00

#### Task
Projenin kapsamını netleştirip kalıcı proje geçmişini başlatmak.

#### Summary
Proje, yalnızca sanatçı kataloglarından düzenli RAW YouTube Music playlistleri üreten sade bir otomasyon olarak tanımlandı. Manuel eleme ve telefon üzerinden playlist indirme otomasyonun dışında bırakıldı.

#### Affected Files
- `WALKTHROUGH.md`

#### Decisions
- Otomatik final playlist üretimi ve telefona otomatik indirme ilk sürüme dahil edilmeyecek.
- Mevcut hedef, hızlı ve düzenli RAW playlist üretimidir.

#### Notes
- Workspace’te henüz uygulama kodu bulunmuyor.
- Sonraki adım, sade MVP için dosya yapısını ve kabul kriterlerini kesinleştirmek.

### 2026-08-17T11:55+03:00

#### Task
OAuth kimlik doğrulamasını ve TUI üzerinden tek seferlik kurulum akışını eklemek.

#### Summary
Google OAuth client JSON dosyasından istemci bilgilerini okuyup `ytmusicapi` OAuth device flow ile yerel token oluşturma desteği eklendi. TUI'a OAuth kurulumu seçeneği, CLI'a `--setup-oauth` seçeneği eklendi. Playlist erişiminde OAuth credentials artık `YTMusic` istemcisine aktarılıyor.

#### Affected Files
- `src/playlist_builder/auth.py`
- `src/playlist_builder/config.py`
- `src/playlist_builder/ytmusic.py`
- `src/playlist_builder/cli.py`
- `src/playlist_builder/tui.py`
- `config.example.yaml`
- `README.md`
- `tests/test_auth.py`
- `tests/test_config.py`
- `tests/test_tui.py`
- `tests/test_ytmusic.py`
- Git dışı yerel `config.yaml`

#### Decisions
- OAuth client dosyası `auth/client_secret.json`, ytmusicapi token dosyası `auth/oauth.json` olarak tutulacak; `auth/` Git dışında kalacak.
- OAuth credentials verilmezse mevcut auth-file-only adapter davranışı korunacak.
- Paket sürümü bu commit ile `0.0.9` olarak hizalanacak.

#### Notes
- Verification: `.venv` içinden `pytest` → `31 passed`.
- Verification: `compileall`, CLI help ve Windows launcher TUI çıkışı başarılı.
- Canlı OAuth akışı henüz çalıştırılmadı; `auth/client_secret.json` henüz kullanıcı tarafından eklenmedi.

### 2026-08-19T02:54+03:00

#### Task
OAuth kurulumu sırasında YouTube TLS bağlantısında oluşan `INVALID_SESSION_ID` hatasını gidermek.

#### Summary
Teşhis sırasında Python/requests ve Windows curl bağlantılarının YouTube TLS handshake aşamasında başarısız olduğu, aynı YouTube endpoint'inin TLS 1.2 ile başarılı HTTP yanıtı verdiği görüldü. OAuth kurulumu ve YouTube Music istemcisi için sertifika doğrulamasını koruyan TLS 1.2 requests session eklendi.

#### Affected Files
- `src/playlist_builder/network.py`
- `src/playlist_builder/auth.py`
- `src/playlist_builder/ytmusic.py`
- `src/playlist_builder/__init__.py`
- `tests/test_network.py`
- `tests/test_auth.py`
- `tests/test_ytmusic.py`
- `WALKTHROUGH.md`

#### Decisions
- TLS doğrulaması kapatılmayacak; yalnızca bu ortamda sorun çıkaran TLS 1.3 yerine TLS 1.2 zorlanacak.
- Paket sürümü bu düzeltme commit'i ile `0.0.10` olarak hizalanacak.

#### Notes
- Root-cause evidence: YouTube endpoint default TLS bağlantısında `INVALID_SESSION_ID`, TLS 1.2 ile `404` (TLS handshake başarılı) döndü; `404`, GET ile yanlış HTTP metodu kullanıldığı için beklenen yanıt.
- OAuth token akışı kullanıcı tarafından henüz yeniden denenmedi.

### 2026-08-19T03:04+03:00

#### Task
TLS 1.2 düzeltmesinden sonra devam eden OAuth device-code zaman aşımını çözmek.

#### Summary
`ytmusicapi 1.12.2` içindeki eski `https://www.youtube.com/o/oauth2/device/code` endpoint'inin POST isteği zaman aşımına uğrarken güncel Google `https://oauth2.googleapis.com/device/code` endpoint'inin hızlı ve geçerli bir yanıt verdiği doğrulandı. OAuth kurulumu, ytmusicapi'nin OAuth sınıflarını koruyarak güncel device-code ve token sözleşmesini kullanacak şekilde uyarlandı.

#### Affected Files
- `src/playlist_builder/auth.py`
- `src/playlist_builder/__init__.py`
- `tests/test_auth.py`
- `WALKTHROUGH.md`

#### Decisions
- TLS sertifika doğrulaması korunacak ve mevcut TLS 1.2 session kullanılmaya devam edecek.
- Device-code isteği güncel Google endpoint'ine, token isteği `device_code` ve `urn:ietf:params:oauth:grant-type:device_code` parametrelerine geçirilecek.
- Paket sürümü bu düzeltme commit'i ile `0.0.11` olarak hizalanacak.

#### Notes
- `auth/client_secret.json` dosyası yapısal olarak geçerli; hata OAuth client JSON dosyasından kaynaklanmıyor.
- Verification: `pytest` → `33 passed`; `compileall` başarılı; gerçek tarayıcı OAuth akışı kullanıcı tarafından henüz yeniden denenmedi.

### 2026-08-19T03:24+03:00

#### Task
Terminal menüsünü işlevsel ve tekrar kullanılabilir bir Textual arayüzüne dönüştürmek.

#### Summary
Eski input tabanlı menü yerine Windows Terminal uyumlu Textual uygulaması eklendi. Ana ekran OAuth durumunu, playlist ayarlarını ve kategori başına sanatçı sayılarını gösteriyor. Dry-run ve gerçek playlist işlemleri Textual worker içinde çalışıyor; işlem ilerlemesi canlı çıktı paneline aktarılıyor. Bloklayan OAuth device flow, arayüz kapatılarak mevcut terminal akışıyla çalıştırılıyor ve sonrasında arayüz yeniden açılıyor.

#### Affected Files
- `src/playlist_builder/tui.py`
- `src/playlist_builder/cli.py`
- `requirements.txt`
- `tests/test_tui.py`
- `README.md`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions
- Core playlist ve API akışı korunacak; Textual yalnızca sunum katmanı olacak.
- İlk iterasyonda sanatçı listeleri dosyalardan okunmaya devam edecek; arayüzde sanatçı düzenleme ayrı bir sonraki iterasyon konusu.
- TUI çalışırken gerçek playlist yazma işlemi başlamadan önce mevcut akış korunacak; OAuth terminal girdisi Textual içine gömülmeyecek.
- Paket sürümü bu iterasyon commit'i ile `0.0.12` olarak hizalanacak.

#### Notes
- Verification: `pytest` → `34 passed`; `compileall` başarılı; `pip check` bağımlılık sorunu bildirmedi.
- Textual `8.2.8` sanal ortamda çalıştırılarak doğrulandı.

### 2026-08-19T03:46+03:00

#### Task
Textual TUI'nin gerçek terminal ölçülerindeki görsel yerleşim sorunlarını düzeltmek.

#### Summary
PTY ve Textual `run_test` ölçümleriyle küçük ve orta terminal boyutları kontrol edildi. Sol paneldeki düğmelerin ekran dışına sessizce taşması, kategori/çıktı panellerinin footer'a taşması ve gereksiz varsayılan arayüz öğeleri giderildi. Dar terminaller için sol panel kaydırılabilir hale getirildi; ana içerik panelleri footer sınırları içinde tutuldu.

#### Affected Files
- `src/playlist_builder/tui.py`
- `tests/test_tui.py`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions
- Kategori tablosu sabit ve kompakt yükseklikte tutulacak; çıktı paneli kalan alanı kullanacak.
- Dar terminalde kontroller gizlenmeyecek; sol panel `VerticalScroll` ile erişilebilir kalacak.
- OAuth akışına ve playlist çekirdeğine dokunulmayacak; bu iterasyon yalnızca TUI sunum katmanını kapsayacak.
- Paket sürümü bu iterasyon commit'i ile `0.0.13` olarak hizalanacak.

#### Notes
- Evidence: TUI `80x24`, `100x30`, `120x35` ve `160x40` boyutlarında ölçüldü; ana paneller footer'a taşmadı. `120x35` ölçüsünde `Yenile` ve `Çıkış` görünür; `80x24` ölçüsünde sol panel kaydırılabilir.
- `palette` kısayolu ve Header'daki varsayılan daire simgesi kaldırıldı; buton metinleri dar genişliklere sığacak şekilde kısaltıldı.
- Verification: `pytest` → `35 passed`; `compileall`, `pip check`, CLI help, `git diff --check` ve gerçek PTY TUI smoke testi başarılı.
- OAuth akışı bu iterasyonda çalıştırılmadı ve OAuth dosyaları değiştirilmedi.

### 2026-08-19T04:16+03:00

#### Task
Sanatçı listelerini dosya düzenlemeden TUI içinden yönetebilmek.

#### Summary
Kategori seçimi ile doğru `artists/<kategori>.txt` dosyasını hedefleyen bir modal sanatçı editörü eklendi. Sanatçılar TUI içinde eklenebiliyor, düzenlenebiliyor ve silinebiliyor; değişiklikler açıkça kaydedilene kadar bellekte tutuluyor. Ana ekrana dönüldüğünde kategori sayıları yenileniyor ve mevcut dry-run/build akışı kullanılmaya devam ediyor.

#### Affected Files
- `src/playlist_builder/artists.py`
- `src/playlist_builder/tui.py`
- `tests/test_artists.py`
- `tests/test_tui.py`
- `README.md`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions
- İç kategori anahtarı dosya adının uzantısız hali; dosya hedefi `config.artists_dir` altında bu anahtarla eşleştirilecek.
- Görünen kategori etiketi ayrı tutulacak; örneğin `hip_hop_rap` için ekran ve playlist adı `HIP-HOP / RAP` olacak.
- `artists/*.txt` kaynak gerçekliği olmaya devam edecek; TUI değişiklikleri ekle/düzenle/sil sonrası `Kaydet` ile diske yazacak.
- Kaydedilmemiş değişiklik varken yeniden yükleme veya editörden çıkış engellenecek.
- OAuth ve playlist çekirdeği değiştirilmedi; sürüm `0.0.14` olarak hizalandı.

#### Notes
- Kanıt: `hip_hop_rap` seçimi `artists\\hip_hop_rap.txt` dosyasını gösteriyor; playlist adı mevcut `HIP-HOP / RAP - RAW` kuralıyla korunuyor.
- Editör düzeni `80x24`, `100x30` ve `120x35` terminal ölçülerinde ölçüldü; düğmeler ekran dışına taşmıyor.
- Verification: `pytest` → `40 passed`; `compileall`, `pip check`, CLI help, `git diff --check` ve PTY smoke testi başarılı.

### 2026-08-19T04:38+03:00

#### Task
Hardcoded tür yapısını kaldırıp playlistleri kullanıcı tarafından dosya adı üzerinden yönetilebilir hale getirmek.

#### Summary
`artists/*.txt` dosyaları artık yalnızca sanatçı listesi değil, playlist tanımı olarak kullanılıyor. Dosyanın uzantısız adı YouTube Music playlist adı olarak doğrudan kullanılıyor; örneğin `METAL - RAW.txt` → `METAL - RAW`. Otomatik genre etiketi ve otomatik `- RAW` eki kaldırıldı. Playlist dosyaları TUI içinden oluşturulabiliyor, yeniden adlandırılabiliyor ve onayla silinebiliyor.

#### Affected Files
- `src/playlist_builder/artists.py`
- `src/playlist_builder/playlists.py`
- `src/playlist_builder/tui.py`
- `tests/test_artists.py`
- `tests/test_playlists.py`
- `tests/test_tui.py`
- `README.md`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions
- Playlist/kategori listesi koddan değil, `config.artists_dir` altındaki tüm `.txt` dosyalarından okunacak.
- Playlist dosyası oluşturma, yeniden adlandırma ve silme backend fonksiyonlarıyla doğrulanacak; dosya adlarında Windows'un geçersiz karakterleri reddedilecek.
- TUI kısayolları: `N` yeni playlist, `M` ad değiştir, `P` playlist dosyasını sil; mevcut `A/E/X/S/R/Esc` sanatçı ve dosya işlemleri korunacak.
- Artist değişiklikleri `Kaydet` ile yazılmaya devam edecek; playlist dosyası işlemleri doğrudan uygulanacak ve silme öncesi onay alınacak.
- Yerel dosyayı silmek veya yeniden adlandırmak YouTube Music'teki mevcut playlisti otomatik silmez/yeniden adlandırmaz; bu, manuel eleme verisini korumak için bilinçli bir sınırdır.
- OAuth akışı değiştirilmedi; sürüm `0.0.15` olarak hizalandı.

#### Notes
- Verification: `pytest` → `43 passed`; `compileall`, `pip check`, CLI help, `git diff --check` ve gerçek PTY TUI smoke testi başarılı.

### 2026-08-19T10:26+03:00

#### Task
TUI footer kısayollarını sadeleştirmek ve native command palette eklemek.

#### Summary
Textual’ın native command palette’i etkinleştirildi. Ana footer artık `D` plan, `B` oluştur/güncelle, `A` playlistler, `R` yenile, `Q` çıkış ve `Ctrl+P` komutlarını gösteriyor. Uygulamanın dry-run, build, playlist düzenleme ve yenileme aksiyonları palette içinde aranabilir hale getirildi.

#### Affected Files
- `src/playlist_builder/tui.py`
- `tests/test_tui.py`
- `README.md`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions
- Özel bir palette yazılmadı; Textual’ın native palette’i ve `get_system_commands` genişletmesi kullanıldı.
- `Ctrl+P` binding’i normal footer binding listesine tekrar eklenmeden, Textual’ın palette alanında tek kez gösterilecek şekilde tanımlandı.
- OAuth ve playlist oluşturma çekirdeği değiştirilmedi.
- Editör modalı açıkken ana ekran aksiyonları palette’e eklenmiyor; mevcut editör kısayolları korunuyor.

#### Notes
- Verification: `pytest` → `44 passed`; `compileall`, `pip check`, CLI help ve `git diff --check` başarılı.
- Gerçek PTY smoke testinde footer taşmadan render edildi; `Ctrl+P` palette’i açıldı ve uygulama aksiyonları listelendi.
- Sürüm `0.0.16` olarak hizalandı.
- Mevcut eski dosyalar (`metal.txt` gibi) yeni adlandırma kuralıyla `metal` playlist kimliğine karşılık gelir. Eski YouTube playlistleri otomatik migrate veya delete edilmez.

### 2026-08-19T10:44+03:00

#### Task
TUI butonlarını küçültmek ve panelleri klavye ile yeniden boyutlandırabilmek.

#### Summary
Tüm TUI butonları tek satırlık kompakt görünüme alındı. Sanatçı editöründeki aksiyon butonları artık içerik genişliğini kullanıyor. Ana ekrandaki sol panel ve editördeki playlist paneli `Ctrl+Left` / `Ctrl+Right` ile daraltılıp genişletilebiliyor; `Ctrl+0` varsayılan genişliğe döndürüyor.

#### Affected Files
- `src/playlist_builder/tui.py`
- `tests/test_tui.py`
- `README.md`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions
- Buton boyutu ve panel genişliği ayarları yalnızca mevcut oturumda tutuluyor; config'e kalıcı UI ayarı eklenmedi.
- Ana panel genişliği `22–44`, editör playlist paneli `24–50` sütun aralığında ve adım `2` olarak belirlendi.
- Native `Ctrl+P` command palette'e ana ekran ve editör panel boyutu komutları eklendi.
- OAuth akışı ve playlist oluşturma çekirdeği değiştirilmedi.

#### Notes
- Verification: `pytest` → `46 passed`; `compileall`, `pip check`, CLI help ve `git diff --check` başarılı.
- Gerçek PTY smoke testinde ana ekran ve editör render edildi; editörde panel genişletme ve durum mesajı kontrol edildi.
- Sürüm `0.0.17` olarak hizalandı.

### 2026-08-19T23:40+03:00

#### Task
Windows terminalinde mouse takılmasını azaltmak; TUI'de tıklama ve tekerlek desteğini korumak.

#### Summary
Textual'ın varsayılan Windows sürücüsü yerine proje içi bir sürücü bağlandı. Mouse hareketlerini sürekli raporlayan `?1003h` modu açılmıyor; yalnızca tıklama/tekerlek olayları için `?1000h` ve SGR koordinatları için `?1006h` kullanılıyor. Uygulama başlarken olası eski mouse modları, kapanırken de kullanılan modlar temizleniyor.

#### Affected Files
- `src/playlist_builder/textual_driver.py`
- `src/playlist_builder/tui.py`
- `tests/test_tui.py`
- `README.md`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions
- Sürükleme sırasında hareket takibi eklenmedi; bu TUI için gerekli değil ve olay yükünü yeniden artırır.
- OAuth ve playlist oluşturma çekirdeği değiştirilmedi.
- Windows dışı platformlarda Textual'ın kendi sürücüsü kullanılmaya devam ediyor.

#### Notes
- Verification: `pytest` → `47 passed`; `compileall`, `pip check` ve `git diff --check` başarılı.
- Gerçek PTY smoke testinde `?1003h` gönderilmedi; uygulama `q` ile temiz kapanıp mouse modlarını kapattı.
- Sürüm `0.0.18` olarak hizalandı.

### 2026-08-22T01:55+03:00

#### Task
Projeyi GitHub üzerinden yayınlamaya hazırlamak ve bilinçli artist listesi temizliğini kaydetmek.

#### Summary
Varsayılan altı artist playlist dosyası kaldırıldı; mevcut `artists/rock.txt` korundu. Yerel OAuth/config/state/cache/log dosyalarının GitHub'a gitmemesi için mevcut ignore kuralları doğrulandı. Kod sürümü `0.0.19` olarak hizalandı.

#### Affected Files
- `artists/ambient_classical.txt`
- `artists/electronic_drive.txt`
- `artists/electronic_focus.txt`
- `artists/hip_hop_rap.txt`
- `artists/jazz_soul_funk.txt`
- `artists/metal.txt`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions
- Altı dosyanın silinmesi bilinçli kabul edildi; `rock.txt` mevcut başlangıç listesi olarak kaldı.
- GitHub repository'si private tutulacak; OAuth credentials ve yerel çalışma verileri publish edilmeyecek.
- GitHub remote'u yerelde eklenmedi; publish işlemi uygulama üzerinden yapılacak.

#### Notes
- Verification: `pytest` → `47 passed`; `compileall`, `pip check` ve `git diff --check` başarılı.
- Takip edilen dosyalar arasında gerçek secret bulunmadı; `client_secret` referansları yalnızca örnek/kod/test içeriği.
- Sürüm `0.0.19` olarak hizalandı.

### 2026-08-22T02:49+03:00

#### Task
Sanatçı girdilerinde isim yanında YouTube kanal URL'si desteği eklemek.

#### Summary
Sanatçı listeleri artık düz isim, YouTube `@handle` veya `channel/<id>` URL'si ve `isim | URL` formatını kabul ediyor. `channel/<id>` girdileri sanatçı aramasını atlayarak doğrudan kanal kimliğini kullanıyor; `@handle` girdileri handle ile mevcut isim arama fallback'ine gidiyor. İsim ve URL birlikte verildiğinde URL kaynak olarak öncelikli, isim ise görünen etiket olarak tutuluyor.

#### Affected Files
- `src/playlist_builder/ytmusic.py`
- `src/playlist_builder/cli.py`
- `src/playlist_builder/tui.py`
- `tests/test_ytmusic.py`
- `README.md`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions
- Mevcut düz sanatçı adı formatı ve mevcut duplicate davranışı korundu; duplicate doğrulaması bu değişikliğin kapsamına alınmadı.
- URL girdileri yalnızca resmi YouTube/YouTube Music hostları ve `@handle` veya `channel/<id>` yolları için kabul ediliyor.
- OAuth ve playlist yazma akışı değiştirilmedi.

#### Notes
- Verification: `pytest` → `51 passed`; `git diff --check` başarılı.
- Sürüm `0.0.20` olarak hizalandı.

### 2026-08-22T03:38+03:00

#### Task
Sanatçı girdilerindeki duplicate çözümünü API kullanımını azaltacak ve build akışını koruyacak şekilde uygulamak.

#### Summary
Ham artist satırlarını ve satır numaralarını koruyan okuyucu eklendi. `--validate` ve TUI'deki `V` / command palette komutu, dosyaları ağ kullanmadan kontrol ediyor; duplicate satırlar otomatik silinmiyor. İsim, `@handle` ve `channel/<id>` girdileri için conservative canonical anahtarlar eklendi. Build aynı playlist içinde önce normalize edilmiş girdiyi, ardından çözümlenmiş `channel_id` değerini deduplicate ediyor. Aynı sanatçı farklı playlistlerde tutuluyor; katalog çağrısı build boyunca channel ID bazında bellekte cache'leniyor.

Çözümlenen artist alias'ları `state/build_state.json` içine `channel_id`, görünen ad ve `resolved_at` ile yazılıyor. `artist_cache_ttl_days` varsayılanı 30 gün; `0` kalıcı alias cache'ini kapatıyor. Eski state dosyalarında `state_version` yoksa geriye dönük yükleme korunuyor. Windows legacy konsollarında Türkçe doğrulama çıktısı için stdout/stderr UTF-8'e alınıyor.

#### Affected Files
- `src/playlist_builder/artists.py`
- `src/playlist_builder/validation.py`
- `src/playlist_builder/ytmusic.py`
- `src/playlist_builder/catalog.py`
- `src/playlist_builder/state.py`
- `src/playlist_builder/config.py`
- `src/playlist_builder/cli.py`
- `src/playlist_builder/tui.py`
- `config.example.yaml`
- `README.md`
- `tests/test_artists.py`
- `tests/test_validation.py`
- `tests/test_ytmusic.py`
- `tests/test_catalog.py`
- `tests/test_state.py`
- `tests/test_config.py`
- `tests/test_cli.py`
- `tests/test_tui.py`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions
- Aynı sanatçıyı global olarak playlistlerden silmek yerine deduplication playlist bazında tutuldu.
- Name-vs-URL semantic duplicate'ları ağsız validation aşamasında varsayılmadı; build sırasında channel ID ile kesinleştirildi.
- Alias cache süresiz güvenilir kabul edilmiyor; TTL ile sınırlandırılıyor.
- OAuth akışına dokunulmadı.

#### Notes
- Verification: `pytest` → `66 passed`; gerçek proje üzerinde `build_playlists.py --validate` → başarılı; kaynak AST parse → başarılı; `git diff --check` → başarılı.
- `compileall` doğrudan F: üzerindeki `__pycache__` izinleri nedeniyle kullanılmadı; test ve AST parse ile doğrulama yapıldı.
- Sürüm `0.0.21` olarak hizalanacak.

### 2026-08-22T04:12+03:00

Format ve uzak sanatçı doğrulaması iki ayrı akışa ayrıldı. Eski `--validate` CLI aliası kaldırıldı; yerine ağsız `--validate-format` ve API kullanan `--validate-remote` komutları geldi. Her iki akış da yalnızca kesin duplicate satırlarını güvenli değişiklik adayı olarak gösteriyor; geçersiz veya çözülemeyen girdiler otomatik değiştirilmiyor. TXT dosyaları kullanıcı onayı olmadan değiştirilmiyor. Onaylı değişiklikler yorumları, boş satırları, satır sırasını ve satır sonlarını koruyan satır-adresli atomic yazımla uygulanıyor. Uzak doğrulama artist çözümünü ve `get_artist` ile channel sayfası kontrolünü yapıyor; aynı playlist içindeki farklı isim/URL girdilerini çözülen `channel_id` üzerinden raporluyor. Build akışı validator çağırmıyor ve TXT dosyalarına yazmıyor. TUI'de `V` format, `U` uzak doğrulama; uzak akış native command palette üzerinden de erişilebilir.

#### Affected Files
- `src/playlist_builder/artists.py`
- `src/playlist_builder/validation.py`
- `src/playlist_builder/ytmusic.py`
- `src/playlist_builder/cli.py`
- `src/playlist_builder/tui.py`
- `tests/test_artists.py`
- `tests/test_validation.py`
- `tests/test_ytmusic.py`
- `tests/test_cli.py`
- `tests/test_tui.py`
- `README.md`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions
- Eski `--validate` aliası korunmadı; kullanıcı iki doğrulama türünü komut adından açıkça seçiyor.
- Otomatik düzeltme kapsamı yalnızca ilk occurrence korunarak duplicate satırının kaldırılmasıyla sınırlı.
- Uzak doğrulama kalıcı alias/state kaydetmiyor; yalnızca onaylı TXT düzeltmesini uyguluyor.
- Build sırasında mevcut API cache/deduplication davranışı korunuyor.

#### Notes
- Verification: `pytest` → `74 passed`; `git diff --check` → başarılı.
- Sürüm `0.0.22`.

### 2026-08-22T04:15+03:00

Onay penceresi ile uygulama arasında artist dosyası değişirse, satırın eski değeri doğrulanmadan yazma yapılmıyor; böylece eski bir planın yeni içeriği yanlışlıkla silmesi engelleniyor.

#### Notes
- Son güvenlik değişikliğinden sonra `pytest` → `74 passed`; kaynak AST parse → `29` dosya; gerçek proje `--validate-format` → başarılı.

### 2026-08-22T04:44+03:00

#### Task

Playlistlerdeki otomatik 550 parça sınırını kaldırmak ve validator cache davranışını netleştirmek.

#### Summary

`playlist.max_tracks` config alanı kaldırıldı. Build artık filtreleme, sıralama ve video ID duplicate ayıklamasından sonra parçaları tek playlist listesi olarak işler; 550 sınırına göre `1`, `2` şeklinde otomatik bölmez. Mevcut append-only playlist güncelleme davranışı korundu. TUI'deki limit göstergesi `yok` olarak güncellendi.

Validatorlar için kalıcı cache/state yazımı olmadığını testlerle güvence altına alan kontroller eklendi. Format validator ağ kullanmıyor; remote validator API kullanıyor ancak varsa çözümleme cache'i yalnızca komut süresince bellekte kalıyor.

#### Affected Files

- `src/playlist_builder/config.py`
- `src/playlist_builder/processing.py`
- `src/playlist_builder/cli.py`
- `src/playlist_builder/tui.py`
- `config.example.yaml`
- `README.md`
- `tests/test_processing.py`
- `tests/test_config.py`
- `tests/test_cli.py`
- `tests/test_tui.py`
- `src/playlist_builder/__init__.py`
- `WALKTHROUGH.md`

#### Decisions

- Her `.txt` dosyası tek playlist hedefler; build parça sayısına göre playlist bölmez.
- Eski yerel config dosyasındaki `playlist.max_tracks` anahtarı artık okunmuyor ve etkisizdir; manuel olarak silinebilir.
- Validatorlar `state/build_state.json` veya `cache/` içine kalıcı veri yazmaz.

#### Notes

- Verification: proje `.venv` ile `pytest` → başarılı; 550 üzeri parça için tek chunk davranışı ayrıca test edildi.
- Sürüm `0.0.23` olarak hizalandı.

### 2026-08-22T05:04+03:00

#### Task

v0.0.23 kodunun büyük gerçek build öncesi bağımsız kalite incelemesi ve filtreleme kapsamının sadeleştirilmesi.

#### Summary

gpt-5.6-sol / xhigh reasoning kullanan read-only subagent incelemesi, testlerin geçmesinden bağımsız olarak düzeltilmesi gereken iki P1 ve üç P2 bulgu raporladı. P1 bulgular artist cache TTL'inin legacy `artist_ids` fallback'iyle aşılması ve başarısız playlist eklemesinin state'i başarı gibi güncelleyebilmesi. P2 bulgular filtre false-positive'leri, TUI kaydında yorum/boş satır kaybı ve state'teki silinmiş playlist ID'sinin build'i kilitlemesi.

#### Decisions

- `live`, `remix`, `remaster`, `deluxe` ve `karaoke` otomatik filtreleri kaldırılacak.
- Build tüm albüm/single parçalarını çekecek; manuel eleme YouTube Music üzerinde yapılacak.
- Filtre kaldırma bir sonraki kod değişikliğinde processing, config, TUI, test ve README'den birlikte temizlenecek.
- P1/P2 bulgular gerçek büyük build'den önce ayrı düzeltme adımları olarak ele alınacak.

#### Follow-ups

- Artist cache TTL ve legacy `artist_ids` migration/fallback davranışını düzelt.
- Playlist yazma response/state güncellemesini başarısız ve kısmi sonuçlara karşı güvenli hale getir.
- TUI artist dosyası kaydında yorumları, boş satırları ve satır biçimini koru; atomic yaz.
- Silinmiş playlist ID'leri için güvenli recovery ekle.

#### Notes

- Bu kayıt turunda kaynak kod değiştirilmedi; mevcut v0.0.23 build'inde filtreler hâlâ config'e göre çalışıyor.

### 2026-08-22T05:15+03:00

#### Task

Otomatik live/remix/remaster/deluxe/karaoke filtrelerini kaldırmak.

#### Summary

Build artık katalogdan gelen tüm albüm ve single parçalarını işler. İçerik adına göre hiçbir parça elenmez; parçalar yalnızca mevcut sanatçı-albüm-track sıralama mantığıyla sıralanır ve aynı `video_id` duplicate'leri ayıklanır. Manuel eleme YouTube Music'e bırakılır.

`FilterConfig`, filtre parser'ı ve processing filtresi kaldırıldı. CLI, TUI, örnek config ve README yeni davranışa göre güncellendi. Eski config dosyalarındaki `filters:` bölümü geriye dönük olarak yok sayılır; yeni örnek ve yerel configte bu bölüm bulunmaz.

#### Affected Files

- `src/playlist_builder/models.py`
- `src/playlist_builder/config.py`
- `src/playlist_builder/processing.py`
- `src/playlist_builder/cli.py`
- `src/playlist_builder/tui.py`
- `src/playlist_builder/__init__.py`
- `config.example.yaml`
- `README.md`
- `tests/test_processing.py`
- `tests/test_config.py`
- `tests/test_tui.py`

#### Decisions

- Otomatik sürüm filtreleri tamamen kaldırıldı; filtre ayarı için yeni bir config alanı yok.
- `prepare_tracks` tüm release varyantlarını korur ve yalnızca video ID bazlı duplicate ayıklar.
- TUI durum paneli `Otomatik filtre: yok` gösterir.
- 550 parça limiti kaldırıldığı için mevcut tek playlist davranışı korunur.

#### Notes

- Verification: hedefli testler → `24 passed`; tam `pytest` → `70 passed`; `compileall` → başarılı; `git diff --check` → başarılı.
- Sürüm `0.0.24` olarak hizalandı.

### 2026-08-22T10:33+03:00

#### Task

Önceki kalite incelemesindeki artist cache TTL bulgusunu düzeltmek.

#### Summary

Build artık yalnızca TTL kontrollü `artist_aliases` kayıtlarını kullanıyor. Timestamp taşımayan legacy `artist_ids` mapping'i runtime artist çözümlemesinde fallback olarak kullanılmıyor ve yeni buildlerde güncellenmiyor. Legacy alan state dosyalarında geriye dönük yükleme için korunuyor; eski kayıtlar gerektiğinde API üzerinden yeniden çözülüp timestamp'li alias olarak kaydediliyor.

#### Affected Files

- `src/playlist_builder/cli.py`
- `src/playlist_builder/__init__.py`
- `tests/test_cli.py`

#### Decisions

- `artist_cache_ttl_days: 0` artık hiçbir kalıcı alias yolunu bypass edemez.
- Legacy `artist_ids` verisi silinmedi; fakat güvenilirliği kanıtlanamadığı için yalnızca migration/round-trip uyumluluğu kapsamında tutuldu.

#### Notes

- Verification: `tests/test_cli.py tests/test_state.py` → `11 passed`.
- Sürüm `0.0.25` olarak hizalandı.
