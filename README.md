# Araç Döndürme Platformu — Basit Sürüm

Raspberry Pi 5 + Raspberry Pi AI Camera (IMX500) ile garaj girişindeki araç döndürme platformunun kontrolü. Nesne tespiti kameranın kendi çipinde çalışan COCO modeliyle yapılır; sadece `car`, `person`, `cat`, `dog` etiketleri dikkate alınır.

## Kullanım döngüsü
Tek kapı güneyde, garaj odası doğuda. Platform her seferinde **saat yönünün tersine 90°** döner ve iş bitince **saat yönünde** home'a geri gelir.

- **Giriş:** Araç kapıdan platforma önüyle girer → OK → platform döner → araç geri geri garaj odasına girer.
- **Çıkış:** Araç garaj odasından platforma önüyle çıkar → OK → platform döner → araç önüyle kapıdan çıkar.
- **Home:** Platform home'da değilken kamerada `auto_home_seconds` (10 sn) boyunca hiç araç görünmezse platform home'a döner. O an çevrede canlı varsa, canlı uzaklaşınca döner.

## Güvenlik kuralları
- **Döndürme şartı:** Araç kutusu **yuvarlak** güvenli bölgenin **tamamen içinde** olmalı ve çevrede canlı (insan, kedi, köpek) olmamalı. Araç kutusunun içinde kalan canlılar araç içi sayılıp yok sayılır.
- **Hareket sırasında:** Canlı görülürse motor hemen durur. Hareket sürerken araç konumuna bakılmaz.
- **Kaldığı yerden devam:** Platform yarıda durduysa OK'e basınca **kesilen hareket** sürdürülür: dönüyorduysa 90°'ye, home'a dönüyorduysa home'a. Dönüşe devam için normal döndürme şartları aranır. Güvenli daire, yarı dönmüş aracın kutusu da sığacak şekilde ayarlanmalıdır; taşıyorsa bir sorun var demektir ve platform hareket etmez (red fotoğrafı çekilir).
- **Home'a dönüş şartı:** Düğmeyle, devamla ya da sıfırlama sonrası home'a dönüşte çevrede canlı olmamalı ve platformda araç varsa güvenli bölgenin sınırını aşmamalıdır.
- **Acil durdur (kumandada `*`):** Motor durur ve sistem **kilitlenir**. `#` ile sıfırlanana kadar döndürme ve otomatik home çalışmaz.
- **Sıfırlama (kumandada `#`):** Kilit açılır ve platform home'da değilse **home'a döner**. Araç üstündeyse araçla birlikte döner. Şartlar sağlanmıyorsa (canlı var ya da araç sınırı aşıyor) sağlanana kadar bekler; bu sırada OK yok sayılır.
- **Zaman aşımı:** Bir hareket `motion_timeout_seconds` (20 sn) içinde hedefe varmazsa (switch arızası, sıkışma) sistem aynı şekilde kilitlenir.
- **Fiziksel acil stop:** Kumandadaki `*` yazılımsal bir durdurmadır. Motor gücünü Pi'den bağımsız kesen fiziksel acil stop butonu panoda mutlaka olmalıdır.

| Durum | Kırmızı LED | Beyaz LED | Buzzer |
|---|---|---|---|
| Duruyor | Açık | Kapalı | Sessiz |
| Dönüyor / home'a dönüyor | Kapalı | Açık | Kesikli |
| Acil durduruldu | Hızlı yanıp söner | Kapalı | Sürekli |

## Fotoğraf ve log kaydı
Fotoğraflar `photos/<tarih>/<saat>_<olay>.jpg` olarak kaydedilir (örnek: `photos/2026-11-04/14-32-05-123_dondurme_onaylandi.jpg`). Önizlemedeki daire ve tespit kutuları fotoğrafta da görünür.

