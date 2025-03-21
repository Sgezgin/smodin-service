import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import subprocess
import time
import logging
import traceback

# Loglama dizinini oluştur
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Loglama ayarları
logging.basicConfig(
    filename=os.path.join(log_directory, 'windows_service.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SmodinService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SmodinService"
    _svc_display_name_ = "Smodin Paragraf Değiştirme Servisi"
    _svc_description_ = "Belgeleri işleyen ve paragraf değiştirmek için paraphrasetool.ai'ye gönderen servis"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = True
        self.process = None
        logging.info("SmodinService başlatıldı")

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
        logging.info("SmodinService durdurma sinyali alındı")
        
        # Python işlemini sonlandır (eğer çalışıyorsa)
        if self.process:
            try:
                logging.info("Alt işlem sonlandırılıyor")
                self.process.terminate()
            except Exception as e:
                logging.error(f"Alt işlem sonlandırma hatası: {str(e)}")

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        logging.info("SmodinService çalışmaya başlıyor")
        self.main()

    def main(self):
        # Python scriptinin yolu
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smodin_service.py')
        logging.info(f"Çalıştırılacak script: {script_path}")
        
        # Scripti Python ile çalıştır
        python_exe = sys.executable
        logging.info(f"Kullanılan Python: {python_exe}")
        
        while self.is_running:
            try:
                # Python scriptini alt işlem olarak başlat
                logging.info("Alt işlem başlatılıyor...")
                self.process = subprocess.Popen([python_exe, script_path])
                logging.info(f"Alt işlem başlatıldı (PID: {self.process.pid})")
                
                # Servis durdurma sinyali için bekle
                while self.is_running:
                    rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                    if rc == win32event.WAIT_OBJECT_0:
                        # Servis durdurma sinyali alındı
                        logging.info("Durdurma sinyali alındı, işlem sonlandırılıyor")
                        self.is_running = False
                        break
                    
                    # İşlemin hala çalışıp çalışmadığını kontrol et
                    if self.process.poll() is not None:
                        # İşlem sonlandıysa, yeniden başlat
                        exit_code = self.process.returncode
                        error_msg = f"Python scripti beklenmedik şekilde sonlandı. Çıkış kodu: {exit_code}. Yeniden başlatılıyor..."
                        logging.warning(error_msg)
                        servicemanager.LogMsg(
                            servicemanager.EVENTLOG_WARNING_TYPE,
                            servicemanager.PYS_SERVICE_STARTED,
                            (self._svc_name_, error_msg)
                        )
                        break
                
                # İşlem hala çalışıyorsa sonlandır
                if self.process and self.process.poll() is None:
                    logging.info("Alt işlem hala çalışıyor, sonlandırılıyor")
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=10)
                        logging.info("Alt işlem başarıyla sonlandırıldı")
                    except subprocess.TimeoutExpired:
                        logging.warning("Alt işlem zaman aşımına uğradı, zorla sonlandırılıyor")
                        self.process.kill()
                
            except Exception as e:
                error_details = traceback.format_exc()
                error_msg = f"SmodinService'de hata: {str(e)}"
                logging.error(f"{error_msg}\n{error_details}")
                servicemanager.LogErrorMsg(error_msg)
                time.sleep(5)  # Yeniden denemeden önce bekle

if __name__ == '__main__':
    if len(sys.argv) == 1:
        try:
            logging.info("Windows servis denetleyicisi başlatılıyor")
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(SmodinService)
            servicemanager.StartServiceCtrlDispatcher()
        except Exception as e:
            error_details = traceback.format_exc()
            logging.critical(f"Servis denetleyicisi başlatma hatası: {str(e)}\n{error_details}")
    else:
        try:
            logging.info(f"Komut satırı komutu işleniyor: {' '.join(sys.argv)}")
            win32serviceutil.HandleCommandLine(SmodinService)
        except Exception as e:
            error_details = traceback.format_exc()
            logging.critical(f"Komut satırı komutu işleme hatası: {str(e)}\n{error_details}")