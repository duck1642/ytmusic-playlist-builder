# WALKTHROUGH.md

## Project
YouTube Music için tür bazlı RAW playlistler oluşturan bir otomasyon sistemi. Amaç, sanatçıların albüm ve single kataloglarını hızlıca playlistlere eklemek ve sonrasında YouTube Music içinde manuel eleme yaparak telefona indirmektir.

## Current State
Uygulama kodu henüz oluşturulmadı. MVP iskeleti, Git deposu ve ilk commit hazır; ilk sürüm yalnızca playlist oluşturma ve organize etme işine odaklanacak.

## Important Decisions
- Script yalnızca YouTube Music playlistlerini oluşturur ve düzenler; telefona indirme resmi YouTube Music uygulamasında yapılır.
- Akış: sanatçı ekleme → albüm/single toplama → sıralama ve filtreleme → RAW playlist → manuel eleme → telefona indirme.
- RAW playlistler müzik keşfi için değil, hızlı manuel eleme için hazırlanır.
- Sıralama: sanatçı alfabetik, albüm eskiden yeniye, parça albümdeki orijinal sıra.
- Türler gereksiz şekilde bölünmez; yaklaşık 500–600 parçayı aşan listeler bölünür.
- İlk sürümde filtreleme deterministik ve isteğe bağlı olur; live, remix, karaoke gibi sürümler başlık kurallarıyla filtrelenebilir.
- Planlanan teknoloji Python ve `ytmusicapi`dir.

---

## History

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
