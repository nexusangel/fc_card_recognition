# core/__init__.py - FC 온라인 선수 카드 인식 시스템 코어 패키지 초기화

"""
FC 온라인 선수 카드 인식 시스템의 핵심 기능을 제공하는 코어 패키지

이 패키지는 다음과 같은 모듈을 포함합니다:
- system: 시스템 전체 관리 및 초기화
- image_processor: 이미지 처리 및 카드 감지
- recognizer: 텍스트 및 객체 인식
- model_trainer: 딥러닝 모델 학습 및 관리
"""

import os
import logging
import tensorflow as tf
from pathlib import Path

# 로거 설정
logger = logging.getLogger("FC_Online_Recognition.core")

# 버전 정보
__version__ = "2.0.0"

# 코어 모듈 임포트
from .system import SystemManager
from .image_processor import ImageProcessor
from .recognizer import RecognitionEngine
from .model_trainer import ModelTrainer

# GPU 설정 초기화
def configure_gpu():
    """GPU 메모리 설정 초기화"""
    try:
        # GPU 메모리 증가 허용
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            logger.info(f"GPU 설정 완료: {len(gpus)}개 GPU 감지됨")
            return True
        else:
            logger.info("GPU가 감지되지 않았습니다. CPU를 사용합니다.")
            return False
    except Exception as e:
        logger.warning(f"GPU 설정 중 오류 발생: {e}")
        logger.info("CPU를 사용합니다.")
        return False

# 기본 경로 설정
def get_base_dirs():
    """기본 디렉토리 설정 및 생성"""
    base_dir = os.path.join(str(Path.home()), "fc_online_data")
    
    # 필수 디렉토리 구조
    directories = {
        'base': base_dir,
        'captures': os.path.join(base_dir, "captures"),
        'models': os.path.join(base_dir, "models"),
        'training_data': os.path.join(base_dir, "training_data"),
        'debug': os.path.join(base_dir, "debug"),
        'backup': os.path.join(base_dir, "backups"),
    }
    
    # 디렉토리 생성
    for dir_path in directories.values():
        os.makedirs(dir_path, exist_ok=True)
    
    return directories

# 시스템 초기화
def initialize_system():
    """시스템 초기화"""
    try:
        # GPU 설정
        gpu_available = configure_gpu()
        
        # 기본 디렉토리 설정
        directories = get_base_dirs()
        
        # TensorFlow 로그 레벨 설정
        tf.get_logger().setLevel('ERROR')
        
        # 환경 설정
        os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
        
        # 초기화 성공
        logger.info("FC 온라인 선수 카드 인식 시스템 코어 패키지 초기화 완료")
        logger.info(f"TensorFlow 버전: {tf.__version__}")
        logger.info(f"GPU 사용 가능: {gpu_available}")
        
        return {
            'success': True,
            'gpu_available': gpu_available,
            'directories': directories,
            'version': __version__
        }
    except Exception as e:
        logger.error(f"시스템 초기화 오류: {e}")
        return {
            'success': False,
            'error': str(e)
        }

# 모듈 초기화 시 시스템 초기화 실행
system_info = initialize_system()

__all__ = [
    'SystemManager',
    'ImageProcessor',
    'RecognitionEngine',
    'ModelTrainer',
    'system_info',
    'get_base_dirs',
    'configure_gpu'
]