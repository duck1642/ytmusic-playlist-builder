# WALKTHROUGH.md

## Project
YouTube Music için tür bazlı RAW playlistler oluşturan bir otomasyon sistemi. Amaç, sanatçıların albüm ve single kataloglarını hızlıca playlistlere eklemek ve sonrasında YouTube Music içinde manuel eleme yaparak telefona indirmektir.

## Current State
Yerel config, sanatçı listesi okuma, JSON state ve JSONL event log katmanları hazır. Çekirdek katalog işleme ile birlikte ağsız test kapsamı 18 teste ulaştı. `ytmusicapi` adapter’ı, playlist yazma ve CLI henüz eklenmedi.

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
