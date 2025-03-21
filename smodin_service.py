import os
import time
import asyncio
import docx
import requests
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import re
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from typing import List, Optional
import logging
import traceback

# Loglama için konfigürasyon
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

logging.basicConfig(
    filename=os.path.join(log_directory, 'smodin_service.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Veritabanı Modelleri
Base = declarative_base()

class Makale(Base):
    __tablename__ = 'Makale'
    
    Id = Column(Integer, primary_key=True)
    SavePath = Column(String(255))
    BitisTarih = Column(DateTime, nullable=True)
    # Diğer gerekli alanlar

class MakaleDetay(Base):
    __tablename__ = 'MakaleDetay'
    
    Id = Column(Integer, primary_key=True)
    MakaleId = Column(Integer, ForeignKey('Makale.Id'))
    Icerik = Column(Text)
    SmodinIcerik = Column(Text, nullable=True)
    GuncellemeTarih = Column(DateTime, nullable=True)
    # Diğer gerekli alanlar

class Token(Base):
    __tablename__ = 'Token'
    
    Id = Column(Integer, primary_key=True)
    Bearer = Column(String(255), nullable=True)
    Cookie = Column(String(255), nullable=True)
    HataMessage = Column(Text, nullable=True)
    HataMessageTarih = Column(DateTime, nullable=True)
    Bekletme = Column(Integer, nullable=True)
    Kelime = Column(Integer, nullable=True)
    # Diğer gerekli alanlar

class SmodinService:
    def __init__(self, db_connection_string):
        """Servisi veritabanı bağlantısı ile başlat"""
        logging.info("Smodin servisi başlatılıyor")
        try:
            self.engine = sa.create_engine(db_connection_string)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            logging.info("Veritabanı bağlantısı başarıyla kuruldu")
        except Exception as e:
            error_details = traceback.format_exc()
            logging.error(f"Veritabanı bağlantısı kurulurken hata oluştu: {str(e)}\n{error_details}")
            raise
        
    async def paraphrasetool_kontrol_dosya(self):
        """Belge dosyalarını işle ve yönetilebilir parçalara böl"""
        try:
            session = self.Session()
            logging.info("paraphrasetool_kontrol_dosya: DOCX dosyalarının işlenmesi başlıyor")
            
            # Varsayılan maksimum kelime sayısı
            max_kelime = 1400
            
            # Tüm makaleleri al
            makale_list = session.query(Makale).all()
            logging.info(f"İşlenecek makale sayısı: {len(makale_list)}")
            
            # Token ve kelime limiti ayarlarını al
            tkn = session.query(Token).filter(Token.Bearer != None).first()
            if tkn and tkn.Kelime:
                max_kelime = int(tkn.Kelime)
                logging.info(f"Token ayarlarından maksimum kelime sayısı: {max_kelime}")
                
            for item in makale_list:
                # Makale detaylarının zaten var olup olmadığını kontrol et
                makdetay_count = session.query(MakaleDetay).filter(
                    MakaleDetay.MakaleId == item.Id).count()
                
                filepath = os.path.join("C:\\Temp", f"{item.SavePath}.docx")
                
                if makdetay_count == 0 and os.path.exists(filepath):
                    # Belge varsa ve henüz işlenmediyse işle
                    logging.info(f"Dosya işleniyor: {filepath}")
                    try:
                        doc = docx.Document(filepath)
                        paragraphs = doc.paragraphs
                        
                        current_count = 0
                        first = 0
                        detay_icerik = ""
                        
                        for i, p in enumerate(paragraphs):
                            makdetay_icerik = p.text
                            
                            if makdetay_icerik.strip():
                                kelime_cnt = len(makdetay_icerik.split())
                                
                                if first == 0:
                                    detay_icerik = makdetay_icerik
                                    current_count = kelime_cnt
                                    
                                    if 900 < current_count < 1300:
                                        # Kelime sayısı istenen aralıktaysa yeni detay kaydı oluştur
                                        new_makdetay = MakaleDetay(
                                            MakaleId=item.Id,
                                            Icerik=makdetay_icerik
                                        )
                                        session.add(new_makdetay)
                                        session.commit()
                                        logging.info(f"Yeni makale detayı eklendi, MakaleId: {item.Id}, Kelime sayısı: {current_count}")
                                        
                                        detay_icerik = ""
                                        current_count = 0
                                        
                                    elif current_count < max_kelime:
                                        first = 1
                                    else:
                                        first = 1
                                        # Gerekirse iki parçaya böl
                                else:
                                    if kelime_cnt + current_count < max_kelime:
                                        # Paragraflar kelime limitine sığıyorsa birleştir
                                        detay_icerik += " [...] " + makdetay_icerik
                                        current_count += kelime_cnt
                                    else:
                                        # Mevcut içeriği kaydet ve yeni detay başlat
                                        new_makdetay = MakaleDetay(
                                            MakaleId=item.Id,
                                            Icerik=detay_icerik
                                        )
                                        session.add(new_makdetay)
                                        session.commit()
                                        logging.info(f"Yeni makale detayı eklendi, MakaleId: {item.Id}, Kelime sayısı: {current_count}")
                                        
                                        detay_icerik = makdetay_icerik
                                        current_count = kelime_cnt
                        
                        # Kalan içeriği kaydet
                        if detay_icerik:
                            new_makdetay = MakaleDetay(
                                MakaleId=item.Id,
                                Icerik=detay_icerik
                            )
                            session.add(new_makdetay)
                            session.commit()
                            logging.info(f"Son makale detayı eklendi, MakaleId: {item.Id}, Kelime sayısı: {current_count}")
                    except Exception as doc_ex:
                        error_details = traceback.format_exc()
                        logging.error(f"Dosya işlenirken hata oluştu ({filepath}): {str(doc_ex)}\n{error_details}")
            
            session.close()
            logging.info("paraphrasetool_kontrol_dosya: İşlem tamamlandı")
            
        except Exception as ex:
            error_details = traceback.format_exc()
            logging.error(f"paraphrasetool_kontrol_dosya'da hata: {str(ex)}\n{error_details}")
    
    async def paraphrasetool_kontrol(self):
        """Metin parçalarını paraphrasetool.ai üzerinden işle"""
        try:
            session = self.Session()
            
            # Tüm işlenmemiş detayları al
            makale_detay_list = session.query(MakaleDetay).filter(
                MakaleDetay.SmodinIcerik == None).all()
            
            logging.info(f"İşlenecek makale detay sayısı: {len(makale_detay_list)}")
            
            for item in makale_detay_list:
                makdetay_id = item.Id
                
                # Varsayılan değerler
                token = ""
                tokenhata = None
                lang = "tr"
                mode = "Fluency" 
                action = "Rephraser"
                entered = ""
                bekletme = 1000
                
                # Token bilgilerini al
                tkn = session.query(Token).filter(Token.Bearer != None).first()
                if tkn:
                    token = tkn.Bearer
                    tokenhata = tkn.HataMessage
                    if tkn.Bekletme:
                        bekletme = int(tkn.Bekletme)
                
                # Sadece tokenhata varsa işlemi atla
                if tokenhata:
                    logging.warning(f"Token hatası nedeniyle işlem atlanıyor: {tokenhata}")
                    continue  # Bu makale detayını atla
                    
                # Token boş olsa bile işleme devam et
                logging.info(f"API isteği hazırlanıyor, MakaleDetayId: {makdetay_id}")
                
                # İçeriği API için hazırla
                entered = item.Icerik
                
                # Cümle limitini aşan içeriği işle
                icerik_cumle_count = len(entered.rstrip('.').split('.'))
                if icerik_cumle_count > 198:
                    logging.info(f"Cümle sayısı limiti aşıldı ({icerik_cumle_count}), bölümlendiriliyor")
                    icerik_ek = ""
                    icerik_cumle200 = ""
                    
                    icerik_cumle_split = entered.rstrip('.').split('.')
                    
                    for sayac, icrk_split in enumerate(icerik_cumle_split):
                        if sayac >= 198:
                            icerik_ek += icrk_split + "."
                        else:
                            icerik_cumle200 += icrk_split + "."
                    
                    entered = icerik_cumle200 + " " + icerik_ek
                
                # Metni temizle
                entered = entered.replace('"', "'")
                entered = entered.replace('/', "-")
                entered = entered.replace('@', "")
                entered = entered.replace('\\', "-")
                
                # Örnek kodunuzdaki gibi basit Cookie yapısı
                cookies = {
                    "XSRF-TOKEN": "eyJpdiI6ImZXYUNBdlI1VFBiYzhuNkxqNFRzQ3c9PSIsInZhbHVlIjoialVrUWpqaFg1cERwaDdVN0dmeE1hRFlWeDZUZU1GRndwYW83clczTzFaMHIzcDFLZWdOeHE1cHBpWGx1WVYrNlJxUGFOR2RJRHVKSFlCZGJKb01mckZzZjBlYmlJamlkWkNkdDZDKzFlOWJFNEJZUThPb1duTWFFZjNnSkhkenIiLCJtYWMiOiI1YWZhZDk3Y2RjMGUyY2NkYzU3MmJiOTRmODFlOWFhMGIyMGI1OTVmYjEyOGIxYTFmNTNkMGFlMWVmNWEyNDQ5IiwidGFnIjoiIn0%3D",
                    "paraphrasetool_session": "eyJpdiI6IkpuK1VqajdXaXhrSVh5N01wY1NKVXc9PSIsInZhbHVlIjoiK25JQVlvb3ZGdWZmcEM4SE9iSEJJT3V3dldWSENNdCtFR2pDYjAwemN2OW81U2dqdmdJVDhFdGYwenBPQWRsQnZYa3gxNVN5d29ER0U4Q2lDZnY3TndHZDlYZ1RVSm4rR0c5OEZTd1EyeFltK0tyUGdjZmxQRmVpZlpNaHU3ZWsiLCJtYWMiOiJiZjk4MDI1NzVhM2Y4NzNmZTVlNDM5YmQ2ZDdiZDM2MDhlMDhiMDEwMjVkMTQ0OWFhNDMxMDNlZjliMzM5ZWQwIiwidGFnIjoiIn0%3D",
                }
                
                # İstek başlıklarını ayarla
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "https://www.paraphrasetool.ai",
                    "Referer": "https://www.paraphrasetool.ai/tr/paragraf-desistirici",
                    "X-CSRF-TOKEN": token,
                }
                
                # İstek verilerini hazırla
                data = {
                    "_token": token,
                    "action": action,
                    "entered": entered.strip(),
                    "mode": mode,
                    "lang": "tr",
                    "max": "4000",
                    "words": "11",
                }
                
                try:
                    # paraphrasetool.ai'ye istek gönder
                    url = "https://www.paraphrasetool.ai/get_content"
                    logging.info(f"API isteği gönderiliyor: {url}")
                    
                    # Birebir örnek kodunuzdaki gibi istek yapısı
                    response = requests.post(url, headers=headers, cookies=cookies, data=data)
                    
                    logging.info(f"API yanıtı: {response.status_code}")
                    
                    if response.status_code == 200:
                        api_response = response.json()
                        
                        # API yanıtını işle
                        if api_response.get('text') and len(api_response.get('text', '')) > 0:
                            if api_response.get('text2'):
                                logging.info(f"Başarılı API yanıtı, veritabanı güncelleniyor")
                                # İşlenmiş içeriği güncelle
                                makdetay = session.query(MakaleDetay).filter(
                                    MakaleDetay.Id == makdetay_id).first()
                                
                                if makdetay:
                                    # Yanıttan HTML etiketlerini temizle
                                    cleaned_text = api_response['text2'] + (icerik_ek if 'icerik_ek' in locals() else '')
                                    cleaned_text = re.sub(r'<span class=\'sw\'>', '', cleaned_text)
                                    cleaned_text = re.sub(r'</span>', '', cleaned_text)
                                    cleaned_text = re.sub(r'<b>', '', cleaned_text)
                                    cleaned_text = re.sub(r'</b>', '', cleaned_text)
                                    cleaned_text = re.sub(r'<br>', '', cleaned_text)
                                    
                                    makdetay.SmodinIcerik = cleaned_text
                                    makdetay.GuncellemeTarih = datetime.now()
                                    session.commit()
                                    logging.info(f"MakaleDetay güncellendi: {makdetay_id}")
                                
                                # Makalenin tüm parçalarının işlenip işlenmediğini kontrol et
                                count_kalan = session.query(MakaleDetay).filter(
                                    MakaleDetay.MakaleId == item.MakaleId,
                                    MakaleDetay.SmodinIcerik == None
                                ).count()
                                
                                if count_kalan == 0:
                                    # Makaleyi tamamlandı olarak güncelle
                                    makbilgi = session.query(Makale).filter(
                                        Makale.Id == item.MakaleId).first()
                                    
                                    if makbilgi:
                                        makbilgi.BitisTarih = datetime.now()
                                        session.commit()
                                        logging.info(f"Makale tamamlandı: {item.MakaleId}")
                            else:
                                # Token'da hatayı kaydet
                                hata_mesaji = f"API yanıtında text2 alanı bulunamadı"
                                logging.error(f"API Hatası: {hata_mesaji}")
                                tkn_val = session.query(Token).filter(Token.Bearer != None).first()
                                if tkn_val:
                                    tkn_val.HataMessage = hata_mesaji
                                    tkn_val.HataMessageTarih = datetime.now()
                                    session.commit()
                        else:
                            hata_mesaji = f"API yanıtında text alanı bulunamadı veya boş"
                            logging.error(f"API Hatası: {hata_mesaji}")
                            tkn_val = session.query(Token).filter(Token.Bearer != None).first()
                            if tkn_val:
                                tkn_val.HataMessage = hata_mesaji
                                tkn_val.HataMessageTarih = datetime.now()
                                session.commit()
                    else:
                        hata_mesaji = f"API Hata Kodu: {response.status_code}, Yanıt: {response.text}"
                        logging.error(f"API Hatası: {hata_mesaji}")
                        if f"{response.status_code} {response.text}" == "0":
                            # Sıfır yanıtı alırsak bekle
                            logging.warning("Sıfır yanıtı alındı, 60 saniye bekleniyor")
                            await asyncio.sleep(60)
                        else:
                            # Token'da hatayı kaydet
                            tkn_val = session.query(Token).filter(Token.Bearer != None).first()
                            if tkn_val:
                                tkn_val.HataMessage = hata_mesaji
                                tkn_val.HataMessageTarih = datetime.now()
                                session.commit()
                except requests.exceptions.RequestException as req_ex:
                    error_details = traceback.format_exc()
                    logging.error(f"API isteği sırasında hata: {str(req_ex)}\n{error_details}")
                    
                    # Token'da hatayı kaydet
                    tkn_val = session.query(Token).filter(Token.Bearer != None).first()
                    if tkn_val:
                        tkn_val.HataMessage = f"API İstek Hatası: {str(req_ex)}"
                        tkn_val.HataMessageTarih = datetime.now()
                        session.commit()
                
                # API hız limitlerini aşmamak için istekler arasında bekle
                logging.info(f"API istekleri arasında {bekletme/1000} saniye bekleniyor")
                await asyncio.sleep(bekletme / 1000)
            
            session.close()
            
        except Exception as ex:
            error_details = traceback.format_exc()
            logging.error(f"paraphrasetool_kontrol'de hata: {str(ex)}\n{error_details}")

    @staticmethod
    def html_to_plain_text(html):
        """HTML'yi düz metne dönüştür"""
        # Satır sonlarını kaldır
        text = re.sub(r'<(br|BR)\s{0,1}\/{0,1}>', '\n', html)
        
        # Etiketleri kaldır
        text = re.sub(r'<[^>]*(>|$)', '', text)
        
        # Boşlukları temizle
        text = re.sub(r'(>|$)(\W|\n|\r)+<', '><', text)
        
        return text


async def main():
    """Servisi çalıştıran ana fonksiyon"""
    try:
        logging.info("Smodin servisi başlatılıyor")
        
        # SQL Server bağlantı dizesini oluştur
        try:
            # Entity Framework bağlantısını SQLAlchemy formatına dönüştür
            server = "DESKTOP-17HLT37"
            database = "MAKALEDB"
            username = "suphi"
            password = "Suphi102030+"
            
            # SQLAlchemy için uygun bağlantı dizesi
            db_connection_string = f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
            
            logging.info("Veritabanı bağlantı dizesi oluşturuldu")
        except Exception as config_ex:
            error_details = traceback.format_exc()
            logging.error(f"Bağlantı dizesi oluşturma hatası: {str(config_ex)}\n{error_details}")
            return
        
        # Servis örneğini oluştur
        try:
            service = SmodinService(db_connection_string)
        except Exception as service_ex:
            error_details = traceback.format_exc()
            logging.critical(f"Servis başlatma hatası: {str(service_ex)}\n{error_details}")
            return
        
        # Sürekli çalıştır
        logging.info("Ana döngü başlıyor")
        while True:
            try:
                await service.paraphrasetool_kontrol_dosya()
                await service.paraphrasetool_kontrol()
                
                # Döngüler arasında 5 saniye bekle
                await asyncio.sleep(5)
            except Exception as ex:
                error_details = traceback.format_exc()
                logging.error(f"Ana döngüde hata: {str(ex)}\n{error_details}")
                await asyncio.sleep(5)
    
    except KeyboardInterrupt:
        logging.info("Kullanıcı tarafından durduruldu (Ctrl+C)")
    except Exception as main_ex:
        error_details = traceback.format_exc()
        logging.critical(f"Ana fonksiyonda kritik hata: {str(main_ex)}\n{error_details}")


if __name__ == "__main__":
    # Program başlangıcında geçici dizinin varlığını kontrol et
    temp_dir = "C:\\Temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        logging.info(f"Geçici dizin oluşturuldu: {temp_dir}")
    
    # Servisi çalıştır
    try:
        asyncio.run(main())
    except Exception as e:
        error_details = traceback.format_exc()
        logging.critical(f"Program başlatma hatası: {str(e)}\n{error_details}")