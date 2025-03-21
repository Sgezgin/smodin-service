import os
import sys
import subprocess
import configparser
import logging
import traceback

# Loglama dizinini oluştur
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Loglama ayarları
logging.basicConfig(
    filename=os.path.join(log_directory, 'setup.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def install_requirements():
    """Gerekli Python paketlerini kur"""
    print("Gerekli paketler kuruluyor...")
    logging.info("Gerekli paketler kuruluyor")
    packages = [
        "pywin32",
        "docx",
        "requests",
        "sqlalchemy",
        "pyodbc",
        "asyncio"
    ]
    
    for package in packages:
        try:
            print(f"Kurulum: {package}")
            logging.info(f"Kuruluyor: {package}")
            result = subprocess.run([sys.executable, "-m", "pip", "install", package], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                logging.info(f"{package} başarıyla kuruldu")
            else:
                logging.error(f"{package} kurulumu başarısız: {result.stderr}")
                print(f"HATA: {package} kurulumu başarısız oldu.")
                print(result.stderr)
        except Exception as e:
            error_details = traceback.format_exc()
            logging.error(f"{package} kurulumu sırasında hata: {str(e)}\n{error_details}")
            print(f"HATA: {package} kurulumunda beklenmeyen bir hata oluştu: {str(e)}")
    
    print("Paket kurulumu tamamlandı.")
    logging.info("Paket kurulumu tamamlandı")

def create_config_file():
    """Servis için yapılandırma dosyası oluştur"""
    logging.info("Yapılandırma dosyası oluşturuluyor")
    config = configparser.ConfigParser()
    
    # Veritabanı ayarları
    config['Veritabani'] = {
        'BaglantiDizesi': 'mssql+pyodbc://kullaniciadi:sifre@sunucu/MAKALEDBEntities1?driver=ODBC+Driver+17+for+SQL+Server'
    }
    
    # Yol ayarları
    config['Yollar'] = {
        'GeciciDizin': 'C:\\Temp'
    }
    
    # API ayarları
    config['API'] = {
        'TemelUrl': 'https://www.paraphrasetool.ai',
        'UcNokta': '/get_content'
    }
    
    # Loglama ayarları
    config['Loglama'] = {
        'LogDizini': 'logs',
        'LogSeviyesi': 'INFO',
        'MaksimumDosyaBoyutu': '10485760',  # 10 MB
        'YedekSayisi': '5'
    }
    
    # Yapılandırmayı dosyaya yaz
    try:
        with open('smodin_config.ini', 'w') as configfile:
            config.write(configfile)
        logging.info("Yapılandırma dosyası başarıyla oluşturuldu")
        print("Yapılandırma dosyası oluşturuldu. Lütfen 'smodin_config.ini' dosyasını veritabanı bilgilerinizle düzenleyin.")
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Yapılandırma dosyası oluşturma hatası: {str(e)}\n{error_details}")
        print(f"Yapılandırma dosyası oluşturulamadı: {str(e)}")

def install_service():
    """Windows servisini kur"""
    print("Windows servisi kuruluyor...")
    logging.info("Windows servisi kuruluyor")
    try:
        result = subprocess.run([sys.executable, "windows_service.py", "install"], 
                                capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info("Servis başarıyla kuruldu")
            print("Servis başarıyla kuruldu!")
            print("Servisi şu komutla başlatabilirsiniz:")
            print("   python windows_service.py start")
        else:
            logging.error(f"Servis kurulum hatası: {result.stderr}")
            print("Servis kurulumu başarısız oldu!")
            print(result.stderr)
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Servis kurulumu sırasında hata: {str(e)}\n{error_details}")
        print(f"Servis kurulumu sırasında hata: {str(e)}")

def main():
    logging.info("=== Smodin Servis Kurulumu Başlatıldı ===")
    
    # Yönetici ayrıcalıklarıyla çalışıp çalışmadığını kontrol et
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logging.warning(f"Yönetici kontrolü yapılamadı: {str(e)}")
        is_admin = False
    
    if not is_admin:
        logging.warning("Script yönetici ayrıcalıklarıyla çalıştırılmıyor")
        print("Bu script'in yönetici ayrıcalıklarıyla çalıştırılması gerekiyor.")
        print("Lütfen scripti yönetici olarak yeniden başlatın.")
        return
    
    print("=== Smodin Servis Kurulumu ===")
    print("Bu script, Smodin paragraf değiştirme servisini kurmanıza yardımcı olacaktır.")
    
    # Onay iste
    confirm = input("Kuruluma devam etmek istiyor musunuz? (e/h): ")
    if confirm.lower() != 'e':
        logging.info("Kullanıcı kurulumu iptal etti")
        print("Kurulum iptal edildi.")
        return
    
    # Python gereksinimlerini kur
    try:
        install_requirements()
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Gereksinimleri kurma hatası: {str(e)}\n{error_details}")
        print(f"Gereksinimleri kurma hatası: {str(e)}")
        return
    
    # Yapılandırma dosyası oluştur
    try:
        create_config_file()
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Yapılandırma dosyası oluşturma hatası: {str(e)}\n{error_details}")
        print(f"Yapılandırma dosyası oluşturma hatası: {str(e)}")
        return
    
    # Veritabanı yapılandırmasının güncellendiğini onayla
    input("Lütfen 'smodin_config.ini' dosyasındaki veritabanı bağlantısını güncellediğinizden emin olun.\nDevam etmek için Enter tuşuna basın...")
    
    # Windows servisini kur
    try:
        install_service()
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Servis kurulumu hatası: {str(e)}\n{error_details}")
        print(f"Servis kurulumu hatası: {str(e)}")
        return
    
    logging.info("Kurulum tamamlandı")
    print("\nKurulum tamamlandı!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_details = traceback.format_exc()
        logging.critical(f"Beklenmeyen hata: {str(e)}\n{error_details}")
        print(f"Beklenmeyen bir hata oluştu: {str(e)}")