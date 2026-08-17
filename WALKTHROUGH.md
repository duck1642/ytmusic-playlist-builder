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
