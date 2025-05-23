# fc_card_recognition/core/recognizer.py
import os
import cv2
import numpy as np
import logging
import re
import json
import hashlib
from collections import Counter
import pytesseract

try:
    import tensorflow as tf
except ImportError:
    tf = None

logger = logging.getLogger("FC_Online_Recognition")

class RecognizerFactory:
    """인식기 팩토리 클래스"""
    @staticmethod
    def create(config):
        """설정에 맞는 인식기 생성"""
        # TensorFlow 사용 가능 여부 확인
        if tf is not None:
            return CombinedRecognizer(config)
        else:
            return OCRRecognizer(config)

class BaseRecognizer:
    """기본 인식기 클래스"""
    def __init__(self, config):
        """초기화"""
        self.config = config
        self.debug_mode = config.get('settings', 'debug_mode')
        self.debug_dir = config.get_path('debug_dir')
        self.base_dir = config.get_path('base_dir')
        
        # Tesseract 설정
        tesseract_path = config.get('settings', 'tesseract_path')
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # 캐싱 설정
        self.enable_caching = config.get('settings', 'enable_caching')
        self.ocr_cache = {}
        
        # 선수 이름 사전 로드
        self.player_name_dict = self._load_player_name_dict()
    
    def _load_player_name_dict(self):
        """선수 이름 사전 로드"""
        dict_path = os.path.join(self.base_dir, "player_names.json")
        try:
            if os.path.exists(dict_path):
                with open(dict_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"선수 이름 사전 로드 오류: {e}")
        return {}
    
    def _save_player_name_dict(self):
        """선수 이름 사전 저장"""
        dict_path = os.path.join(self.base_dir, "player_names.json")
        try:
            with open(dict_path, 'w', encoding='utf-8') as f:
                json.dump(self.player_name_dict, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"선수 이름 사전 저장 오류: {e}")
            return False
    
    def update_player_name_dict(self, corrections):
        """선수 이름 사전 업데이트"""
        if 'player_name' not in corrections:
            return False
        
        try:
            # 원본 이름과 수정된 이름 가져오기
            original_name = corrections.get('original_player_name', '')
            corrected_name = corrections['player_name']
            
            # 원본 이름이 없으면 처리 불가
            if not original_name or not corrected_name:
                return False
            
            # 동일한 경우 무시
            if original_name == corrected_name:
                return False
            
            # 사전에 추가
            self.player_name_dict[original_name] = corrected_name
            
            # 사전 저장
            self._save_player_name_dict()
            
            logger.info(f"선수 이름 사전 업데이트: {original_name} -> {corrected_name}")
            return True
        except Exception as e:
            logger.error(f"선수 이름 사전 업데이트 오류: {e}")
            return False
    
    def recognize_all(self, rois):
        """모든 ROI 인식"""
        raise NotImplementedError("서브클래스에서 구현해야 합니다")

