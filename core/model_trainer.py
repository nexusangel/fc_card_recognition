# fc_card_recognition/core/model_trainer.py
import os
import json
import logging
import shutil
import cv2
import numpy as np
from datetime import datetime

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, load_model, save_model
    from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, GlobalAveragePooling2D
    from tensorflow.keras.applications import EfficientNetB0
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau, Callback
except ImportError:
    tf = None

logger = logging.getLogger("FC_Online_Recognition")

class ModelTrainer:
    """모델 학습 클래스"""
    def __init__(self, config):
        """초기화"""
        self.config = config
        self.models_dir = config.get_path('models_dir')
        self.training_data_dir = config.get_path('training_data_dir')
        self.debug_dir = config.get_path('debug_dir')
        self.backup_dir = config.get_path('backup_dir')
        
        # 학습 통계 로드
        self.training_stats = self._load_training_stats()
        
        # 학습 취소 플래그
        self.training_canceled = False
    
    def _load_training_stats(self):
        """학습 통계 로드"""
        stats_path = os.path.join(self.config.get_path('base_dir'), "training_stats.json")
        
        try:
            if os.path.exists(stats_path):
                with open(stats_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 기본 통계 생성
                default_stats = {}
                for field in ['overall', 'position', 'salary', 'enhance_level', 'season_icon']:
                    default_stats[field] = {
                        'samples': 0,
                        'accuracy': 0.0,
                        'last_trained': '없음',
                        'classes': 0
                    }
                
                # 저장
                with open(stats_path, 'w', encoding='utf-8') as f:
                    json.dump(default_stats, f, indent=2, ensure_ascii=False)
                
                return default_stats
        except Exception as e:
            logger.error(f"학습 통계 로드 오류: {e}")
            
            # 기본 통계 반환
            default_stats = {}
            for field in ['overall', 'position', 'salary', 'enhance_level', 'season_icon']:
                default_stats[field] = {
                    'samples': 0,
                    'accuracy': 0.0,
                    'last_trained': '없음',
                    'classes': 0
                }
            
            return default_stats
    
    def _save_training_stats(self):
        """학습 통계 저장"""
        stats_path = os.path.join(self.config.get_path('base_dir'), "training_stats.json")
        
        try:
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(self.training_stats, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"학습 통계 저장 오류: {e}")
            return False
    
    def get_stats(self):
        """모델 통계 정보 반환"""
        return self.training_stats.copy()
    
    def save_training_data(self, image_path, rois, corrections):
        """수정된 인식 결과로 학습 데이터 저장"""
        try:
            # 파일명 추출
            file_name = os.path.basename(image_path)
            
            # 각 필드별 처리
            for field, value in corrections.items():
                if field not in rois:
                    continue
                
                # 학습 데이터 디렉토리 생성
                train_dir = os.path.join(self.training_data_dir, field, value)
                os.makedirs(train_dir, exist_ok=True)
                
                # 이미지 저장
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                save_path = os.path.join(train_dir, f"{file_name}_{timestamp}.jpg")
                cv2.imwrite(save_path, rois[field])
                logger.info(f"학습 데이터 저장: {save_path}")
                
                # 데이터 증강을 통한 추가 학습 데이터 생성
                roi = rois[field]
                
                # 이미지 크기 확인
                if roi.shape[0] > 10 and roi.shape[1] > 10:
                    # 약간의 회전
                    for angle in [5, -5, 10, -10]:
                        h, w = roi.shape[:2]
                        center = (w // 2, h // 2)
                        M = cv2.getRotationMatrix2D(center, angle, 1.0)
                        rotated = cv2.warpAffine(roi, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
                        
                        aug_path = os.path.join(train_dir, f"{file_name}_rot{angle}_{timestamp}.jpg")
                        cv2.imwrite(aug_path, rotated)
                    
                    # 밝기 조정
                    for beta in [20, -20]:
                        brightness = cv2.convertScaleAbs(roi, alpha=1, beta=beta)
                        aug_path = os.path.join(train_dir, f"{file_name}_bright{beta}_{timestamp}.jpg")
                        cv2.imwrite(aug_path, brightness)
            
            return True
        except Exception as e:
            logger.error(f"학습 데이터 저장 오류: {e}")
            return False
    
    def train(self, field, progress_callback=None):
        """모델 학습 실행"""
        # TensorFlow 사용 가능 여부 확인
        if tf is None:
            return False, "TensorFlow 라이브러리가 설치되지 않았습니다."
        
        try:
            # 학습 취소 플래그 초기화
            self.training_canceled = False
            
            # 학습 데이터 디렉토리 확인
            train_dir = os.path.join(self.training_data_dir, field)
            
            if not os.path.exists(train_dir):
                os.makedirs(train_dir, exist_ok=True)
                return False, f"{field} 모델 학습 폴더가 없습니다. 폴더를 생성했으니 이미지를 추가하세요."
            
            # 클래스 확인
            classes = [d for d in os.listdir(train_dir) if os.path.isdir(os.path.join(train_dir, d))]
            num_classes = len(classes)
            
            # 최소 2개 클래스 필요
            if num_classes < 2:
                return False, f"{field} 모델 학습 실패: 클래스가 2개 이상 필요합니다 (현재: {num_classes}개)."
            
            # 데이터셋 유효성 확인 및 정제
            class_counts = []
            valid_classes = []
            total_images = 0
            
            for class_name in classes:
                class_path = os.path.join(train_dir, class_name)
                image_files = [f for f in os.listdir(class_path) 
                              if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
                
                # 유효한 이미지만 카운트
                valid_images = 0
                for img_file in image_files:
                    img_path = os.path.join(class_path, img_file)
                    try:
                        img = cv2.imread(img_path)
                        if img is not None and img.size > 0:
                            valid_images += 1
                    except:
                        pass
                
                total_images += valid_images
                class_counts.append((class_name, valid_images))
                
                if valid_images > 0:
                    valid_classes.append(class_name)
            
            # 유효한 클래스 확인
            if len(valid_classes) < 2:
                return False, f"{field} 모델 학습 실패: 이미지가 있는 클래스가 2개 이상 필요합니다 (현재: {len(valid_classes)}개)."
            
            # 이미지 총 개수 확인
            if total_images < 10:
                return False, f"{field} 모델 학습 실패: 이미지가 너무 적습니다 (현재: {total_images}개). 최소 10개 이상 권장."
            
            # 진행 상태 업데이트
            if progress_callback:
                progress_callback(5, f"데이터 검증 완료: {total_images}개 이미지, {len(valid_classes)}개 클래스")
            
            # 데이터 증강 설정 (이미지 적을 때 더 강한 증강)
            if total_images < 50:
                datagen = ImageDataGenerator(
                    rescale=1./255,
                    rotation_range=15,
                    zoom_range=0.15,
                    width_shift_range=0.15,
                    height_shift_range=0.15,
                    shear_range=0.1,
                    horizontal_flip=False,
                    brightness_range=[0.8, 1.2],
                    fill_mode='nearest',
                    validation_split=0.2
                )
            else:
                datagen = ImageDataGenerator(
                    rescale=1./255,
                    rotation_range=10,
                    zoom_range=0.1,
                    width_shift_range=0.1,
                    height_shift_range=0.1,
                    shear_range=0.05,
                    horizontal_flip=False,
                    fill_mode='nearest',
                    validation_split=0.2
                )
            
            # 학습 데이터 생성
            try:
                train_generator = datagen.flow_from_directory(
                    train_dir,
                    target_size=(224, 224),
                    batch_size=8,
                    class_mode='categorical',
                    color_mode='rgb',
                    subset='training',
                    shuffle=True
                )
                
                validation_generator = datagen.flow_from_directory(
                    train_dir,
                    target_size=(224, 224),
                    batch_size=8,
                    class_mode='categorical',
                    color_mode='rgb',
                    subset='validation',
                    shuffle=True
                )
                
                # 샘플 수 확인
                if train_generator.samples == 0:
                    return False, f"{field} 모델 학습 실패: 학습 데이터가 없습니다."
                
                # 최소 검증 데이터 확인
                if validation_generator.samples == 0:
                    # 검증 데이터 생성 오류시 학습 데이터만 사용
                    validation_generator = train_generator
            
                # 진행 상태 업데이트
                if progress_callback:
                    progress_callback(10, f"데이터 로딩 완료: 학습 {train_generator.samples}개, 검증 {validation_generator.samples}개")
                
                # 이전 모델 백업
                model_path = os.path.join(self.models_dir, f"{field}_model.h5")
                if os.path.exists(model_path):
                    backup_path = os.path.join(self.models_dir, f"{field}_model_before_train.h5")
                    try:
                        shutil.copy2(model_path, backup_path)
                        logger.info(f"학습 전 모델 백업: {backup_path}")
                    except Exception as e:
                        logger.warning(f"모델 백업 실패: {e}")
                
                # 모델 생성
                inputs = tf.keras.Input(shape=(224, 224, 3))
                
                # 데이터 양에 따라 다른 기본 모델 사용
                if total_images < 50:
                    # 데이터가 적을 때는 더 작은 모델
                    base_model = tf.keras.applications.MobileNetV2(
                        weights='imagenet', 
                        include_top=False, 
                        input_shape=(224, 224, 3)
                    )
                else:
                    # 데이터가 충분할 때는 더 큰 모델
                    base_model = EfficientNetB0(
                        weights='imagenet', 
                        include_top=False, 
                        input_shape=(224, 224, 3)
                    )
                
                # 전이 학습 설정
                for layer in base_model.layers:
                    layer.trainable = False
                
                x = base_model(inputs, training=False)
                x = GlobalAveragePooling2D()(x)
                
                # 데이터 양에 따라 다른 네트워크 구성
                if total_images < 30:
                    # 데이터가 매우 적을 때는 더 단순한 네트워크
                    x = Dense(64, activation='relu')(x)
                    x = Dropout(0.3)(x)
                else:
                    # 데이터가 충분할 때
                    x = Dense(256, activation='relu')(x)
                    x = Dropout(0.5)(x)
                    x = Dense(128, activation='relu')(x)
                    x = Dropout(0.3)(x)
                
                outputs = Dense(num_classes, activation='softmax')(x)
                
                model = tf.keras.Model(inputs, outputs)
                
                # 모델 컴파일 (데이터 양에 따라 다른 학습률)
                if total_images < 30:
                    optimizer = Adam(learning_rate=0.0005)  # 더 낮은 학습률
                else:
                    optimizer = Adam(learning_rate=0.001)
                    
                model.compile(
                    optimizer=optimizer,
                    loss='categorical_crossentropy',
                    metrics=['accuracy']
                )
                
                # 진행 상태 업데이트
                if progress_callback:
                    progress_callback(15, f"모델 초기화 완료")
                
                # 콜백 설정
                checkpoint = ModelCheckpoint(
                    model_path,
                    monitor='val_accuracy',
                    save_best_only=True,
                    mode='max',
                    verbose=1
                )
                
                # 데이터 양에 따라 다른 조기 종료 설정
                if total_images < 30:
                    patience = 15  # 더 긴 인내심
                else:
                    patience = 10
                    
                early_stop = EarlyStopping(
                    monitor='val_accuracy',
                    patience=patience,
                    restore_best_weights=True,
                    mode='max',
                    verbose=1
                )
                
                reduce_lr = ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=5,
                    min_lr=0.00001,
                    verbose=1
                )
                
                # 학습 파라미터 계산
                steps_per_epoch = max(1, train_generator.samples // train_generator.batch_size)
                validation_steps = max(1, validation_generator.samples // validation_generator.batch_size)
                
                # 데이터가 적은 경우 에포크 조정
                if total_images < 30:
                    epochs = 100  # 데이터가 매우 적을 때 더 많은 에포크
                elif total_images < 100:
                    epochs = 70  # 데이터가 적을 때 더 많은 에포크
                else:
                    epochs = 50
                
                # 메모리 사용량 최적화
                tf.keras.backend.clear_session()
                
                # 진행 상태 콜백
                class ProgressCallback(Callback):
                    def __init__(self, progress_callback, epochs):
                        super().__init__()
                        self.progress_callback = progress_callback
                        self.epochs = epochs
                        self.best_acc = 0
                    
                    def on_epoch_end(self, epoch, logs=None):
                        # 취소 확인
                        if hasattr(self.model, 'stop_training') and self.model.stop_training:
                            return
                        
                        # 진행 상황 계산 (15-95%)
                        progress = 15 + ((epoch + 1) / self.epochs * 80)
                        
                        # 정확도 업데이트
                        val_acc = logs.get('val_accuracy', 0)
                        
                        # 최고 정확도 업데이트
                        if val_acc > self.best_acc:
                            self.best_acc = val_acc
                        
                        # 진행 상태 업데이트
                        if self.progress_callback:
                            self.progress_callback(
                                int(progress), 
                                f"학습 중 ({epoch+1}/{self.epochs}): 정확도={val_acc:.2%}, 최고={self.best_acc:.2%}"
                            )
                
                # 진행 상태 콜백 생성
                progress_cb = None
                if progress_callback:
                    progress_cb = ProgressCallback(progress_callback, epochs)
                    callbacks = [checkpoint, early_stop, reduce_lr, progress_cb]
                else:
                    callbacks = [checkpoint, early_stop, reduce_lr]
                
                # 학습 실행
                logger.info(f"모델 학습 시작: {field}, 클래스={num_classes}, 샘플={train_generator.samples}")
                
                history = model.fit(
                    train_generator,
                    steps_per_epoch=steps_per_epoch,
                    epochs=epochs,
                    validation_data=validation_generator,
                    validation_steps=validation_steps,
                    callbacks=callbacks,
                    verbose=0  # 콜백에서 처리하므로 출력 끔
                )
                
                # 학습 취소 확인
                if self.training_canceled:
                    logger.info(f"{field} 모델 학습이 취소되었습니다.")
                    return False, f"{field} 모델 학습이 취소되었습니다."
                
                # 모델 저장
                model.save(model_path)
                
                # 학습 통계 업데이트
                if 'val_accuracy' in history.history and len(history.history['val_accuracy']) > 0:
                    best_acc = max(history.history['val_accuracy'])
                else:
                    best_acc = 0.0
                    
                if not isinstance(self.training_stats.get(field, None), dict):
                    self.training_stats[field] = {'samples': 0, 'accuracy': 0.0, 'last_trained': '없음', 'classes': 0}
                
                self.training_stats[field]['accuracy'] = float(best_acc)
                self.training_stats[field]['last_trained'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.training_stats[field]['samples'] = train_generator.samples
                self.training_stats[field]['classes'] = num_classes
                self._save_training_stats()
                
                # 진행 상태 업데이트
                if progress_callback:
                    progress_callback(100, f"학습 완료: 정확도={best_acc:.2%}")
                
                logger.info(f"{field} 모델 학습 완료 (정확도: {best_acc:.2%})")
                
                return True, f"{field} 모델 학습이 완료되었습니다 (정확도: {best_acc:.2%})"
                
            except Exception as e:
                error_msg = f"{field} 모델 학습 중 오류: {e}"
                logger.error(error_msg)
                
                # 상세 오류 로그
                import traceback
                logger.error(traceback.format_exc())
                
                # 진행 상태 업데이트
                if progress_callback:
                    progress_callback(0, f"오류 발생: {str(e)}")
                
                return False, error_msg
                
        except Exception as e:
            error_msg = f"{field} 모델 학습 준비 중 오류: {e}"
            logger.error(error_msg)
            
            # 상세 오류 로그
            import traceback
            logger.error(traceback.format_exc())
            
            # 진행 상태 업데이트
            if progress_callback:
                progress_callback(0, f"오류 발생: {str(e)}")
            
            return False, error_msg
    
    def cancel_training(self):
        """학습 취소"""
        self.training_canceled = True
        logger.info("모델 학습 취소 요청")
        return True