| Olay | Dosya adı eki |
|---|---|
| Dönüş onaylandı (ya da yarıda kalan dönüş sürdürüldü) | `dondurme_onaylandi` |
| Araç platformdayken döndürme, devam ya da home dönüşü reddedildi | `dondurme_reddedildi` |
| Araç platformdayken çevrede canlı belirdi (en fazla 10 sn'de bir) | `guvensiz_durum` |
| Dönüş tamamlandı | `dondurme_tamamlandi` |

- **Fotoğraf saklama:** `PhotoConfig.retention_days` (30) günden eski fotoğraf klasörleri program açılışında silinir.
- **Loglar:** `logs/platform.log` dosyasına yazılır. Her gece yeni dosyaya geçilir (`platform.log.2026-11-04` gibi), son `log_retention_days` (30) günün logları saklanır.

## Konum algılama
- **90° konumu:** Platform 90°'ye gelince mekanik limit switch'e basar (switch daha sonra takılacak, kod hazır).
- **Home:** Motoru panodaki mekanik switch keser. Pi switch'i okumaz; home komutundan `home_seconds` sonra home'a varılmış kabul eder.
- **Ara konum:** Bilinmez ve gerekmez. Yön her zaman belli (dışarı = saat yönünün tersi, home = saat yönü); motor hedefe varana kadar döner.

Switch bağlanmamışken sistem tam simülasyonda çalışır (90°'ye `rotation_seconds` sonra varılır). Switch takılınca: `config.py` → `MotorConfig.use_limit_switch = True`.

## Devre şeması
![Devre şeması](docs/devre_semasi.svg)

| Bileşen | Bağlantı (fiziksel pin) |
|---|---|
| Kırmızı LED | GPIO17 (11) → 330 Ω → LED → GND |
| Beyaz LED | GPIO27 (13) → 330 Ω → LED → GND |
| Aktif buzzer | GPIO22 (15) → buzzer + ; buzzer − → GND |
| KY-022 IR alıcı | `S` → GPIO23 (16), `+` → 3.3V (17), `−` → GND |
| 90° limit switch *(planlanan)* | NO kontağın bir ucu → GPIO24 (18), diğer ucu → GND (14) |
| AI Camera | Şerit kablo → CAM/DISP 0 |
| Röle modülü *(planlanan, kodda yok)* | IN1 → GPIO5 (29) döndür, IN2 → GPIO6 (31) home |

- **Limit switch:** Pi'nin dahili pull-up direnci kullanılır, ek direnç ya da besleme gerekmez. Switch basılıyken pin LOW okunur. Panodaki (yüksek voltajlı) devreye bağlı bir kontak kullanılmaz; ayrı bir switch ya da switch'in boştaki ikinci kontağı kullanılır.
- **IR alıcı:** KY-022'yi 3.3V'a bağlayın, 5V'a değil.
- **Buzzer:** 5V buzzer doğrudan GPIO'ya bağlanmaz; araya NPN transistör (ör. 2N2222) gerekir.
- **Pano tarafı:** Pano (12–24V / 220V) asla doğrudan Pi'ye bağlanmaz; röle ya da optokuplör kullanılır.
- **Ortak GND:** Tüm GND'ler ortak olmalı. Pi 5'i resmi 27 W USB-C adaptörle besleyin.

## Kurulum (bir kez)
```bash
sudo apt update
sudo apt install -y imx500-all python3-picamera2 python3-opencv python3-gpiozero python3-lgpio v4l-utils
echo "dtoverlay=gpio-ir,gpio_pin=23" | sudo tee -a /boot/firmware/config.txt
sudo reboot
```
- **Overlay satırı:** `config.txt` içinde tam olarak `dtoverlay=gpio-ir,gpio_pin=23` olmalı (virgülden sonra **boşluk yok**) ve `[all]` başlığının altında durmalı. Boşluk olursa pin ayarı okunmaz, sürücü varsayılan GPIO18'i dinler.
- **IR kod çözme:** Program kumanda sinyalini ham olarak (`/dev/lircN`) okuyup kendi NEC çözücüsüyle çözer. KY-022 başlangıç darbesini uzattığı (~10.400 µs) ve çekirdeğin NEC çözücüsü bunu reddettiği için böyle yapılır; `ir-keytable -p nec` ya da crontab ayarı **gerekmez**.
- **IR sorun giderme:** `sudo ir-ctl -d /dev/lirc0 -r` komutu çalışırken kumandaya basınca `+9000 -4500 …` gibi sayılar akmalı. Akmıyorsa kablolama ya da overlay satırı hatalıdır. `/dev/lirc0` açılırken `Permission denied` alınırsa: `sudo usermod -aG video $USER` ve yeniden giriş.

Sanal ortam kullanılacaksa picamera2 sistem paketinden geldiği için: `python3 -m venv --system-site-packages .venv`.

## Çalıştırma
```bash
python3 main.py
```

| Kumanda | Klavye | Görev |
|---|---|---|
| OK | `d` | Döndür. Platform 90°'deyken basılırsa araçla birlikte home'a döner. |
| `*` | `x` | Acil durdur (kilitler) |
| `#` | `r` | Acil durdurmayı sıfırla |
| | `+` / `-` ya da `b` / `v` | Güvenli bölgeyi büyüt / küçült |
| | Ok tuşları ya da `i` `m` `j` `l` | Güvenli bölgeyi yukarı / aşağı / sola / sağa taşı |
| | `k` | Bölgeyi `zone.json` dosyasına kaydet (açılışta otomatik yüklenir) |
| | `q` | Çıkış |

- **Klavye:** Tuşlar terminale gider. Önizleme penceresi açıksa tuşlamadan önce terminal penceresine tıklayın.
- **Tanımsız tuş ya da kod:** Terminalde `Tanımsız tuş geldi` ya da `Tanımsız IR kodu geldi: 0x..` yazar. Kodu `KeyboardConfig` ya da `IrRemoteConfig` içine ekleyebilirsiniz.
- **Kumanda yoksa:** Kumanda bulunamazsa sistem klavyeyle çalışmaya devam eder.

Konsolda durum satırı FPS, düğme, motor durumu, konum (HOME/DÖNMÜŞ/ARADA), komut, araç/canlı bilgisi ve home geri sayımını gösterir. Önizlemede güvenli daire (güvenliyse yeşil, değilse kırmızı) ve tespit kutuları çizilir.

## Ayarlar (`config.py`)
| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `CameraConfig.confidence_threshold` | 0.55 | Tespit güven eşiği. Yanlış algılama çoksa yükseltin. |
| `CameraConfig.show_preview` | True | Monitör yoksa (SSH) False |
| `SafetyConfig.zone_*` | merkez 0.5/0.5, yarıçap 0.40 | `zone.json` yoksa kullanılan varsayılan daire |
| `SafetyConfig.vehicle_labels` / `living_labels` | car / person, cat, dog | Dikkate alınan nesneler |
| `MotorConfig.use_limit_switch` | False | 90° limit switch takıldıktan sonra True |
| `MotorConfig.rotation_seconds` | 6 | Simülasyonda 90° dönüş süresi |
| `MotorConfig.home_seconds` | 8 | Home'a varılmış sayılma süresi; gerçek dönüş süresinden biraz uzun olmalı |
| `MotorConfig.auto_home_seconds` | 10 | Araç görünmezse home'a dönme süresi |
| `MotorConfig.motion_timeout_seconds` | 20 | Hedefe varılamazsa acil durdurma süresi |
| `IrRemoteConfig.*_code` | OK 0x1C, * 0x16, # 0x0D | Kumanda tuş kodları |
| `PhotoConfig.directory` | photos | Fotoğraf klasörü |
| `PhotoConfig.retention_days` | 30 | Fotoğraf saklama süresi (gün) |
| `PhotoConfig.unsafe_cooldown_seconds` | 10 | Güvensiz durum fotoğrafları arasındaki en kısa süre |
| `log_retention_days` | 30 | Log saklama süresi (gün) |
| `GpioConfig.*_pin` | 17 / 27 / 22 | LED ve buzzer pinleri |

## Klasör yapısı
```
domain/        İş kuralları (donanımdan bağımsız): geometri, yuvarlak bölge, tespit, güvenlik
application/   Arayüzler (ports), kontrolcü, platform motoru (limit switch + süreli home),
               ayarlanabilir bölge, araç yokluk sayacı, güvensiz durum izleyici, FPS ölçer
hardware/      AI Camera, IR kumanda (ham LIRC + NEC çözücü), klavye, 90° limit switch, LED/buzzer,
               motor sürücüsü (şimdilik ekrana yazar), simüle motor, bölge ve fotoğraf kaydı
presentation/  Konsol çıktısı ve önizleme çizimi
docs/          Devre şeması
config.py      Tüm ayarlar
main.py        Bileşenleri bağlayan giriş noktası
```

## Gerçek motora geçiş
Motor komutları şu an `hardware/console_motor_driver.py` ile ekrana yazılıyor. Röleler bağlanınca `application/ports.py` içindeki `MotorDriver` arayüzünü (`start_rotate_out`, `start_return_home`, `stop`) uygulayan bir röle sürücüsü yazılır ve `main.py` içindeki `build_motor` fonksiyonunda `ConsoleMotorDriver` yerine verilir. Kontrolcü, güvenlik kuralları ve switch mantığı değişmez.

Gerçek motor gelince `home_seconds` değeri, motorun 90°'den home'a dönüş süresi ölçülerek ayarlanmalıdır.
