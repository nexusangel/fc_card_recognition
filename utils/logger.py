# fc_card_recognition/utils/logger.py
import logging
import os
from datetime import datetime
from pathlib import Path

def setup_logger():
    """로깅 설정"""
    # 기본 경로 설정
    base_dir = os.path.join(str(Path.home()), "fc_online_data")
    logs_dir = os.path.join(base_dir, "logs")
    
    # 로그 디렉토리 생성
    os.makedirs(logs_dir, exist_ok=True)
    
    # 로그 파일 경로 (날짜별)
    log_file = os.path.join(logs_dir, f"fc_online_{datetime.now().strftime('%Y%m%d')}.log")
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # 로거 가져오기
    logger = logging.getLogger("FC_Online_Recognition")
    
    # 로그 시작 메시지
    logger.info("=== FC 온라인 선수 카드 정보 인식 시스템 로깅 시작 ===")
    
    return logger