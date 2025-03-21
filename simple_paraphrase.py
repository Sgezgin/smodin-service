import requests
import json
import time
from datetime import datetime
import os
import logging

# Loglama ayarları
logging.basicConfig(
    filename='paraphrase_service.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def paragraf_degistir(metin, token, cookies, mode="Fluency", lang="tr"):
    """
    Metni paragraf değiştirmek için paraphrasetool.ai'ye gönderir
    
    Parametreler:
        metin: Değiştirilecek metin
        token: Kimlik doğrulama için CSRF token'ı
        cookies: Çerezler sözlüğü
        mode: Paragraf değiştirme modu (Fluency, General, vb.)
        lang: Dil kodu
        
    Dönüş:
        Değiştirilmiş metin veya hata durumunda None
    """
    url = "https://www.paraphrasetool.ai/get_content"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.paraphrasetool.ai",
        "Referer": "https://www.paraphrasetool.ai/tr/paragraf-desistirici",
        "X-CSRF-TOKEN": token,
    }

    data = {
        "_token": token,
        "action": "Rephraser",
        "entered": metin,
        "mode": mode,
        "lang": lang,
        "max": "4000",
        "words": "11",
    }

    try:
        response = requests.post(url, headers=headers, cookies=cookies, data=data)
        
        if response.status_code == 200:
            response_data = response.json()
            return response_data.get('text2')
        else:
            logging.error(f"API Hatası: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        logging.error(f"İstisna oluştu: {str(e)}")
        return None

def veritabani_kayitlarini_isle():
    """
    Veritabanındaki kayıtları işleyen fonksiyon
    Bu, SQL Server veritabanınıza bağlanır ve kayıtları işler
    """
    # Bu, veritabanı kodunuz için bir yer tutucudur
    # Burada tam servis ile benzer SQLAlchemy kodu ekleyeceksiniz
    
    # Örnek taslak kod:
    # 1. Veritabanına bağlan
    # 2. İşlenmemiş kayıtların listesini al
    # 3. Her kayıt için:
    #    - Metin içeriğini al
    #    - paragraf_degistir() fonksiyonunu çağır
    #    - Sonuçla veritabanını güncelle
    pass

def main():
    # Örnek kullanım
    token = "05cRWgc1FhznXsirLYqYtx0G4NseuDuZfqLubsAJ"  # Bu, veritabanınızdan gelmeli
    
    cookies = {
        "XSRF-TOKEN": "eyJpdiI6ImZXYUNBdlI1VFBiYzhuNkxqNFRzQ3c9PSIsInZhbHVlIjoialVrUWpqaFg1cERwaDdVN0dmeE1hRFlWeDZUZU1GRndwYW83clczTzFaMHIzcDFLZWdOeHE1cHBpWGx1WVYrNlJxUGFOR2RJRHVKSFlCZGJKb01mckZzZjBlYmlJamlkWkNkdDZDKzFlOWJFNEJZUThPb1duTWFFZjNnSkhkenIiLCJtYWMiOiI1YWZhZDk3Y2RjMGUyY2NkYzU3MmJiOTRmODFlOWFhMGIyMGI1OTVmYjEyOGIxYTFmNTNkMGFlMWVmNWEyNDQ5IiwidGFnIjoiIn0%3D",
        "paraphrasetool_session": "eyJpdiI6IkpuK1VqajdXaXhrSVh5N01wY1NKVXc9PSIsInZhbHVlIjoiK25JQVlvb3ZGdWZmcEM4SE9iSEJJT3V3dldWSENNdCtFR2pDYjAwemN2OW81U2dqdmdJVDhFdGYwenBPQWRsQnZYa3gxNVN5d29ER0U4Q2lDZnY3TndHZDlYZ1RVSm4rR0c5OEZTd1EyeFltK0tyUGdjZmxQRmVpZlpNaHU3ZWsiLCJtYWMiOiJiZjk4MDI1NzVhM2Y4NzNmZTVlNDM5YmQ2ZDdiZDM2MDhlMDhiMDEwMjVkMTQ0OWFhNDMxMDNlZjliMzM5ZWQwIiwidGFnIjoiIn0%3D",
    }
    
    # Test için, konsoldan girdi al
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "--interactive":
        kullanici_girisi = input("Lütfen metni girin: ")
        sonuc = paragraf_degistir(kullanici_girisi, token, cookies)
        
        if sonuc:
            print("Değiştirilmiş metin:")
            print(sonuc)
        else:
            print("Paragraf değiştirme başarısız oldu.")
    else:
        # Ana servis işlevi - Veritabanı kayıtlarını işle
        logging.info("Paragraf değiştirme servisi çalışmaya başlıyor")
        try:
            veritabani_kayitlarini_isle()
            logging.info("Paragraf değiştirme servisi çalışması başarıyla tamamlandı")
        except Exception as e: