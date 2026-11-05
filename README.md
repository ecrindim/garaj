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
- **Otomatik acil durdurma:** Şu durumlarda sistem kendiliğinden kilitlenir:
  - Home ve 90° switch'leri aynı anda basılı (kablo ya da switch arızası). Arıza sürdükçe `#` sıfırlamaz.
  - Motor çalıştırıldı ama platform `departure_timeout_seconds` (3 sn) içinde başlangıç switch'inden ayrılmadı (motor, röle ya da pano arızası).
  - Bir hareket `motion_timeout_seconds` (20 sn) içinde hedefe varmadı (sıkışma, switch arızası).
- **Röle güvenliği:** İki röle asla aynı anda çekmez; yön değişiminde aralarında 0,5 sn beklenir. Röleler GPIO2/GPIO3'te olduğu için (kart üzerinde pull-up) Pi açılırken ya da program çalışmıyorken bırakık kalır.
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

## Konum algılama ve motor kontrolü
- **Konum:** İki mekanik limit switch okunur. Home switch'i basılıysa HOME, 90° switch'i basılıysa DÖNMÜŞ, ikisi de bırakıksa ARADA, ikisi birden basılıysa ARIZA. Switch'ler panodaki (motoru uçlarda kesen) switch'lerin yanına **ayrı** olarak takılır.
- **Motor:** Pi, 4 kanallı röle modülünün iki kanalıyla panoya "döndür" (saat yönünün tersi) ve "home" (saat yönü) sinyali verir. Motoru pano çalıştırır; panodaki limit switch'ler ve yön kilitlemesi görevini sürdürür. Motor akımı röleden geçmez.
- **Simülasyon:** Switch'ler ya da röleler bağlanmadan da sistem çalışır. `use_limit_switches = False` iken konum süreyle simüle edilir; `use_relays = False` iken motor komutları ekrana yazılır. İkisi bağımsızdır; örneğin switch'ler gelmeden röle ve pano bağlantısı test edilebilir.

## Devre şeması
![Devre şeması](docs/devre_semasi.svg)

| Bileşen | Bağlantı (fiziksel pin) |
|---|---|
| Kırmızı LED | GPIO17 (11) → 330 Ω → LED → GND |
| Beyaz LED | GPIO27 (13) → 330 Ω → LED → GND |
| Aktif buzzer | GPIO22 (15) → buzzer + ; buzzer − → GND |
| KY-022 IR alıcı | `S` → GPIO23 (16), `+` → 3.3V (17), `−` → GND |
| Home limit switch | NO kontağın bir ucu → GPIO4 (7), diğer ucu → GND (9) |
| 90° limit switch | NO kontağın bir ucu → GPIO24 (18), diğer ucu → GND (14) |
| AI Camera | Şerit kablo → CAM/DISP 0 |
| Röle modülü (giriş tarafı) | VCC → 3.3V (1), IN1 → GPIO2 (3) döndür, IN2 → GPIO3 (5) home; giriş tarafı GND **bağlanmaz** |
| Röle modülü (güç tarafı) | JD-VCC jumper'ı **çıkarılır**; JD-VCC ve GND → **ayrı 5V adaptör** |
| Röle kontakları → pano | Röle 1 COM–NO → pano "döndür", röle 2 COM–NO → pano "home" (elektrikçi) |

- **Limit switch'ler:** Pi'nin dahili pull-up direnci kullanılır, ek direnç ya da besleme gerekmez. Switch basılıyken pin LOW okunur. Panodaki (yüksek voltajlı) devreye bağlı bir kontak kullanılmaz.
- **Röle modülü:** Giriş tarafı Pi'nin 3.3V'u ile beslendiği için aktif-LOW röleler düzgün çeker ve bırakır. Röle bobinleri ayrı 5V adaptörden beslenir ve adaptörün GND'si Pi'ye bağlanmaz; optokuplör yalıtımı bu sayede korunur.
- **Pano bağlantısı (elektrikçi):** Sadece NO kontak kullanılır. Panoda mühürleme (self-hold) olmamalı: motor yalnızca röle kapalıyken dönmeli, röle açılınca durmalı. Böylece Pi canlı gördüğünde ya da acil durdurmada motoru durdurabilir; Pi'nin ya da elektriğin kesilmesi de motoru durdurur. Panoda iki yönün aynı anda çalışmasını engelleyen elektriksel kilitleme bulunmalı.
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
| `MotorConfig.use_limit_switches` | False | Home ve 90° switch'leri takıldıktan sonra True |
| `MotorConfig.home_switch_pin` / `rotated_switch_pin` | 4 / 24 | Switch pinleri |
| `MotorConfig.departure_timeout_seconds` | 3 | Motor çalışınca platformun switch'ten ayrılması için süre |
| `MotorConfig.use_relays` | False | Röle modülü ve pano bağlantısı yapıldıktan sonra True |
| `MotorConfig.rotate_relay_pin` / `home_relay_pin` | 2 / 3 | Röle pinleri |
| `MotorConfig.relay_active_low` | True | Modül IN pini LOW olunca çeker |
| `MotorConfig.relay_dead_time_seconds` | 0.5 | Yön değişiminde iki röle arasındaki bekleme |
| `MotorConfig.rotation_seconds` | 6 | Simülasyonda 90° dönüş süresi |
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
application/   Arayüzler (ports), kontrolcü, platform motoru (iki limit switch),
               ayarlanabilir bölge, araç yokluk sayacı, güvensiz durum izleyici, FPS ölçer
hardware/      AI Camera, IR kumanda (ham LIRC + NEC çözücü), klavye, limit switch'ler, röle sürücüsü, LED/buzzer,
               ekrana yazan motor sürücüsü, simüle motor, bölge ve fotoğraf kaydı
presentation/  Konsol çıktısı ve önizleme çizimi
docs/          Devre şeması
config.py      Tüm ayarlar
main.py        Bileşenleri bağlayan giriş noktası
```

## Gerçek donanıma geçiş (sırasıyla)
1. **Röle testi (motor bağlı değilken):** Röle modülünü bağlayın, `use_relays = True` yapın. `d` ile döndürünce röle 1'in, home'da röle 2'nin çektiğini (LED ve tık sesi) ve `x` ile ikisinin de bıraktığını kontrol edin. Program kapalıyken röleler bırakık olmalı.
2. **Switch testi:** Switch'leri bağlayıp `use_limit_switches = True` yapın. Switch'lere elle basarak konsoldaki `Konum: HOME / DÖNMÜŞ / ARADA` değerini kontrol edin. İkisine birden basınca sistemin acil durdurmaya geçtiğini görün.
3. **Pano bağlantısı:** Elektrikçi röle kontaklarını panoya bağladıktan sonra platformu boşken, fiziksel acil stop butonunun yanında durarak deneyin.
