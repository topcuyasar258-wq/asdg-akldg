# 🎯 LeadHunter — veridiareklam.com.tr

Google Maps'teki işletmeleri her gün otomatik tarayıp **potansiyel müşterileri tespit eden** ve size **WhatsApp raporu** gönderen sistem.

## Ne yapar?

1. **Google Maps taraması** — Resmi Google Places API ile işletmeleri bulur (isim, telefon, adres, puan, yorumlar, web sitesi).
2. **Yorum analizi** — Yorum sayısı, ortalama puan ve Türkçe şikayet sinyallerini değerlendirir.
3. **Web sitesi analizi** — Site var mı, açılıyor mu, SSL'i var mı, mobil uyumlu mu, yavaş mı?
4. **Sosyal medya tespiti** — Sitedeki Instagram / Facebook / X / LinkedIn / YouTube hesaplarını bulur.
5. **Lead puanlama (0-100)** — Dijital varlığı zayıf işletme = ajans için yüksek potansiyel. Her lead için önerilecek hizmet listesi çıkarır (web tasarım, sosyal medya yönetimi, itibar yönetimi...).
6. **WhatsApp raporu** — En iyi lead'leri işletme telefonuyla birlikte numaranıza iletir.
7. **Tekrarsız günlük çalışma** — GitHub Actions her sabah 09:00'da (TR) çalışır; daha önce bildirilen işletmeler bir daha bildirilmez.

## Kurulum

### 1. Google Places API anahtarı

1. [Google Cloud Console](https://console.cloud.google.com/) → proje oluşturun.
2. **Places API (New)**'i etkinleştirin.
3. API anahtarı oluşturun.

### 2. WhatsApp (CallMeBot — ücretsiz, önerilen)

1. Telefonunuzdan **+34 621 331 709** numarasını rehbere ekleyin.
2. Bu numaraya WhatsApp'tan şu mesajı gönderin: `I allow callmebot to send me messages`
3. Gelen cevaptaki **API key**'i kaydedin.
   (Detay: [callmebot.com/blog/free-api-whatsapp-messages](https://www.callmebot.com/blog/free-api-whatsapp-messages/))

Alternatif olarak kurumsal kullanım için Twilio WhatsApp API da desteklenir.

### 3. GitHub Secrets

Repo → **Settings → Secrets and variables → Actions** altına ekleyin:

| Secret | Açıklama | Zorunlu |
|---|---|---|
| `GOOGLE_PLACES_API_KEY` | Google Places API anahtarı | ✅ |
| `WHATSAPP_TO` | Raporun gideceği numara, örn. `+90532xxxxxxx` | ✅ |
| `CALLMEBOT_API_KEY` | CallMeBot anahtarı | ✅ (veya Twilio) |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_WHATSAPP_FROM` | Twilio kullanacaksanız | ❌ |

Bunlar tamamlandığında sistem her gün kendiliğinden çalışır — başka bir şey yapmanıza gerek yok.

## Tarama profilleri

`config/profiles.yaml` dosyasında haftanın her günü için farklı bir sektör/bölge profili tanımlıdır:

| Gün | Profil | Örnek |
|---|---|---|
| Pazartesi | restoran-kafe | Kadıköy restoranları |
| Salı | guzellik-bakim | Şişli güzellik salonları |
| Çarşamba | saglik | Diş klinikleri, veterinerler |
| Perşembe | hizmet-sektoru | Emlak, oto servis, nakliyat |
| Cuma | perakende | Mobilya, butik, çiçekçi |
| Cumartesi | egitim-spor | Kurslar, spor salonları |
| Pazar | konaklama-turizm | Butik oteller, tur acenteleri |

Sorguları, şehirleri ve eşikleri (`min_lead_score`, `max_leads_per_report` vb.) bu dosyadan dilediğiniz gibi değiştirebilirsiniz.

## Elle çalıştırma

GitHub → **Actions → Günlük Lead Taraması → Run workflow** ile istediğiniz an, istediğiniz profil veya özel sorguyla çalıştırabilirsiniz.

Bilgisayarınızda test için:

```bash
pip install -r requirements.txt
export GOOGLE_PLACES_API_KEY="..."
python main.py --query "kafe Moda İstanbul" --dry-run   # WhatsApp göndermeden dene
python main.py --profile saglik                          # belirli profili çalıştır
```

## Örnek WhatsApp raporu

```
🎯 VERİDİA REKLAM — Günlük Lead Raporu
📅 07.07.2026 | Profil: restoran-kafe
🔍 Taranan işletme: 54 | Potansiyel müşteri: 6

1) Örnek Lokantası — Skor: 75/100
📞 (0216) 555 55 55
📍 Caferağa Mah. ... Kadıköy/İstanbul
⭐ 3.8 (14 yorum)
❗ Web sitesi yok | Instagram hesabı bulunamadı | Az yorum (14 adet) | Düşük puan (3.8)
💼 Önerilecek hizmet: Web tasarım, Sosyal medya yönetimi, İtibar yönetimi
🗺️ https://maps.google.com/?cid=...
```

## Puanlama mantığı

| Sinyal | Puan |
|---|---|
| Web sitesi yok | +30 |
| Site yerine Instagram/Linktree kullanıyor | +25 |
| Sitesi var ama açılmıyor | +25 |
| Instagram hesabı yok | +15 |
| SSL yok / mobil uyumsuz | +10 / +10 |
| 20'den az yorum | +10 |
| Google puanı 4.0 altı | +10 |
| Yorumlarda şikayet sinyali | +5 |
| Facebook yok / site yavaş | +5 / +5 |

`min_lead_score` (varsayılan 40) üzerindeki işletmeler rapora girer; telefonu olmayanlar elenir.

## ⚠️ Önemli not

Bu sistem lead'leri **size** raporlar. Tespit edilen işletmelere toplu/otomatik mesaj gönderimi yapmaz ve yapılmamalıdır — Türkiye'de ticari elektronik ileti için 6563 sayılı kanun (İYS) kapsamında alıcı onayı gerekir. İletişimi ekibiniz birebir kurmalıdır.