class OCRRecognizer(BaseRecognizer):
    """OCR 기반 인식기"""
    def __init__(self, config):
        """초기화"""
        super().__init__(config)
        self.confidence_threshold = config.get('settings', 'confidence_threshold')
    
    def recognize_all(self, rois):
        """모든 ROI 인식"""
        results = {'success': True, 'results': {}, 'confidences': {}}
        
        # 각 ROI 인식
        for field, roi in rois.items():
            if roi is None:
                continue
            
            # 인식 실행
            text, confidence = self.recognize_text(roi, field)
            
            # 결과 저장
            results['results'][field] = text
            results['confidences'][field] = confidence
        
        return results
    
    def recognize_text(self, roi, field):
        """ROI에서 텍스트 인식"""
        if roi is None or roi.size == 0:
            logger.warning(f"'{field}' 인식 실패: 빈 이미지")
            return "", 0.0
        
        # 캐싱 사용 여부 확인
        if self.enable_caching:
            # 이미지 해시 생성
            try:
                img_hash = hashlib.md5(roi.tobytes()).hexdigest()
                cache_key = f"{field}_{img_hash}"
                
                # 캐시 확인
                if cache_key in self.ocr_cache:
                    cached_result = self.ocr_cache[cache_key]
                    logger.info(f"OCR 캐시 히트: {field} - {cached_result[0]}")
                    return cached_result
            except:
                # 해시 생성 실패 시 캐싱 사용 안 함
                pass
        
        # 부스트 레벨 특별 처리
        if field == 'boost_level':
            return self._recognize_boost_level(roi)
        
        # 필드별 전처리 및 OCR 설정
        preprocessed_images, config = self._get_preprocessing_config(roi, field)
        
        # 디버그 모드인 경우 전처리된 이미지 저장
        if self.debug_mode:
            for i, img in enumerate(preprocessed_images):
                # 이미지 형식 체크
                if len(img.shape) == 2 or img.shape[2] == 1:  # 그레이스케일
                    debug_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                else:  # 컬러
                    debug_img = img.copy()
                
                debug_path = os.path.join(self.debug_dir, f"debug_{field}_preproc{i}.jpg")
                cv2.imwrite(debug_path, debug_img)
        
        # 각 전처리 이미지별 OCR 수행
        results = []
        
        for i, img in enumerate(preprocessed_images):
            try:
                # OCR 수행
                text = pytesseract.image_to_string(img, config=config).strip()
                
                # 후처리
                text = self._postprocess_text(text, field)
                
                if text:
                    results.append(text)
                    if self.debug_mode:
                        logger.info(f"OCR 결과 ({field}, 이미지 {i}): '{text}'")
            except Exception as e:
                logger.warning(f"OCR 인식 중 오류 ({field}, 이미지 {i}): {e}")
        
        # 결과 빈도 계산 및 가장 많이 나온 결과 반환
        if results:
            counter = Counter(results)
            most_common = counter.most_common(1)[0]
            text = most_common[0]
            confidence = most_common[1] / len(preprocessed_images)
            
            # 선수 이름 사전 적용 (선수 이름 필드만)
            if field == 'player_name' and text in self.player_name_dict:
                text = self.player_name_dict[text]
                confidence = 1.0  # 사전 교정은 최고 신뢰도
            
            # 결과 캐싱
            if self.enable_caching:
                try:
                    self.ocr_cache[cache_key] = (text, confidence)
                    
                    # 캐시 크기 제한 (최대 1000개)
                    if len(self.ocr_cache) > 1000:
                        # 오래된 캐시 삭제 (단순 FIFO 방식)
                        oldest_key = next(iter(self.ocr_cache))
                        self.ocr_cache.pop(oldest_key)
                except:
                    pass
            
            return text, confidence
        else:
            # 인식 실패
            default_values = {
                'overall': '80',
                'position': 'ST',
                'salary': '1',
                'enhance_level': '0',
                'player_name': '알 수 없음',
                'season_icon': '21FC',
                'boost_level': '0'
            }
            return default_values.get(field, ''), 0.0
    
    def _recognize_boost_level(self, roi):
        """부스트 레벨 게이지 인식"""
        try:
            # HSV 색상 공간으로 변환
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            
            # 녹색 범위 정의
            lower_green = np.array([35, 40, 40])
            upper_green = np.array([85, 255, 255])
            
            # 녹색 마스크 생성
            green_mask = cv2.inRange(hsv, lower_green, upper_green)
            
            # 모폴로지 연산으로 노이즈 제거
            kernel = np.ones((2, 2), np.uint8)
            green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel)
            
            # 게이지 바의 가로 방향 분석
            height, width = green_mask.shape
            
            # 다양한 높이에서 스캔하여 평균 녹색 끝 위치 찾기
            green_ends = []
            for h_pos in [height//4, height//2, height*3//4]:
                if h_pos < height:
                    row = green_mask[h_pos, :]
                    
                    # 왼쪽부터 연속된 녹색 영역의 끝 찾기
                    green_end = 0
                    for x in range(width):
                        if row[x] > 0:  # 녹색 픽셀
                            green_end = x
                        else:
                            # 구분선인지 확인 (짧은 간격이면 무시)
                            if x + 5 < width and np.any(row[x:x+5] > 0):
                                continue  # 구분선이므로 계속
                            if green_end > 0:  # 이미 녹색 영역이 발견된 경우
                                break  # 녹색 영역 끝
                    
                    green_ends.append(green_end)
            
            # 평균 녹색 끝 위치 계산
            if green_ends:
                green_end = sum(green_ends) / len(green_ends)
            else:
                green_end = 0
            
            # 전체 대비 녹색 비율 계산
            green_ratio = (green_end + 1) / width
            
            # 게이지 범위에 따른 보정
            boost_steps = [0, 20, 40, 50, 60, 80, 100]  # 가능한 부스트 값
            boost_thresholds = [0.05, 0.25, 0.45, 0.55, 0.65, 0.85, 0.95]  # 각 값의 임계치
            
            boost_percent = 0
            for i, threshold in enumerate(boost_thresholds):
                if green_ratio >= threshold:
                    boost_percent = boost_steps[i]
            
            # 디버그 정보
            if self.debug_mode:
                logger.info(f"부스트 레벨 분석: 녹색 끝 위치={green_end:.1f}, "
                         f"전체 너비={width}, 비율={green_ratio:.2f}, 결과={boost_percent}%")
                
                # 시각화 이미지 저장
                debug_boost = np.zeros((50, width, 3), dtype=np.uint8)
                # 전체 게이지 바 그리기 (회색)
                cv2.rectangle(debug_boost, (0, 0), (width-1, 49), (128, 128, 128), -1)
                # 녹색 부분 그리기
                cv2.rectangle(debug_boost, (0, 0), (int(green_end), 49), (0, 255, 0), -1)
                # 비율 표시
                cv2.putText(debug_boost, f"{green_ratio:.2f} ({boost_percent}%)", (5, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                cv2.imwrite(os.path.join(self.debug_dir, "debug_boost_analysis.jpg"), debug_boost)
            
            return str(boost_percent), 1.0
            
        except Exception as e:
            logger.error(f"부스트 레벨 분석 오류: {e}")
            return "0", 0.0
    
    def _get_preprocessing_config(self, roi, field):
        """필드별 전처리 및 OCR 설정"""
        if field == 'overall':
            preprocessed_images = [
                roi,  # 원본
                cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY),  # 그레이스케일
                # 이진화
                cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
                # 적응형 이진화
                cv2.adaptiveThreshold(cv2.GaussianBlur(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), (5, 5), 0), 
                                    255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            ]
            config = '--psm 7 -c tessedit_char_whitelist=0123456789'
        elif field == 'position':
            preprocessed_images = [
                roi,  # 원본
                cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY),  # 그레이스케일
                # 이진화
                cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
                # 노이즈 제거
                cv2.medianBlur(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 3)
            ]
            config = '--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        elif field == 'salary':
            preprocessed_images = [
                roi,  # 원본
                cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY),  # 그레이스케일
                # 이진화
                cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
                # 대비 강화
                cv2.equalizeHist(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY))
            ]
            config = '--psm 7 -c tessedit_char_whitelist=0123456789'
        elif field == 'enhance_level':
            preprocessed_images = [
                roi,  # 원본
                cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY),  # 그레이스케일
                # 이진화
                cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
                # 확대
                cv2.resize(roi, (roi.shape[1]*2, roi.shape[0]*2), interpolation=cv2.INTER_CUBIC)
            ]
            config = '--psm 7 -c tessedit_char_whitelist=0123456789'
        elif field == 'player_name':
            preprocessed_images = [
                roi,  # 원본
                cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY),  # 그레이스케일
                # 이진화
                cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
                # 선명도 향상
                cv2.convertScaleAbs(roi, alpha=1.5, beta=0)
            ]
            config = '--psm 7 -l kor+eng'  # 한글+영어 인식
        elif field == 'season_icon':
            preprocessed_images = [
                roi,  # 원본
                cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY),  # 그레이스케일
                # 이진화
                cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
                # 에지 강화
                cv2.Canny(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 100, 200)
            ]
            config = '--psm 7'  # 기본 설정
        else:
            preprocessed_images = [roi]
            config = '--psm 7'  # 기본 설정
        
        return preprocessed_images, config
    
    def _postprocess_text(self, text, field):
        """인식된 텍스트 후처리"""
        if field == 'overall':
            # 숫자만 추출
            text = ''.join(filter(str.isdigit, text))
            if text and len(text) > 0:
                # 70-120 범위 확인
                num = int(text)
                if num < 70:
                    text = str(70 + (num % 50))  # 70보다 작으면 70에 맞춤
                elif num > 120:
                    text = str(70 + (num % 50))  # 120보다 크면 조정
        elif field == 'position':
            # 알파벳만 추출하고 대문자로 변환
            text = ''.join(filter(str.isalpha, text)).upper()
            # 포지션 유효성 검사 (유효한 포지션 목록)
            valid_positions = {'GK', 'SW', 'CB', 'LB', 'RB', 'DMF', 'CMF', 'LMF', 'RMF', 
                              'AMF', 'LWF', 'RWF', 'SS', 'CF', 'ST', 'CAM', 'CDM', 'RW'}
            
            # 유사한 포지션으로 교정
            position_correction = {
                'DM': 'DMF', 'CM': 'CMF', 'AM': 'AMF', 'RM': 'RMF', 'LM': 'LMF',
                'RW': 'RWF', 'LW': 'LWF', 'CD': 'CB', 'LWP': 'LWF', 'BWF': 'RWF',
                'DMI': 'DMF', 'CNF': 'CMF', 'BMP': 'RMF'
            }
            
            if text in position_correction:
                text = position_correction[text]

            if text not in valid_positions:
                # 유효하지 않은 포지션은 가장 유사한 포지션으로 교정
                if 'LW' in text or 'LF' in text:
                    text = 'LWF'
                elif 'RW' in text or 'RF' in text:
                    text = 'RWF'
                elif 'DM' in text:
                    text = 'DMF'
                elif 'CM' in text:
                    text = 'CMF'
                elif 'AM' in text:
                    text = 'AMF'
                elif 'CB' in text:
                    text = 'CB'
                elif text.startswith('S') and len(text) > 1:
                    text = 'ST'
        elif field == 'salary':
            # 숫자만 추출
            text = ''.join(filter(str.isdigit, text))
            if text and len(text) > 0:
                # 유효 범위 확인 (1-100)
                num = int(text)
                if num > 100:
                    text = str(1 + (num % 100))  # 100보다 크면 조정
        elif field == 'enhance_level':
            # 숫자만 추출하고 범위 확인 (0-5)
            text = ''.join(filter(str.isdigit, text))
            if text and len(text) > 0:
                num = int(text)
                if num > 5:
                    text = '5'  # 최대 5로 제한
        elif field == 'player_name':
            # 특수문자 및 불필요한 기호 제거
            text = re.sub(r'[^\w가-힣]', '', text)  # \s(공백)도 제거 대상에 포함
            
            # 모든 공백 제거
            text = text.replace(" ", "")
            
            # 선수 이름 사전 확인
            if text in self.player_name_dict:
                text = self.player_name_dict[text]
        elif field == 'season_icon':
            # 일반적인 시즌 아이콘 목록에 있는지 확인
            season_icons = {'21FC', '22FC', 'TOTS', 'TOTY', 'ICON', 'HERO', 'LOL', 'HC'}
            
            # 공백 제거 및 대문자 변환
            text = text.replace(' ', '').upper()
            
            # 유사 아이콘으로 교정
            icon_correction = {
                'FC21': '21FC', 'FC22': '22FC',
                'TOT': 'TOTS', 'TTS': 'TOTS', 'T0TS': 'TOTS',
                'TTY': 'TOTY', 'TOY': 'TOTY', 'T0TY': 'TOTY',
                'HRO': 'HERO', 'HER': 'HERO', 'HEP0': 'HERO',
                'IC0N': 'ICON', 'ICN': 'ICON', '1CON': 'ICON'
            }
            
            if text in icon_correction:
                text = icon_correction[text]
        
        return text

