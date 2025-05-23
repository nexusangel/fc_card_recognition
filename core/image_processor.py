# fc_card_recognition/core/image_processor.py
import os
import cv2
import numpy as np
import logging

logger = logging.getLogger("FC_Online_Recognition")

class ImageProcessor:
    """이미지 처리 및 ROI 추출 클래스"""
    def __init__(self, config):
        """초기화"""
        self.config = config
        self.debug_mode = config.get('settings', 'debug_mode')
        self.debug_dir = config.get_path('debug_dir')
        self.roi_config = self._load_roi_config()
        
        # 필드별 색상 정의
        self.field_colors = {
            'overall': (0, 0, 255),      # 빨강
            'position': (0, 255, 0),     # 초록
            'season_icon': (255, 0, 0),  # 파랑
            'salary': (0, 255, 255),     # 노랑
            'enhance_level': (255, 0, 255),  # 자주색
            'player_name': (255, 255, 0),    # 청록색
            'boost_level': (128, 0, 255)     # 보라색
        }
    
    def _load_roi_config(self):
        """ROI 설정 로드"""
        roi_config_path = os.path.join(
            self.config.get_path('base_dir'), 
            "roi_config.json"
        )
        
        try:
            if os.path.exists(roi_config_path):
                import json
                with open(roi_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            logger.error(f"ROI 설정 로드 오류: {e}")
            return {}
    
    def load_image(self, image_path):
        """이미지 파일 로드"""
        try:
            if not os.path.exists(image_path):
                logger.error(f"이미지 파일이 존재하지 않습니다: {image_path}")
                return None
            
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"이미지를 로드할 수 없습니다: {image_path}")
                return None
            
            return img
        except Exception as e:
            logger.error(f"이미지 로드 오류: {e}")
            return None
    
    def detect_card(self, image):
        """이미지에서 카드 영역 감지"""
        try:
            # 이미지 크기 확인
            height, width = image.shape[:2]
            
            # 너무 작거나 큰 이미지 처리
            if width < 300 or height < 300:
                logger.warning(f"이미지가 너무 작습니다: {width}x{height}")
                return None
            
            # 이미지 전처리 (크기 정규화 - 비율 유지)
            max_dimension = 1280
            if width > max_dimension or height > max_dimension:
                scale = max_dimension / max(width, height)
                new_width, new_height = int(width * scale), int(height * scale)
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
                height, width = new_height, new_width
                logger.info(f"이미지 크기 조정: {width}x{height}")
            
            # 디버그 모드인 경우 원본 이미지 저장
            if self.debug_mode:
                debug_img_path = os.path.join(self.debug_dir, "debug_original.jpg")
                cv2.imwrite(debug_img_path, image)
            
            # HSV 색 공간으로 변환 (더 나은 색상 분리)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # 여러 색상 범위 마스크 생성
            masks = []
            
            # 밝은 영역 마스크 (카드는 대체로 밝음)
            lower_val = np.array([0, 0, 150])  # 밝기가 150 이상인 모든 색상
            upper_val = np.array([180, 60, 255])
            bright_mask = cv2.inRange(hsv, lower_val, upper_val)
            masks.append(bright_mask)
            
            # 금색/노란색 영역 마스크 (시즌 아이콘 등)
            lower_gold = np.array([20, 100, 100])
            upper_gold = np.array([40, 255, 255])
            gold_mask = cv2.inRange(hsv, lower_gold, upper_gold)
            masks.append(gold_mask)
            
            # 파란색 영역 마스크 (배경색 등)
            lower_blue = np.array([100, 50, 50])
            upper_blue = np.array([130, 255, 255])
            blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
            masks.append(blue_mask)
            
            # 모든 마스크 결합
            combined_mask = np.zeros_like(bright_mask)
            for mask in masks:
                combined_mask = cv2.bitwise_or(combined_mask, mask)
            
            # 모폴로지 연산으로 노이즈 제거 및 영역 확장
            kernel = np.ones((5, 5), np.uint8)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
            
            # 디버그 모드인 경우 마스크 저장
            if self.debug_mode:
                cv2.imwrite(os.path.join(self.debug_dir, "debug_mask.jpg"), combined_mask)
            
            # 윤곽선 찾기
            contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 가장 큰 윤곽선 선택 (일정 크기 이상)
            min_area = width * height * 0.1  # 전체 이미지의 10% 이상
            valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
            
            if valid_contours:
                # 가장 큰 윤곽선 선택
                largest_contour = max(valid_contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)
                
                # 비율 확인 (카드 비율은 약 1:1.4)
                aspect_ratio = h / w
                
                # 카드 비율 범위 확장 (1.0 ~ 1.8)
                if 1.0 <= aspect_ratio <= 1.8:
                    # 카드 추출
                    card = image[y:y+h, x:x+w].copy()
                    
                    # 디버그 모드인 경우 검출된 카드 저장
                    if self.debug_mode:
                        cv2.imwrite(os.path.join(self.debug_dir, "debug_card_detected.jpg"), card)
                        
                        # 디버그 이미지에 검출 영역 표시
                        debug_img = image.copy()
                        cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        cv2.putText(debug_img, f"AR: {aspect_ratio:.2f}", (x, y-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                        cv2.imwrite(os.path.join(self.debug_dir, "debug_card_detection.jpg"), debug_img)
                    
                    logger.info(f"카드 감지 성공: ({x}, {y}, {w}, {h}), 비율: {aspect_ratio:.2f}")
                    return {
                        'card': card,
                        'position': (x, y, w, h)
                    }
            
            # 카드 감지 실패 시 전체 이미지 사용
            logger.warning("카드 감지 실패, 전체 이미지 사용")
            
            if self.debug_mode:
                cv2.imwrite(os.path.join(self.debug_dir, "debug_card_fallback.jpg"), image)
            
            return {
                'card': image.copy(),
                'position': (0, 0, width, height)
            }
            
        except Exception as e:
            logger.error(f"카드 감지 오류: {e}")
            return None
    
    def extract_rois(self, card):
        """카드에서 중요 정보 영역 추출"""
        height, width = card.shape[:2]
        rois = {}
        
        # 디버그용 이미지 복사
        if self.debug_mode:
            debug_card = card.copy()
        
        # 수동 ROI 설정 사용 여부 확인
        use_manual_roi = self.config.get('settings', 'use_manual_roi')
        
        if use_manual_roi and self.roi_config:
            # 수동 ROI 설정이 있는 경우 이를 우선 사용
            logger.info(f"수동 ROI 설정 사용: {len(self.roi_config)}개 필드 설정됨")
            
            for field, roi_ratio in self.roi_config.items():
                try:
                    # 좌표 값 검증
                    if not (isinstance(roi_ratio, list) and len(roi_ratio) == 4):
                        continue
                    
                    x1, y1, x2, y2 = roi_ratio
                    
                    # 좌표값 검증 (0~1 사이 값)
                    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
                        continue
                    
                    # 픽셀 좌표로 변환
                    x1_px, y1_px = int(x1 * width), int(y1 * height)
                    x2_px, y2_px = int(x2 * width), int(y2 * height)
                    
                    # ROI 추출 (픽셀 좌표 범위 검증)
                    if 0 <= x1_px < x2_px <= width and 0 <= y1_px < y2_px <= height:
                        roi = card[y1_px:y2_px, x1_px:x2_px].copy()
                        
                        # 유효한 ROI 확인 (빈 배열이 아닌지)
                        if roi.size > 0 and roi.shape[0] > 0 and roi.shape[1] > 0:
                            rois[field] = roi
                            
                            # 디버그 이미지에 ROI 영역 표시
                            if self.debug_mode:
                                color = self.field_colors.get(field, (0, 255, 0))
                                cv2.rectangle(debug_card, (x1_px, y1_px), (x2_px, y2_px), color, 2)
                                cv2.putText(debug_card, field, (x1_px, y1_px-5), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                                
                                # ROI 디버그 저장
                                debug_roi_path = os.path.join(self.debug_dir, f"debug_{field}.jpg")
                                cv2.imwrite(debug_roi_path, roi)
                except Exception as e:
                    logger.error(f"필드 '{field}'의 ROI 추출 오류: {e}")
        else:
            # 자동 ROI 감지 (기본 위치 기반)
            logger.info("자동 ROI 감지 사용")
            
            # 기본 ROI 위치 (상대 좌표)
            default_rois = {
                'overall': [0.35, 0.05, 0.65, 0.15],
                'position': [0.35, 0.15, 0.65, 0.25],
                'salary': [0.1, 0.35, 0.3, 0.45],
                'enhance_level': [0.05, 0.6, 0.25, 0.75],
                'player_name': [0.2, 0.75, 0.8, 0.9],
                'season_icon': [0.05, 0.05, 0.25, 0.15],
                'boost_level': [0.7, 0.435, 0.97, 0.455]
            }
            
            for field, roi_ratio in default_rois.items():
                try:
                    x1, y1, x2, y2 = roi_ratio
                    
                    # 픽셀 좌표로 변환
                    x1_px, y1_px = int(x1 * width), int(y1 * height)
                    x2_px, y2_px = int(x2 * width), int(y2 * height)
                    
                    # ROI 추출
                    if 0 <= x1_px < x2_px <= width and 0 <= y1_px < y2_px <= height:
                        roi = card[y1_px:y2_px, x1_px:x2_px].copy()
                        
                        if roi.size > 0 and roi.shape[0] > 0 and roi.shape[1] > 0:
                            rois[field] = roi
                            
                            # 디버그 이미지에 ROI 영역 표시
                            if self.debug_mode:
                                color = self.field_colors.get(field, (0, 255, 0))
                                cv2.rectangle(debug_card, (x1_px, y1_px), (x2_px, y2_px), color, 2)
                                cv2.putText(debug_card, field, (x1_px, y1_px-5), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                                
                                # ROI 디버그 저장
                                debug_roi_path = os.path.join(self.debug_dir, f"debug_{field}.jpg")
                                cv2.imwrite(debug_roi_path, roi)
                except Exception as e:
                    logger.error(f"자동 ROI 추출 오류 ({field}): {e}")
        
        # 디버그 이미지 저장
        if self.debug_mode:
            cv2.imwrite(os.path.join(self.debug_dir, "debug_all_rois.jpg"), debug_card)
        
        return rois
    
    def create_debug_image(self, image, card_data, rois, results):
        """디버그 이미지 생성 (ROI 영역 및 인식 결과 표시)"""
        debug_image = image.copy()
        
        # 카드 영역 표시
        x, y, w, h = card_data['position']
        cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # 인식 결과가 있는 경우만 처리
        if results.get('success', False) and 'results' in results:
            # 카드 이미지
            card = card_data['card']
            card_h, card_w = card.shape[:2]
            
            # 각 ROI 영역 표시
            for field, roi in rois.items():
                if field not in results['results']:
                    continue
                
                # 인식 결과와 신뢰도
                value = results['results'][field]
                confidence = results['confidences'].get(field, 0)
                
                # ROI 영역 좌표 계산
                roi_h, roi_w = roi.shape[:2]
                
                # 카드 내 상대 위치 계산 (roi 추출 시 사용한 방식과 일치하게)
                if field in self.roi_config:
                    # 수동 설정된 ROI 좌표
                    rx1, ry1, rx2, ry2 = self.roi_config[field]
                    rx = int(x + rx1 * w)
                    ry = int(y + ry1 * h)
                    rw = int((rx2 - rx1) * w)
                    rh = int((ry2 - ry1) * h)
                else:
                    # 기본 위치
                    if field == 'overall':
                        rx, ry = int(x + w*0.35), int(y + h*0.05)
                    elif field == 'position':
                        rx, ry = int(x + w*0.35), int(y + h*0.15)
                    elif field == 'salary':
                        rx, ry = int(x + w*0.1), int(y + h*0.35)
                    elif field == 'enhance_level':
                        rx, ry = int(x + w*0.05), int(y + h*0.6)
                    elif field == 'player_name':
                        rx, ry = int(x + w*0.2), int(y + h*0.75)
                    elif field == 'season_icon':
                        rx, ry = int(x + w*0.05), int(y + h*0.05)
                    elif field == 'boost_level':
                        rx, ry = int(x + w*0.7), int(y + h*0.435)
                    else:
                        continue
                    
                    rw, rh = roi_w, roi_h
                
                # 색상 설정 (신뢰도에 따라)
                if confidence >= 0.8:
                    color = (0, 255, 0)  # 높은 신뢰도: 녹색
                elif confidence >= 0.5:
                    color = (0, 255, 255)  # 중간 신뢰도: 노랑
                else:
                    color = (0, 0, 255)  # 낮은 신뢰도: 빨강
                
                # ROI 영역 그리기
                cv2.rectangle(debug_image, (rx, ry), (rx+rw, ry+rh), color, 2)
                
                # 필드 이름 및 인식 결과 표시
                label = f"{field}: {value} ({confidence:.1f})"
                cv2.putText(debug_image, label, (rx, ry-5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # 디버그 이미지 저장
        if self.debug_mode:
            cv2.imwrite(os.path.join(self.debug_dir, "debug_recognition_result.jpg"), debug_image)
        
        return debug_image