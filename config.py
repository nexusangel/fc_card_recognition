# fc_card_recognition/config.py
import os
import json
import logging
from pathlib import Path

logger = logging.getLogger("FC_Online_Recognition")

def get_default_tesseract_path():
    """시스템에 맞는 기본 Tesseract 경로 반환"""
    if os.name == 'nt':  # Windows
        paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe'
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return paths[0]  # 기본 경로
    else:  # Linux/Mac
        paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/opt/local/bin/tesseract'
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return paths[0]  # 기본 경로

DEFAULT_CONFIG = {
    'paths': {
        'base_dir': os.path.join(str(Path.home()), "fc_online_data"),
        'captures_dir': 'captures',
        'models_dir': 'models',
        'training_data_dir': 'training_data',
        'debug_dir': 'debug',
        'backup_dir': 'backups',
    },
    'settings': {
        'tesseract_path': get_default_tesseract_path(),
        'auto_learning': True,
        'capture_interval': 1.0,
        'confidence_threshold': 0.7,
        'use_manual_roi': True,
        'debug_mode': True,
        'enable_caching': True,
        'auto_backup': True,
        'theme': 'system',
        'ui_scale': 1.0,
    },
    'batch': {
        'max_batch_size': 50,
        'parallel_jobs': 4
    }
}

class Config:
    """설정 관리 클래스"""
    def __init__(self, config_path=None):
        """설정 초기화"""
        self.data = DEFAULT_CONFIG.copy()
        
        # 기본 경로 설정
        base_dir = self.data['paths']['base_dir']
        self.data['paths']['captures_dir'] = os.path.join(base_dir, self.data['paths']['captures_dir'])
        self.data['paths']['models_dir'] = os.path.join(base_dir, self.data['paths']['models_dir'])
        self.data['paths']['training_data_dir'] = os.path.join(base_dir, self.data['paths']['training_data_dir'])
        self.data['paths']['debug_dir'] = os.path.join(base_dir, self.data['paths']['debug_dir'])
        self.data['paths']['backup_dir'] = os.path.join(base_dir, self.data['paths']['backup_dir'])
        
        # 설정 파일 경로
        self.config_path = config_path or os.path.join(base_dir, "config.json")
        
        # 설정 디렉토리 생성
        self._create_directories()
        
        # 설정 로드
        self.load()
    
    def _create_directories(self):
        """필요한 디렉토리 생성"""
        for path_name, path in self.data['paths'].items():
            os.makedirs(path, exist_ok=True)
        logger.info("필요한 디렉토리 생성 완료")
    
    def get(self, section, key, default=None):
        """설정 값 가져오기"""
        return self.data.get(section, {}).get(key, default)
    
    def set(self, section, key, value):
        """설정 값 설정"""
        if section not in self.data:
            self.data[section] = {}
        self.data[section][key] = value
        
        # 자동 저장
        self.save()
    
    def load(self):
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                    # 섹션별로 병합
                    for section, values in loaded_data.items():
                        if section in self.data:
                            # 기존 섹션 업데이트
                            self.data[section].update(values)
                        else:
                            # 새 섹션 추가
                            self.data[section] = values
                            
                logger.info(f"설정 로드 완료: {self.config_path}")
            else:
                # 기본 설정 저장
                self.save()
                logger.info(f"기본 설정 파일 생성: {self.config_path}")
        except Exception as e:
            logger.error(f"설정 로드 오류: {e}")
    
    def save(self):
        """설정 파일 저장"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            logger.info(f"설정 저장 완료: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"설정 저장 오류: {e}")
            return False
    
    def get_all(self):
        """모든 설정 반환"""
        return self.data.copy()
    
    def get_path(self, key):
        """경로 설정 가져오기"""
        return self.data['paths'].get(key)