import sys
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from src.ui.dashboard import Dashboard

# Thiết lập logging
def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/app.log"),
            logging.StreamHandler()
        ]
    )

def main():
    try:
        # Thiết lập logging
        setup_logging()
        logger = logging.getLogger(__name__)
        
        # Khởi tạo ứng dụng
        app = QApplication(sys.argv)
        
        # Thiết lập style
        app.setStyle("Fusion")
        
        # Load stylesheet
        with open("src/ui/styles/dark.qss", "r") as f:
            app.setStyleSheet(f.read())
            
        # Khởi tạo dashboard
        dashboard = Dashboard()
        dashboard.show()
        
        # Chạy ứng dụng
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()