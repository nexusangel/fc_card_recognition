# fc_card_recognition/utils/backup_manager.py
import os
import json
import shutil
import logging
from datetime import datetime

logger = logging.getLogger("FC_Online_Recognition")

class BackupManager:
    """시스템 백업 및 복원 관리 클래스"""
    def __init__(self, config):
        """초기화"""
        self.config = config
        self.base_dir = config.get_path('base_dir')
        self.backup_dir = config.get_path('backup_dir')
        self.models_dir = config.get_path('models_dir')
        
        # 백업 디렉토리 생성
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_backup(self, backup_type="자동"):
        """시스템 백업 생성"""
        try:
            # 백업 ID 생성 (타임스탬프)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_id = f"backup_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_id)
            
            # 백업 디렉토리 생성
            os.makedirs(backup_path, exist_ok=True)
            
            # 설정 파일 백업
            config_files = {
                "config.json": os.path.join(self.base_dir, "config.json"),
                "roi_config.json": os.path.join(self.base_dir, "roi_config.json"),
                "roi_presets.json": os.path.join(self.base_dir, "roi_presets.json"),
                "player_names.json": os.path.join(self.base_dir, "player_names.json"),
                "training_stats.json": os.path.join(self.base_dir, "training_stats.json")
            }
            
            for backup_name, original_path in config_files.items():
                if os.path.exists(original_path):
                    shutil.copy2(original_path, os.path.join(backup_path, backup_name))
            
            # 모델 백업
            models_backup_dir = os.path.join(backup_path, "models")
            os.makedirs(models_backup_dir, exist_ok=True)
            
            if os.path.exists(self.models_dir):
                model_files = [f for f in os.listdir(self.models_dir) if f.endswith('.h5')]
                for model_file in model_files:
                    shutil.copy2(
                        os.path.join(self.models_dir, model_file),
                        os.path.join(models_backup_dir, model_file)
                    )
            
            # 백업 정보 파일 생성
            backup_info = {
                "id": backup_id,
                "timestamp": timestamp,
                "type": backup_type,
                "configs": [f for f in config_files.keys() if os.path.exists(config_files[f])],
                "models": model_files if 'model_files' in locals() else []
            }
            
            with open(os.path.join(backup_path, "backup_info.json"), 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            # 오래된 백업 정리 (30개 이상)
            self._cleanup_old_backups(30)
            
            logger.info(f"백업 생성 완료: {backup_id}")
            return backup_id
            
        except Exception as e:
            logger.error(f"백업 생성 오류: {e}")
            return None
    
    def restore_backup(self, backup_id):
        """백업에서 시스템 복원"""
        try:
            # 백업 경로 확인
            backup_path = os.path.join(self.backup_dir, backup_id)
            if not os.path.exists(backup_path):
                logger.error(f"백업을 찾을 수 없습니다: {backup_id}")
                return False
            
            # 백업 정보 확인
            info_path = os.path.join(backup_path, "backup_info.json")
            if not os.path.exists(info_path):
                logger.error(f"백업 정보 파일이 없습니다: {backup_id}")
                return False
            
            # 복원 전 현재 설정 백업
            self.create_backup(backup_type="복원 전")
            
            # 설정 파일 복원
            config_files = {
                "config.json": os.path.join(self.base_dir, "config.json"),
                "roi_config.json": os.path.join(self.base_dir, "roi_config.json"),
                "roi_presets.json": os.path.join(self.base_dir, "roi_presets.json"),
                "player_names.json": os.path.join(self.base_dir, "player_names.json"),
                "training_stats.json": os.path.join(self.base_dir, "training_stats.json")
            }
            
            for backup_name, target_path in config_files.items():
                source_path = os.path.join(backup_path, backup_name)
                if os.path.exists(source_path):
                    shutil.copy2(source_path, target_path)
            
            # 모델 복원
            models_backup_dir = os.path.join(backup_path, "models")
            if os.path.exists(models_backup_dir):
                os.makedirs(self.models_dir, exist_ok=True)
                
                model_files = [f for f in os.listdir(models_backup_dir) if f.endswith('.h5')]
                for model_file in model_files:
                    shutil.copy2(
                        os.path.join(models_backup_dir, model_file),
                        os.path.join(self.models_dir, model_file)
                    )
            
            logger.info(f"백업 복원 완료: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"백업 복원 오류: {e}")
            return False
    
    def get_backups(self):
        """사용 가능한 백업 목록 반환"""
        try:
            backups = []
            
            # 백업 디렉토리 확인
            if not os.path.exists(self.backup_dir):
                return []
            
            # 백업 디렉토리 목록
            for item in os.listdir(self.backup_dir):
                item_path = os.path.join(self.backup_dir, item)
                
                # 디렉토리만 처리
                if not os.path.isdir(item_path):
                    continue
                
                # 백업 정보 파일 확인
                info_path = os.path.join(item_path, "backup_info.json")
                if os.path.exists(info_path):
                    try:
                        with open(info_path, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                            backups.append(info)
                    except:
                        # 정보 파일이 손상된 경우 기본 정보 추가
                        backups.append({
                            "id": item,
                            "timestamp": os.path.getctime(item_path),
                            "type": "알 수 없음",
                            "configs": [],
                            "models": []
                        })
                else:
                    # 정보 파일이 없는 경우 기본 정보 추가
                    backups.append({
                        "id": item,
                        "timestamp": os.path.getctime(item_path),
                        "type": "알 수 없음",
                        "configs": [],
                        "models": []
                    })
            
            # 최신순 정렬
            backups.sort(key=lambda x: x["timestamp"] if isinstance(x["timestamp"], str) else "", reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"백업 목록 조회 오류: {e}")
            return []
    
    def delete_backup(self, backup_id):
        """백업 삭제"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_id)
            if not os.path.exists(backup_path):
                logger.error(f"백업을 찾을 수 없습니다: {backup_id}")
                return False
            
            # 백업 삭제
            shutil.rmtree(backup_path)
            
            logger.info(f"백업 삭제 완료: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"백업 삭제 오류: {e}")
            return False
    
    def _cleanup_old_backups(self, max_backups=30):
        """오래된 백업 정리"""
        try:
            # 백업 목록
            backups = self.get_backups()
            
            # 최대 개수 초과 시 오래된 것부터 삭제
            if len(backups) > max_backups:
                for backup in backups[max_backups:]:
                    self.delete_backup(backup["id"])
                
                logger.info(f"오래된 백업 정리 완료: {len(backups) - max_backups}개 삭제됨")
            
            return True
            
        except Exception as e:
            logger.error(f"백업 정리 오류: {e}")
            return False