# core/system.py - FC 온라인 선수 카드 인식 시스템 관리 모듈

import os
import logging
import configparser
import json
import shutil
import tensorflow as tf
import cv2
import numpy as np
import pytesseract
from datetime import datetime, timedelta
from pathlib import Path

# 로거 설정
logger = logging.getLogger("FC_Online_Recognition.core.system")

class SystemManager:
    """FC 온라인 선수 카드 인식 시스템 관리 클래스"""
    
    def __init__(self, base_dir=None):
        """
        시스템 관리자 초기화
        
        Args:
            base_dir: 기본 디렉토리 경로 (기본값: ~/fc_online_data)
        """
        # 기본 경로 설정
        if base_dir is None:
            self.base_dir = os.path.join(str(Path.home()), "fc_online_data")
        else:
            self.base_dir = base_dir
            
        # 필수 디렉토리 설정
        self.captures_dir = os.path.join(self.base_dir, "captures")
        self.models_dir = os.path.join(self.base_dir, "models")
        self.training_data_dir = os.path.join(self.base_dir, "training_data")
        self.debug_dir = os.path.join(self.base_dir, "debug")
        self.backup_dir = os.path.join(self.base_dir, "backups")
        
        # 설정 파일 경로
        self.config_path = os.path.join(self.base_dir, "config.ini")
        self.roi_config_path = os.path.join(self.base_dir, "roi_config.json")
        self.roi_presets_path = os.path.join(self.base_dir, "roi_presets.json")
        self.player_dict_path = os.path.join(self.base_dir, "player_names.json")
        
        # 디렉토리 생성
        self._ensure_directories()
        
        # 설정 로드
        self.config = self._load_config()
        
        # Tesseract 경로 설정
        self._setup_tesseract()
        
        # 상태 변수
        self.initialized = False
        self.training_stats = self._load_training_stats()
        self.player_name_dict = self._load_player_name_dict()
        
        # 시스템 초기화 완료
        self.initialized = True
        logger.info("시스템 관리자 초기화 완료")
    
    def _ensure_directories(self):
        """필수 디렉토리 생성"""
        try:
            for dir_path in [self.base_dir, self.captures_dir, self.models_dir, 
                            self.training_data_dir, self.debug_dir, self.backup_dir]:
                os.makedirs(dir_path, exist_ok=True)
            
            # 학습 데이터 하위 디렉토리 생성
            for field in ['overall', 'position', 'salary', 'enhance_level', 'season_icon', 'boost_level']:
                field_dir = os.path.join(self.training_data_dir, field)
                os.makedirs(field_dir, exist_ok=True)
                
            logger.info("필수 디렉토리 확인 완료")
            return True
        except Exception as e:
            logger.error(f"디렉토리 생성 오류: {e}")
            return False
    
    def _load_config(self):
        """설정 파일 로드 (개선됨)"""
        config = configparser.ConfigParser()
        
        # 기본 설정
        default_settings = {
            'Settings': {
                'tesseract_path': self._get_default_tesseract_path(),
                'auto_learning': 'True',
                'capture_interval': '1.0',
                'auto_save_corrections': 'True',
                'ui_scale': '1.2',
                'confidence_threshold': '0.7',
                'use_manual_roi': 'True',
                'debug_mode': 'True',
                'enable_caching': 'True',
                'auto_backup': 'True',
                'theme': 'system'
            },
            'Paths': {
                'captures_dir': self.captures_dir,
                'models_dir': self.models_dir,
                'training_data_dir': self.training_data_dir,
                'backup_dir': self.backup_dir
            },
            'Batch': {
                'max_batch_size': '50',
                'parallel_jobs': '4'
            }
        }
        
        # 설정 파일이 없으면 기본 설정으로 생성
        if not os.path.exists(self.config_path):
            # 기본 설정 적용
            for section, options in default_settings.items():
                if section not in config:
                    config[section] = {}
                for option, value in options.items():
                    config[section][option] = value
            
            # 설정 파일 저장
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            logger.info(f"기본 설정 파일 생성됨: {self.config_path}")
        else:
            # 기존 설정 파일 로드
            config.read(self.config_path, encoding='utf-8')
            
            # 누락된 설정 추가
            for section, options in default_settings.items():
                if section not in config:
                    config[section] = {}
                for option, value in options.items():
                    if option not in config[section]:
                        config[section][option] = value
            
            # 업데이트된 설정 저장
            with open(self.config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            logger.info(f"설정 파일 로드됨: {self.config_path}")
            
            # 경로 업데이트
            paths = config['Paths']
            self.captures_dir = paths.get('captures_dir', self.captures_dir)
            self.models_dir = paths.get('models_dir', self.models_dir)
            self.training_data_dir = paths.get('training_data_dir', self.training_data_dir)
            self.backup_dir = paths.get('backup_dir', self.backup_dir)
        
        return config
    
    def _get_default_tesseract_path(self):
        """시스템에 맞는 기본 Tesseract 경로 반환"""
        if os.name == 'nt':  # Windows
            default_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            
            # 다른 일반적인 경로 확인
            alternate_paths = [
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'C:\Tesseract-OCR\tesseract.exe'
            ]
            
            for path in alternate_paths:
                if os.path.exists(path):
                    return path
            
            return default_path
        else:  # Linux/Mac
            default_path = '/usr/bin/tesseract'
            
            # 다른 일반적인 경로 확인
            alternate_paths = [
                '/usr/local/bin/tesseract',
                '/opt/local/bin/tesseract'
            ]
            
            for path in alternate_paths:
                if os.path.exists(path):
                    return path
            
            return default_path
    
    def _setup_tesseract(self):
        """Tesseract OCR 엔진 설정"""
        try:
            # 설정에서 Tesseract 경로 가져오기
            tesseract_path = self.config.get('Settings', 'tesseract_path', fallback=self._get_default_tesseract_path())
            
            # 경로 존재 확인
            if not os.path.exists(tesseract_path):
                logger.warning(f"Tesseract 경로를 찾을 수 없습니다: {tesseract_path}")
                tesseract_path = self._get_default_tesseract_path()
                logger.info(f"기본 Tesseract 경로 사용: {tesseract_path}")
            
            # Tesseract 경로 설정
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            # 설정 업데이트
            self.config['Settings']['tesseract_path'] = tesseract_path
            
            # Tesseract 버전 확인
            try:
                version = pytesseract.get_tesseract_version()
                logger.info(f"Tesseract 버전: {version}")
                return True
            except Exception as e:
                logger.warning(f"Tesseract 버전 확인 오류: {e}")
                return False
        except Exception as e:
            logger.error(f"Tesseract 설정 오류: {e}")
            return False
    
    def save_config(self):
        """설정 파일 저장"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
            
            logger.info(f"설정 파일 저장됨: {self.config_path}")
            
            # 자동 백업 활성화 시 백업 생성
            if self.config.getboolean('Settings', 'auto_backup', fallback=True):
                self._backup_config()
            
            return True
        except Exception as e:
            logger.error(f"설정 저장 오류: {e}")
            return False
    
    def _backup_config(self):
        """설정 파일 백업 생성"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"config_{timestamp}.ini")
            
            shutil.copy2(self.config_path, backup_path)
            logger.info(f"설정 백업 완료: {backup_path}")
            
            # 오래된 백업 정리
            self._cleanup_old_backups("config_", 10)
            
            return True
        except Exception as e:
            logger.error(f"설정 백업 오류: {e}")
            return False
    
    def _cleanup_old_backups(self, prefix, max_keep=10):
        """오래된 백업 파일 정리"""
        try:
            backup_files = [f for f in os.listdir(self.backup_dir) 
                          if f.startswith(prefix) and f.endswith(".ini") or f.endswith(".json")]
            
            if len(backup_files) > max_keep:
                # 날짜 기준 정렬
                backup_files.sort(reverse=True)
                
                # 오래된 파일 삭제
                for old_file in backup_files[max_keep:]:
                    os.remove(os.path.join(self.backup_dir, old_file))
                    logger.info(f"오래된 백업 파일 삭제: {old_file}")
            
            return True
        except Exception as e:
            logger.error(f"백업 파일 정리 오류: {e}")
            return False
    
    def _load_training_stats(self):
        """학습 통계 로드"""
        stats_path = os.path.join(self.base_dir, "training_stats.json")
        
        # 기본 통계 데이터
        default_stats = {
            'overall': {'samples': 0, 'accuracy': 0.0, 'last_trained': '없음', 'classes': 0},
            'position': {'samples': 0, 'accuracy': 0.0, 'last_trained': '없음', 'classes': 0},
            'salary': {'samples': 0, 'accuracy': 0.0, 'last_trained': '없음', 'classes': 0},
            'enhance_level': {'samples': 0, 'accuracy': 0.0, 'last_trained': '없음', 'classes': 0},
            'season_icon': {'samples': 0, 'accuracy': 0.0, 'last_trained': '없음', 'classes': 0},
            'boost_level': {'samples': 0, 'accuracy': 0.0, 'last_trained': '없음', 'classes': 0}
        }
        
        try:
            if os.path.exists(stats_path):
                with open(stats_path, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                
                # 누락된 필드 추가
                for field in default_stats:
                    if field not in stats:
                        stats[field] = default_stats[field]
                
                logger.info("학습 통계 로드 완료")
                return stats
            else:
                logger.info("학습 통계 파일이 없습니다. 기본값 사용.")
                return default_stats
        except Exception as e:
            logger.error(f"학습 통계 로드 오류: {e}")
            return default_stats
    
    def save_training_stats(self, stats=None):
        """학습 통계 저장"""
        if stats is None:
            stats = self.training_stats
        
        stats_path = os.path.join(self.base_dir, "training_stats.json")
        
        try:
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
            
            logger.info("학습 통계 저장 완료")
            return True
        except Exception as e:
            logger.error(f"학습 통계 저장 오류: {e}")
            return False
    
    def _load_player_name_dict(self):
        """선수 이름 사전 로드"""
        try:
            if os.path.exists(self.player_dict_path):
                with open(self.player_dict_path, 'r', encoding='utf-8') as f:
                    name_dict = json.load(f)
                    logger.info(f"선수 이름 사전 로드 완료: {len(name_dict)}개 항목")
                    return name_dict
        except Exception as e:
            logger.error(f"선수 이름 사전 로드 오류: {e}")
        
        # 기본 빈 사전 반환
        return {}
    
    def save_player_name_dict(self, player_dict=None):
        """선수 이름 사전 저장"""
        if player_dict is None:
            player_dict = self.player_name_dict
        
        try:
            with open(self.player_dict_path, 'w', encoding='utf-8') as f:
                json.dump(player_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"선수 이름 사전 저장 완료: {len(player_dict)}개 항목")
            
            # 자동 백업 활성화 시 백업 생성
            if self.config.getboolean('Settings', 'auto_backup', fallback=True):
                self._backup_player_dict()
            
            return True
        except Exception as e:
            logger.error(f"선수 이름 사전 저장 오류: {e}")
            return False
    
    def _backup_player_dict(self):
        """선수 이름 사전 백업"""
        try:
            if os.path.exists(self.player_dict_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(self.backup_dir, f"player_names_{timestamp}.json")
                
                shutil.copy2(self.player_dict_path, backup_path)
                logger.info(f"선수 이름 사전 백업 완료: {backup_path}")
                
                # 오래된 백업 정리
                self._cleanup_old_backups("player_names_", 5)
            
            return True
        except Exception as e:
            logger.error(f"선수 이름 사전 백업 오류: {e}")
            return False
    
    def update_player_name_dict(self, original_name, corrected_name):
        """선수 이름 사전 업데이트"""
        if not original_name or not corrected_name or original_name == corrected_name:
            return False
        
        # 원본 이름에서 공백 제거
        no_space_original = original_name.replace(" ", "")
        
        # 사전 업데이트
        self.player_name_dict[no_space_original] = corrected_name
        
        # 사전 저장
        return self.save_player_name_dict()
    
    def backup_now(self):
        """수동 백업 실행"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(self.backup_dir, f"manual_backup_{timestamp}")
            os.makedirs(backup_dir, exist_ok=True)
            
            # 설정 파일 백업
            if os.path.exists(self.config_path):
                shutil.copy2(self.config_path, os.path.join(backup_dir, "config.ini"))
            
            # ROI 설정 백업
            if os.path.exists(self.roi_config_path):
                shutil.copy2(self.roi_config_path, os.path.join(backup_dir, os.path.basename(self.roi_config_path)))
            
            # ROI 프리셋 백업
            if os.path.exists(self.roi_presets_path):
                shutil.copy2(self.roi_presets_path, os.path.join(backup_dir, os.path.basename(self.roi_presets_path)))
            
            # 선수 이름 사전 백업
            if os.path.exists(self.player_dict_path):
                shutil.copy2(self.player_dict_path, os.path.join(backup_dir, "player_names.json"))
            
            # 모델 파일 백업
            model_backup_dir = os.path.join(backup_dir, "models")
            os.makedirs(model_backup_dir, exist_ok=True)
            
            model_files = [f for f in os.listdir(self.models_dir) if f.endswith('.h5')]
            for model_file in model_files:
                shutil.copy2(os.path.join(self.models_dir, model_file), os.path.join(model_backup_dir, model_file))
            
            # 학습 통계 백업
            stats_path = os.path.join(self.base_dir, "training_stats.json")
            if os.path.exists(stats_path):
                shutil.copy2(stats_path, os.path.join(backup_dir, "training_stats.json"))
            
            # 백업 정보 파일 생성
            with open(os.path.join(backup_dir, "backup_info.txt"), 'w', encoding='utf-8') as f:
                f.write(f"백업 생성 시간: {timestamp}\n")
                f.write(f"백업 유형: 수동 백업\n")
                f.write(f"설정 파일: {'O' if os.path.exists(self.config_path) else 'X'}\n")
                f.write(f"ROI 설정: {'O' if os.path.exists(self.roi_config_path) else 'X'}\n")
                f.write(f"ROI 프리셋: {'O' if os.path.exists(self.roi_presets_path) else 'X'}\n")
                f.write(f"선수 이름 사전: {'O' if os.path.exists(self.player_dict_path) else 'X'}\n")
                f.write(f"모델 파일: {len(model_files)}개\n")
            
            logger.info(f"수동 백업 완료: {backup_dir}")
            return {
                'success': True,
                'backup_dir': backup_dir,
                'timestamp': timestamp
            }
        except Exception as e:
            logger.error(f"수동 백업 오류: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def schedule_auto_backup(self, initial_delay=1800000):
        """자동 백업 스케줄러 설정 (ms 단위 지연)"""
        if self.config.getboolean('Settings', 'auto_backup', fallback=True):
            # 다음 자동 백업 시간 저장
            next_backup_time = datetime.now() + timedelta(milliseconds=initial_delay)
            self.next_backup_time = next_backup_time
            
            logger.info(f"자동 백업 예약됨: {next_backup_time}")
            return True
        else:
            logger.info("자동 백업이 비활성화되어 있습니다.")
            return False
    
    def check_auto_backup(self):
        """자동 백업 시간 확인 및 실행"""
        if not hasattr(self, 'next_backup_time'):
            # 초기 자동 백업 설정
            return self.schedule_auto_backup()
        
        if datetime.now() >= self.next_backup_time:
            logger.info("자동 백업 실행 중...")
            
            # 백업 실행
            result = self.backup_now()
            
            # 다음 백업 스케줄링 (6시간 = 21600000ms)
            self.schedule_auto_backup(21600000)
            
            return result
        
        return None
    
    def get_backup_list(self):
        """백업 목록 가져오기"""
        try:
            # 백업 디렉토리 확인
            if not os.path.exists(self.backup_dir):
                return []
            
            # 백업 디렉토리 목록
            backup_dirs = []
            
            for item in os.listdir(self.backup_dir):
                item_path = os.path.join(self.backup_dir, item)
                
                # 디렉토리만 처리
                if not os.path.isdir(item_path):
                    continue
                
                # 백업 정보 파일 확인
                info_path = os.path.join(item_path, "backup_info.txt")
                info = {}
                
                if os.path.exists(info_path):
                    with open(info_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if ':' in line:
                                key, value = line.strip().split(':', 1)
                                info[key.strip()] = value.strip()
                
                # 백업 크기 계산
                size = 0
                for dirpath, dirnames, filenames in os.walk(item_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        size += os.path.getsize(fp)
                
                # 백업 정보 추가
                backup_dirs.append({
                    'name': item,
                    'path': item_path,
                    'size': size,
                    'size_mb': size / (1024 * 1024),
                    'date': info.get('백업 생성 시간', '알 수 없음'),
                    'type': info.get('백업 유형', '알 수 없음'),
                    'info': info
                })
            
            # 날짜순 정렬 (최신순)
            backup_dirs.sort(key=lambda x: x['name'], reverse=True)
            
            return backup_dirs
        except Exception as e:
            logger.error(f"백업 목록 가져오기 오류: {e}")
            return []
    
    def restore_from_backup(self, backup_dir, options=None):
        """백업에서 복원"""
        if not backup_dir or not os.path.exists(backup_dir):
            logger.error(f"백업 디렉토리가 존재하지 않습니다: {backup_dir}")
            return {
                'success': False,
                'error': '백업 디렉토리가 존재하지 않습니다.'
            }
        
        # 복원 옵션 기본값
        if options is None:
            options = {
                'config': True,
                'roi': True,
                'presets': True,
                'player_dict': True,
                'models': True,
                'stats': True
            }
        
        try:
            # 현재 설정 백업 (복원 전)
            self.backup_now()
            
            # 복원 시작
            restored_items = []
            
            # 설정 파일 복원
            if options.get('config', True) and os.path.exists(os.path.join(backup_dir, "config.ini")):
                shutil.copy2(os.path.join(backup_dir, "config.ini"), self.config_path)
                restored_items.append('설정 파일')
                
                # 설정 다시 로드
                self.config = self._load_config()
            
            # ROI 설정 복원
            roi_filename = os.path.basename(self.roi_config_path)
            if options.get('roi', True) and os.path.exists(os.path.join(backup_dir, roi_filename)):
                shutil.copy2(os.path.join(backup_dir, roi_filename), self.roi_config_path)
                restored_items.append('ROI 설정')
            
            # ROI 프리셋 복원
            presets_filename = os.path.basename(self.roi_presets_path)
            if options.get('presets', True) and os.path.exists(os.path.join(backup_dir, presets_filename)):
                shutil.copy2(os.path.join(backup_dir, presets_filename), self.roi_presets_path)
                restored_items.append('ROI 프리셋')
            
            # 선수 이름 사전 복원
            if options.get('player_dict', True) and os.path.exists(os.path.join(backup_dir, "player_names.json")):
                shutil.copy2(os.path.join(backup_dir, "player_names.json"), self.player_dict_path)
                restored_items.append('선수 이름 사전')
                
                # 선수 이름 사전 다시 로드
                self.player_name_dict = self._load_player_name_dict()
            
            # 모델 파일 복원
            if options.get('models', True) and os.path.exists(os.path.join(backup_dir, "models")):
                # 모델 디렉토리의 모든 파일 복원
                model_files = [f for f in os.listdir(os.path.join(backup_dir, "models")) if f.endswith('.h5')]
                
                for model_file in model_files:
                    src = os.path.join(backup_dir, "models", model_file)
                    dst = os.path.join(self.models_dir, model_file)
                    shutil.copy2(src, dst)
                
                restored_items.append(f'모델 파일 ({len(model_files)}개)')
            
            # 학습 통계 복원
            if options.get('stats', True) and os.path.exists(os.path.join(backup_dir, "training_stats.json")):
                shutil.copy2(os.path.join(backup_dir, "training_stats.json"), 
                           os.path.join(self.base_dir, "training_stats.json"))
                restored_items.append('학습 통계')
                
                # 학습 통계 다시 로드
                self.training_stats = self._load_training_stats()
            
            logger.info(f"백업 복원 완료: {backup_dir}")
            return {
                'success': True,
                'restored_items': restored_items,
                'backup_dir': backup_dir
            }
        except Exception as e:
            logger.error(f"백업 복원 오류: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_backup(self, backup_dir):
        """백업 삭제"""
        if not backup_dir or not os.path.exists(backup_dir):
            logger.error(f"백업 디렉토리가 존재하지 않습니다: {backup_dir}")
            return False
        
        try:
            # 백업 디렉토리 삭제
            shutil.rmtree(backup_dir)
            logger.info(f"백업 삭제 완료: {backup_dir}")
            return True
        except Exception as e:
            logger.error(f"백업 삭제 오류: {e}")
            return False
    
    def get_memory_usage(self):
        """현재 메모리 사용량 조회"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                'rss': memory_info.rss,  # 실제 메모리 사용량
                'rss_mb': memory_info.rss / (1024 * 1024),  # MB 단위
                'vms': memory_info.vms,  # 가상 메모리 사용량
                'vms_mb': memory_info.vms / (1024 * 1024)  # MB 단위
            }
        except Exception as e:
            logger.error(f"메모리 사용량 조회 오류: {e}")
            return None
    
    def clean_memory(self):
        """메모리 정리"""
        try:
            # 가비지 컬렉션 강제 실행
            import gc
            gc.collect()
            
            # TensorFlow 메모리 정리
            tf.keras.backend.clear_session()
            
            logger.info("메모리 정리 완료")
            return True
        except Exception as e:
            logger.error(f"메모리 정리 오류: {e}")
            return False
    
    def get_system_info(self):
        """시스템 정보 조회"""
        try:
            import platform
            
            # GPU 정보
            gpus = tf.config.list_physical_devices('GPU')
            gpu_info = []
            
            if gpus:
                for i, gpu in enumerate(gpus):
                    gpu_info.append({
                        'index': i,
                        'name': gpu.name
                    })
            
            # 메모리 사용량
            memory_usage = self.get_memory_usage()
            
            # 시스템 정보
            return {
                'platform': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'tensorflow_version': tf.__version__,
                'opencv_version': cv2.__version__,
                'numpy_version': np.__version__,
                'gpu_available': len(gpus) > 0,
                'gpu_count': len(gpus),
                'gpu_info': gpu_info,
                'memory_usage': memory_usage
            }
        except Exception as e:
            logger.error(f"시스템 정보 조회 오류: {e}")
            return {
                'error': str(e)
            }