class CombinedRecognizer(OCRRecognizer):
    """OCR과 딥러닝을 결합한 인식기"""
    def __init__(self, config):
        """초기화"""
        super().__init__(config)
        
        # 모델 로드
        self.models_dir = config.get_path('models_dir')
        self.models = self._load_models()
    
    def _load_models(self):
        """학습된 모델 로드"""
        models = {}
        
        # 모델 디렉토리 확인
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir, exist_ok=True)
            logger.info(f"모델 디렉토리 생성됨: {self.models_dir}")
            return models
        
        # 필드별 모델 로드
        for field in ['overall', 'position', 'salary', 'enhance_level', 'season_icon']:
            model_path = os.path.join(self.models_dir, f"{field}_model.h5")
            
            if os.path.exists(model_path):
                try:
                    # 컴파일 옵션 끄고 로드하여 호환성 문제 최소화
                    model = tf.keras.models.load_model(model_path, compile=False)
                    
                    # 모델 테스트 (유효성 검증)
                    test_input = np.zeros((1, 224, 224, 3), dtype=np.float32)
                    _ = model.predict(test_input, verbose=0)
                    
                    # 모델 저장
                    models[field] = model
                    logger.info(f"모델 로드 성공: {field}")
                    
                except Exception as e:
                    logger.warning(f"모델 로드 실패 ({field}): {e}")
        
        return models
    
    def recognize_all(self, rois):
        """모든 ROI 인식 (OCR + 딥러닝)"""
        # 기본 OCR 인식 결과
        results = super().recognize_all(rois)
        
        # 딥러닝 모델이 있는 필드는 모델 예측 결과 추가
        for field, model in self.models.items():
            if field in rois and rois[field] is not None:
                try:
                    # 이미지 전처리
                    roi = rois[field]
                    img = cv2.resize(roi, (224, 224))
                    img = img / 255.0
                    img = np.expand_dims(img, axis=0)
                    
                    # 예측
                    predictions = model.predict(img, verbose=0)
                    pred_class = np.argmax(predictions[0])
                    pred_conf = float(predictions[0][pred_class])
                    
                    # 분류 결과 변환
                    if field == 'overall':
                        pred_value = str(pred_class + 70)  # 70-120 범위
                    elif field == 'position':
                        position_classes = [
                            'GK', 'SW', 'CB', 'LB', 'RB', 'DMF', 'CMF', 'LMF', 'RMF', 
                            'AMF', 'LWF', 'RWF', 'SS', 'CF', 'ST', 'CAM', 'CDM', 'RW'
                        ]
                        pred_value = position_classes[min(pred_class, len(position_classes)-1)]
                    elif field == 'enhance_level':
                        pred_value = str(pred_class)  # 0-5 범위
                    elif field == 'season_icon':
                        season_classes = [
                            '21FC', '22FC', 'TOTS', 'TOTY', 'ICON', 'HERO', 'LOL', 'HC', 'OTHER'
                        ]
                        pred_value = season_classes[min(pred_class, len(season_classes)-1)]
                    elif field == 'salary':
                        pred_value = str(pred_class + 1)  # 1-100 범위
                    else:
                        continue
                    
                    # OCR 결과보다 신뢰도가 높으면 교체
                    ocr_conf = results['confidences'].get(field, 0)
                    if pred_conf > ocr_conf:
                        results['results'][field] = pred_value
                        results['confidences'][field] = pred_conf
                        
                        if self.debug_mode:
                            logger.info(f"모델 인식 결과 ({field}): '{pred_value}' (신뢰도: {pred_conf:.1%})")
                except Exception as e:
                    logger.warning(f"모델 예측 오류 ({field}): {e}")
        
        return results