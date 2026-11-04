# Araç Döndürme Platformu — Basit Sürüm

Raspberry Pi 5 + Raspberry Pi AI Camera (IMX500). Nesne tespiti kameranın kendi çipinde çalışan COCO modeliyle yapılır.

## Kurallar
Düğmeye (`d` tuşu) basıldığında platform yalnızca şu durumda döner (DÖNDÜR KOMUTU = 1):
- Araç kutusu **yuvarlak** güvenli bölgenin **tamamen içindeyse** (sınırla çakışan ya da dışarıdaki araç → döndürme yok)
- Çevrede canlı (insan, kedi, köpek) yoksa (merkezi araç kutusunun içinde kalanlar araç içi sayılıp yok sayılır)

Tek basış dönüşü başlatır (basılı tutmak gerekmez); motor `rotation_seconds` süresi dolunca durur. Platform dönmüşken düğmeye basılırsa platform home'a döner. Platform home'da değilken kamerada `auto_home_seconds` (10 sn) boyunca hiç araç görünmezse otomatik olarak home'a döner; o an çevrede canlı varsa canlı uzaklaşınca döner. Dönüş sırasında canlı algılanırsa platform hemen durur. Dönüş başladıktan sonra araç konumu kontrol edilmez (dönen aracın kutusu daireden taşabileceği için). FPS hem konsolda hem önizlemede gösterilir. Sadece `car`, `person`, `cat`, `dog` etiketleri dikkate alınır; diğer nesneler hiç işlenmez (`config.py` → `SafetyConfig`).

| Durum   | Kırmızı LED | Beyaz LED | Buzzer  |
|---------|-------------|-----------|---------|
| Duruyor | Açık        | Kapalı    | Sessiz  |
| Dönüyor | Kapalı      | Açık      | Kesikli |

## Giriş / çıkış akışı
Araç hem girerken hem çıkarken platforma düz girer, platform **saat yönünün tersine 90°** döner ve araç geri geri hareket eder:
- **Giriş:** Araç güneydeki kapıdan platforma girer → OK → platform döner → araç geri geri doğudaki garaj odasına girer.
- **Çıkış:** Araç garaj odasından platforma çıkar → OK → platform döner → araç geri geri kapıdan çıkar.

Her iki durumda araç platformdan ayrıldıktan sonra kamerada 10 sn araç görünmezse platform **saat yönünde** home'a döner; yeni araç gelebilir ya da garajdaki araç çıkabilir.

## Konum algılama (gerçek sistem)
- **90° konumu:** Lazer mesafe sensörü platform ucundaki metali görür (platform hep aynı 90° konumuna gittiği için tek metal yeterli).
- **Home:** Motoru panodaki mekanik switch keser; Pi switch'i okumaz, belirli süre dolunca home'a varılmış kabul eder.
- **Ara konum** bilinmez ve gerekmez: yön her zaman belli (dışarı = saat yönünün tersi, home = saat yönü); motor hedefe varana kadar döner.

## Klasör yapısı
```
domain/        İş kuralları (donanımdan bağımsız): geometri, yuvarlak bölge, tespit, güvenlik
application/   Arayüzler (ports), kontrolcü, ayarlanabilir bölge, FPS ölçer
hardware/      AI Camera, klavye dinleyici, simüle düğme/motor, LED/buzzer, bölge kaydı
presentation/  Konsol çıktısı ve önizleme çizimi
config.py      Tüm ayarlar (güvenli bölge, pinler, eşikler)
main.py        Bileşenleri bağlayan giriş noktası
```

## Kurulum
```bash
sudo apt update && sudo apt install -y imx500-all python3-picamera2 python3-opencv python3-gpiozero python3-lgpio
sudo reboot
```
Sanal ortam kullanılacaksa picamera2 sistem paketinden geldiği için `python3 -m venv --system-site-packages .venv`.

## Çalıştırma
```bash
python3 main.py
```
| Tuş | Görev |
|-----|-------|
| `d` | Döndür düğmesi |
| `+` / `-` ya da `b` / `v` | Güvenli bölgeyi büyüt / küçült |
| Ok tuşları ya da `i` `m` `j` `l` | Güvenli bölgeyi yukarı / aşağı / sola / sağa taşı |
| `k` | Bölgeyi `zone.json` dosyasına kaydet (açılışta otomatik yüklenir) |
| `q` | Çıkış |

Bağlı olmayan bir tuşa basılırsa terminalde `Tanımsız tuş geldi: '…'` yazar; bir tuş çalışmıyorsa ne gönderdiğini buradan görüp `KeyboardConfig` içine ekleyebilirsiniz. Tuşlar terminale gider; önizleme penceresi açıksa tuşlamadan önce terminal penceresine tıklayın. Loglar `logs/platform.log` dosyasına da yazılır.

## Bağlantı (varsayılan, BCM)
Kırmızı LED → GPIO17, beyaz LED → GPIO27, buzzer → GPIO22 (LED'lere seri direnç unutmayın). `config.py` → `GpioConfig` ile değiştirilebilir.

## Ayarlanacaklar
- Güvenli bölge: Çalışırken klavyeyle ayarlayıp `k` ile kaydedin. `zone.json` yoksa `SafetyConfig` içindeki varsayılan merkez/yarıçap kullanılır. Adım büyüklükleri `zone_move_step` ve `zone_resize_step`.
- `CameraConfig.show_preview`: Monitör yoksa (SSH) `False`.
- `MotorConfig.rotation_seconds`: Simüle dönüş süresi.

## Gerçek donanıma geçiş
`application/ports.py` içindeki `RotationMotor` (lazer okuma + süreli home) ve `CommandButton` arayüzlerini uygulayan yeni sınıflar yazıp `main.py` içinde `SimulatedMotor` ve `SimulatedButton` yerine verin; diğer kodlar değişmez.

`zone.json` kuruluma özel çalışma dosyasıdır; repoya eklemeyin (`.gitignore`).
