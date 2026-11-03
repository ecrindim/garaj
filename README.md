# Araç Döndürme Platformu — Basit Sürüm

Raspberry Pi 5 + Raspberry Pi AI Camera (IMX500). Nesne tespiti kameranın kendi çipinde çalışan COCO modeliyle yapılır.

## Kurallar
Düğmeye (`d` tuşu) basıldığında platform yalnızca şu durumda döner (DÖNDÜR KOMUTU = 1):
- Araç kutusu güvenli bölgenin **tamamen içindeyse** (sınırla çakışan ya da dışarıdaki araç → döndürme yok)
- Çevrede insan yoksa (merkezi araç kutusunun içinde kalan insanlar araç içi sayılıp yok sayılır)

Dönüş sırasında insan algılanırsa platform durur.

| Durum   | Kırmızı LED | Beyaz LED | Buzzer  |
|---------|-------------|-----------|---------|
| Duruyor | Açık        | Kapalı    | Sessiz  |
| Dönüyor | Kapalı      | Açık      | Kesikli |

## Klasör yapısı
```
domain/        İş kuralları (donanımdan bağımsız): geometri, tespit, güvenlik
application/   Arayüzler (ports) ve kontrolcü (durum makinesi)
hardware/      AI Camera, klavye-düğme, simüle motor, LED/buzzer
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
`d` = döndür, `q` = çıkış. Loglar `logs/platform.log` dosyasına da yazılır.

## Bağlantı (varsayılan, BCM)
Kırmızı LED → GPIO17, beyaz LED → GPIO27, buzzer → GPIO22 (LED'lere seri direnç unutmayın). `config.py` → `GpioConfig` ile değiştirilebilir.

## Ayarlanacaklar
- `SafetyConfig.safe_zone`: Güvenli bölge, 0–1 arası normalize koordinatlar. Önizlemede çizilen yeşil/kırmızı dikdörtgene bakarak platforma oturtun.
- `CameraConfig.show_preview`: Monitör yoksa (SSH) `False`.
- `MotorConfig.rotation_seconds`: Simüle dönüş süresi.

## Gerçek donanıma geçiş
`application/ports.py` içindeki `RotationMotor` ve `CommandButton` arayüzlerini uygulayan yeni sınıflar yazıp `main.py` içinde `SimulatedMotor` ve `KeyboardButton` yerine verin; diğer kodlar değişmez.
