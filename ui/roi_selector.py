# roi_selector.py - FC 온라인 선수 카드 인식 시스템 ROI 선택 모듈

import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import json
import logging
from pathlib import Path

logger = logging.getLogger("FC_Online_Recognition")

class ROISelector:
    """ROI(Region of Interest) 영역 선택 관리 클래스"""
    
    def __init__(self, parent, base_dir=None):
        """
        ROI 선택기 초기화
        
        Args:
            parent: 부모 윈도우 또는 애플리케이션 인스턴스
            base_dir: 설정 파일 저장 기본 디렉토리
        """
        self.parent = parent
        
        # 기본 디렉토리 설정
        if base_dir is None:
            self.base_dir = os.path.join(str(Path.home()), "fc_online_data")
        else:
            self.base_dir = base_dir
            
        # ROI 설정 파일 경로
        self.roi_config_path = os.path.join(self.base_dir, "roi_config.json")
        self.roi_presets_path = os.path.join(self.base_dir, "roi_presets.json")
        
        # 디버그 디렉토리
        self.debug_dir = os.path.join(self.base_dir, "debug")
        os.makedirs(self.debug_dir, exist_ok=True)
        
        # ROI 관련 변수 초기화
        self.roi_selections = {}
        self.field_colors = {
            'overall': '#FF0000',     # 빨강
            'position': '#00FF00',    # 초록
            'salary': '#0000FF',      # 파랑
            'enhance_level': '#FFFF00', # 노랑
            'player_name': '#FF00FF', # 마젠타
            'season_icon': '#00FFFF',  # 시안
            'boost_level': '#FF8000'  # 주황
        }
        
        # ROI 설정 로드
        self.load_roi_config()
        self.load_roi_presets()
        
        # 기타 변수 초기화
        self.current_image = None
        self.roi_original_image = None
        self.roi_selection_start_x = None
        self.roi_selection_start_y = None
        self.roi_image_offset_x = 0
        self.roi_image_offset_y = 0
        self.training_canceled = False

    def load_roi_config(self):
        """마우스로 선택한 ROI 좌표 설정 로드"""
        if os.path.exists(self.roi_config_path):
            try:
                with open(self.roi_config_path, 'r', encoding='utf-8') as f:
                    roi_config = json.load(f)
                
                # ROI 구성의 유효성 검사
                valid_config = {}
                for field, coords in roi_config.items():
                    # 좌표가 4개이고, 모두 0~1 사이의 값인지 확인
                    if (isinstance(coords, list) and len(coords) == 4 and
                        all(isinstance(c, (int, float)) and 0 <= c <= 1 for c in coords)):
                        valid_config[field] = coords
                    else:
                        logger.warning(f"유효하지 않은 ROI 설정 무시: {field} - {coords}")
                
                logger.info(f"ROI 좌표 설정 로드 완료: {len(valid_config)}개 필드")
                self.roi_selections = valid_config
                return valid_config
            except Exception as e:
                logger.error(f"ROI 좌표 설정 로드 실패: {e}")
        
        # 기본값 반환
        logger.info("ROI 설정 파일이 없습니다. 기본 설정을 사용합니다.")
        return {}

    def save_roi_config(self):
        """마우스로 선택한 ROI 좌표 설정 저장"""
        try:
            # 좌표 값 검증
            valid_selections = {}
            for field, coords in self.roi_selections.items():
                if isinstance(coords, list) and len(coords) == 4:
                    # 모든 좌표가 0~1 사이의 유효한 값인지 확인
                    if all(isinstance(c, (int, float)) and 0 <= c <= 1 for c in coords):
                        valid_selections[field] = coords
                    else:
                        logger.warning(f"유효하지 않은 ROI 좌표 값: {field} - {coords}")
                else:
                    logger.warning(f"유효하지 않은 ROI 좌표 형식: {field} - {coords}")
            
            # 유효한 좌표만 저장
            with open(self.roi_config_path, 'w', encoding='utf-8') as f:
                json.dump(valid_selections, f, indent=2)
            logger.info(f"ROI 좌표 설정 저장 완료: {len(valid_selections)}개 필드")
            
            return True
        except Exception as e:
            logger.error(f"ROI 좌표 설정 저장 실패: {e}")
            return False

    def load_roi_presets(self):
        """저장된 ROI 프리셋 불러오기"""
        if os.path.exists(self.roi_presets_path):
            try:
                with open(self.roi_presets_path, 'r', encoding='utf-8') as f:
                    presets = json.load(f)
                    logger.info(f"ROI 프리셋 로드 완료: {len(presets)}개")
                    self.roi_presets = presets
                    return presets
            except Exception as e:
                logger.error(f"ROI 프리셋 로드 오류: {e}")
        
        # 기본 프리셋 생성
        default_presets = {
            "기본 설정": {
                "overall": [0.35, 0.05, 0.65, 0.15],
                "position": [0.35, 0.15, 0.65, 0.25],
                "salary": [0.1, 0.35, 0.3, 0.45],
                "enhance_level": [0.05, 0.6, 0.25, 0.75],
                "player_name": [0.2, 0.75, 0.8, 0.9],
                "season_icon": [0.05, 0.05, 0.25, 0.15],
                "boost_level": [0.7, 0.435, 0.97, 0.455]
            }
        }
        self.roi_presets = default_presets
        self.save_roi_presets()
        return default_presets

    def save_roi_presets(self, presets=None):
        """ROI 프리셋 저장"""
        try:
            if presets is None:
                presets = self.roi_presets
            
            with open(self.roi_presets_path, 'w', encoding='utf-8') as f:
                json.dump(presets, f, indent=2)
                logger.info(f"ROI 프리셋 저장 완료: {len(presets)}개")
            
            return True
        except Exception as e:
            logger.error(f"ROI 프리셋 저장 오류: {e}")
            return False

    def setup_manual_roi_selection(self, image):
        """마우스 드래그로 ROI 영역 지정 UI 설정"""
        if image is None:
            messagebox.showinfo("알림", "이미지를 먼저 로드하세요.")
            return
        
        # ROI 원본 이미지 저장
        self.roi_original_image = image.copy()
        
        # ROI선택 창 생성
        selection_window = tk.Toplevel(self.parent)
        selection_window.title("수동 ROI 영역 지정")
        selection_window.geometry("1300x900")  # 초기 창 크기
        
        # 안내 텍스트
        ttk.Label(selection_window, text="각 필드 선택 후 영역을 드래그하여 지정하세요. 모든 필드의 영역을 선택한 후 '모든 ROI 저장' 버튼을 클릭하세요.",
                font=('Gulim', 12, 'bold')).pack(pady=10)
        
        # 메인 프레임
        main_frame = ttk.Frame(selection_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 좌측 이미지 프레임
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 이미지 관련 컨트롤 설정
        control_frame, canvas, roi_info_label = self._setup_image_controls(left_frame)
        
        # 우측 컨트롤 패널
        right_panel, field_selections, field_rectangles, field_var = self._setup_control_panel(main_frame)
        
        # 자동 크기 조정 및 줌 관련 변수
        auto_resize_var = tk.BooleanVar(value=True)
        roi_zoom_var = tk.DoubleVar(value=1.0)
        
        # 이벤트 핸들러 설정
        self._setup_event_handlers(selection_window, canvas, field_var, field_selections, 
                                  field_rectangles, roi_zoom_var, auto_resize_var, roi_info_label)
        
        # 초기 이미지 표시
        selection_window.after(100, lambda: self._update_roi_display(canvas, self.roi_original_image, 
                                                                   field_var.get(), field_selections, 
                                                                   field_rectangles, roi_zoom_var, roi_info_label))
        
        return selection_window

    def _setup_image_controls(self, parent_frame):
        """이미지 표시 영역 및 컨트롤 설정"""
        # 상단 컨트롤 프레임
        control_frame = ttk.Frame(parent_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        # 자동 크기 조정 옵션
        auto_resize_var = tk.BooleanVar(value=True)  # 기본값 True
        
        auto_resize_check = ttk.Checkbutton(
            control_frame,
            text="창 크기에 맞춤",
            variable=auto_resize_var
        )
        auto_resize_check.pack(side=tk.LEFT, padx=10)
        
        # 줌 컨트롤 프레임
        zoom_frame = ttk.Frame(control_frame)
        zoom_frame.pack(side=tk.RIGHT, padx=5)
        ttk.Label(zoom_frame, text="확대/축소:", font=('Gulim', 11)).pack(side=tk.LEFT, padx=5)
        
        # 이미지 표시를 위한 스크롤 가능한 프레임
        img_frame = ttk.Frame(parent_frame)
        img_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 스크롤바 추가
        h_scrollbar = ttk.Scrollbar(img_frame, orient="horizontal")
        v_scrollbar = ttk.Scrollbar(img_frame, orient="vertical")
        
        # 캔버스 생성
        canvas = tk.Canvas(img_frame, bg='#404040',  # 어두운 회색 배경
                         xscrollcommand=h_scrollbar.set,
                         yscrollcommand=v_scrollbar.set,
                         highlightthickness=0)
        
        # 스크롤바 배치
        h_scrollbar.config(command=canvas.xview)
        v_scrollbar.config(command=canvas.yview)
        
        # 스크롤바 및 캔버스 패킹
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 선택된 영역 정보 표시
        info_frame = ttk.Frame(parent_frame)
        info_frame.pack(fill=tk.X, pady=5)
        roi_info_label = ttk.Label(info_frame, text="선택 정보: ", font=('Gulim', 11))
        roi_info_label.pack(side=tk.LEFT, padx=5)
        
        return control_frame, canvas, roi_info_label

    def _setup_control_panel(self, parent_frame):
        """우측 컨트롤 패널 설정"""
        # 우측 컨트롤 패널
        right_panel = ttk.Frame(parent_frame, width=300)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=5)
        right_panel.pack_propagate(False)
        
        # 필드 선택 프레임
        fields_frame = ttk.LabelFrame(right_panel, text="ROI 영역 선택", padding=(10, 5))
        fields_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 현재 선택된 필드
        field_var = tk.StringVar()
        
        # 필드별 선택 상태 및 색상
        field_selections = {}
        field_rectangles = {}

        # 모든 필드에 대한 기본 데이터 구조 초기화
        for field in self.field_colors.keys():
            field_selections[field] = {
                'coords': None,
                'label': tk.StringVar(value="미설정")
            }
            
        # 필드 버튼 생성
        for i, (field, color) in enumerate(self.field_colors.items()):
            field_frame = ttk.Frame(fields_frame)
            field_frame.pack(fill=tk.X, pady=5)
            
            # 필드 라디오 버튼
            radio = ttk.Radiobutton(field_frame, text=field, value=field, variable=field_var)
            radio.pack(side=tk.LEFT, padx=5)
            
            # 색상 표시
            color_canvas = tk.Canvas(field_frame, width=20, height=20, bg=color, highlightthickness=1)
            color_canvas.pack(side=tk.LEFT, padx=5)
            
            # 좌표 정보
            coord_var = tk.StringVar(value="미설정")
            coord_label = ttk.Label(field_frame, textvariable=coord_var, font=('Gulim', 9))
            coord_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            
            # 필드 정보 저장
            field_selections[field] = {
                'coords': None,
                'label': coord_var
            }
            
            # 이미 설정된 ROI가 있으면 표시
            if field in self.roi_selections:
                field_selections[field]['coords'] = self.roi_selections[field]
                x1, y1, x2, y2 = self.roi_selections[field]
                coord_var.set(f"[{x1:.2f}, {y1:.2f}, {x2:.2f}, {y2:.2f}]")

        # 기본 필드 선택
        field_var.set("overall")
        
        # 버튼 프레임
        buttons_frame = ttk.Frame(right_panel)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        # 현재 필드 ROI 초기화 버튼
        clear_roi_btn = ttk.Button(buttons_frame, text="현재 필드 ROI 초기화",
                                  command=lambda: self.clear_roi_selection(None, field_var.get(), field_selections, field_rectangles))
        clear_roi_btn.pack(fill=tk.X, pady=5)
        
        # 모든 ROI 저장 버튼
        save_all_btn = ttk.Button(buttons_frame, text="모든 ROI 저장",
                                command=lambda: self.save_all_roi_selections(None, field_selections))
        save_all_btn.pack(fill=tk.X, pady=5)

        # 프리셋으로 저장 기능 추가
        save_preset_frame = ttk.Frame(buttons_frame)
        save_preset_frame.pack(fill=tk.X, pady=5)
        
        preset_name_var = tk.StringVar()
        ttk.Entry(save_preset_frame, textvariable=preset_name_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(save_preset_frame, text="프리셋 저장",
                 command=lambda: self.save_roi_as_preset(None, preset_name_var.get(), field_selections)).pack(side=tk.LEFT, padx=2)
        
        return right_panel, field_selections, field_rectangles, field_var

    def _setup_event_handlers(self, window, canvas, field_var, field_selections, field_rectangles, 
                            roi_zoom_var, auto_resize_var, roi_info_label):
        """이벤트 핸들러 설정"""
        # 필드 선택 시 처리
        def on_field_change(*args):
            self._update_roi_display(canvas, self.roi_original_image, field_var.get(), 
                                    field_selections, field_rectangles, roi_zoom_var, roi_info_label)
        
        # 필드 변경 이벤트 연결
        field_var.trace('w', on_field_change)
        
        # 마우스 이벤트 바인딩
        canvas.bind("<ButtonPress-1>", lambda event: self.on_roi_selection_start(event, canvas, 
                                                                              field_var.get(), 
                                                                              field_selections, 
                                                                              field_rectangles, 
                                                                              roi_info_label, 
                                                                              roi_zoom_var, 
                                                                              self.roi_original_image))
        
        canvas.bind("<B1-Motion>", lambda event: self.on_roi_selection_drag(event, canvas, 
                                                                         field_var.get(), 
                                                                         field_selections, 
                                                                         field_rectangles, 
                                                                         roi_info_label, 
                                                                         roi_zoom_var, 
                                                                         self.roi_original_image))
        
        canvas.bind("<ButtonRelease-1>", lambda event: self.on_roi_selection_end(event, canvas, 
                                                                              field_var.get(), 
                                                                              field_selections, 
                                                                              field_rectangles, 
                                                                              roi_info_label))

    def _update_roi_display(self, canvas, roi_original_image, field, field_selections, field_rectangles, 
                           roi_zoom_var, roi_info_label):
        """ROI 설정 창의 이미지 및 ROI 영역 표시 업데이트"""
        if roi_original_image is None:
            return
        
        # 줌 비율 가져오기
        zoom = roi_zoom_var.get()
        
        # 이미지 크기 계산
        h, w = roi_original_image.shape[:2]
        new_w, new_h = int(w * zoom), int(h * zoom)
        
        # 이미지 크기 조정
        try:
            scaled_image = cv2.resize(roi_original_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            # 이미지를 Tkinter에서 표시 가능한 형식으로 변환
            display_img = cv2.cvtColor(scaled_image, cv2.COLOR_BGR2RGB)
            img_tk = ImageTk.PhotoImage(image=Image.fromarray(display_img))
            
            # 캔버스 크기 및 현재 스크롤 위치 획득
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            # 캔버스 크기가 유효하지 않으면 부모 위젯 크기 사용
            if canvas_width <= 1:
                canvas_width = canvas.master.winfo_width() - 30  # 스크롤바 공간 고려
            if canvas_height <= 1:
                canvas_height = canvas.master.winfo_height() - 30  # 스크롤바 공간 고려
            
            # 현재 스크롤 위치 (0.0 ~ 1.0)
            try:
                scroll_x = canvas.xview()[0]
                scroll_y = canvas.yview()[0]
            except:
                scroll_x = 0
                scroll_y = 0
            
            # 캔버스 내용 지우기
            canvas.delete("all")
            
            # 스크롤 영역 설정
            scroll_width = max(new_w + 100, canvas_width)
            scroll_height = max(new_h + 100, canvas_height)
            canvas.config(scrollregion=(0, 0, scroll_width, scroll_height))
            
            # 이미지 중앙 위치 계산
            x_center = max(0, (scroll_width - new_w) // 2)
            y_center = max(0, (scroll_height - new_h) // 2)
            
            # 이미지 위치 저장
            self.roi_image_offset_x = x_center
            self.roi_image_offset_y = y_center
            
            # 이미지 표시
            image_id = canvas.create_image(x_center, y_center, anchor=tk.NW, image=img_tk, tags="image")
            canvas.itemconfigure(image_id, image=img_tk)
            canvas.image = img_tk  # 참조 유지
            
            # 이전 스크롤 위치 복원
            canvas.xview_moveto(scroll_x)
            canvas.yview_moveto(scroll_y)
            
            # 모든 ROI 영역 표시
            for f, data in field_selections.items():
                if data['coords'] is not None:
                    # 비율 좌표를 픽셀로 변환
                    x1, y1, x2, y2 = data['coords']
                    px1 = int(x1 * w * zoom) + x_center
                    py1 = int(y1 * h * zoom) + y_center
                    px2 = int(x2 * w * zoom) + x_center
                    py2 = int(y2 * h * zoom) + y_center
                    
                    # ROI 사각형 그리기
                    rect_id = canvas.create_rectangle(
                        px1, py1, px2, py2,
                        outline=self.field_colors[f],
                        width=3 if f == field else 1,  # 현재 선택 필드는 굵게
                        dash=(5, 5) if f != field else None,  # 현재 선택 필드가 아니면 점선
                        tags=f"selection_{f}"
                    )
                    
                    # 필드 이름 표시
                    canvas.create_text(
                        px1 + 5, py1 + 5,
                        text=f,
                        fill=self.field_colors[f],
                        font=("Gulim", 10, "bold"),
                        anchor=tk.NW,
                        tags=f"label_{f}"
                    )
                    
                    # 사각형 ID 저장
                    field_rectangles[f] = rect_id
            
            # 현재 선택된 필드의 정보 표시
            if field in field_selections and field_selections[field]['coords'] is not None:
                x1, y1, x2, y2 = field_selections[field]['coords']
                px1 = int(x1 * w * zoom) + x_center
                py1 = int(y1 * h * zoom) + y_center
                px2 = int(x2 * w * zoom) + x_center
                py2 = int(y2 * h * zoom) + y_center
                
                # 선택 영역 크기 계산
                width_px = abs(px2 - px1)
                height_px = abs(py2 - py1)
                
                # 정보 표시
                if roi_info_label:
                    roi_info_label.config(text=f"'{field}' 선택: ({x1:.3f}, {y1:.3f}) - ({x2:.3f}, {y2:.3f}) | "
                                       f"크기: {width_px}x{height_px}px")
            else:
                if roi_info_label:
                    roi_info_label.config(text=f"'{field}' 선택: 미설정")
            
            # 줌 정보 표시
            canvas.create_text(
                10, 10,
                text=f"줌: {zoom:.1f}x | 이미지: {new_w}x{new_h}",
                fill="white",
                font=("Gulim", 10),
                anchor=tk.NW,
                tags="zoom_info"
            )
            
        except Exception as e:
            logger.error(f"ROI 이미지 표시 오류: {e}")

    def on_roi_selection_start(self, event, canvas, field, field_selections, field_rectangles, 
                              roi_info_label, roi_zoom_var, roi_original_image):
        """ROI 선택 시작 (마우스 클릭)"""
        # 캔버스 좌표 얻기
        x = canvas.canvasx(event.x)
        y = canvas.canvasy(event.y)
        
        # 이미지 크기 및 오프셋
        h, w = roi_original_image.shape[:2]
        zoom = roi_zoom_var.get()
        offset_x = self.roi_image_offset_x
        offset_y = self.roi_image_offset_y
        
        # 이미지 영역 내에 있는지 확인
        if offset_x <= x < offset_x + w * zoom and offset_y <= y < offset_y + h * zoom:
            # 기존 선택 영역 삭제
            if field in field_rectangles:
                canvas.delete(field_rectangles[field])
                canvas.delete(f"label_{field}")
            
            # 선택 시작 위치 저장
            self.roi_selection_start_x = x
            self.roi_selection_start_y = y
            
            # 새 선택 영역 생성
            rect_id = canvas.create_rectangle(
                x, y, x, y,
                outline=self.field_colors[field],
                width=3,
                tags=f"selection_{field}"
            )
            
            # 사각형 ID 저장
            field_rectangles[field] = rect_id
            
            logger.info(f"ROI 선택 시작: 필드={field}, 위치=({x}, {y})")

    def on_roi_selection_drag(self, event, canvas, field, field_selections, field_rectangles, 
                             roi_info_label, roi_zoom_var, roi_original_image):
        """ROI 선택 드래그 (마우스 이동)"""
        if not hasattr(self, 'roi_selection_start_x') or self.roi_selection_start_x is None:
            return
        
        # 캔버스 좌표 얻기
        x = canvas.canvasx(event.x)
        y = canvas.canvasy(event.y)
        
        # 이미지 크기 및 오프셋
        h, w = roi_original_image.shape[:2]
        zoom = roi_zoom_var.get()
        offset_x = self.roi_image_offset_x
        offset_y = self.roi_image_offset_y
        
        # 선택 영역 업데이트
        if field in field_rectangles:
            canvas.coords(field_rectangles[field], self.roi_selection_start_x, self.roi_selection_start_y, x, y)
            
            # 이미지 좌표계로 변환
            x1 = min(self.roi_selection_start_x, x)
            y1 = min(self.roi_selection_start_y, y)
            x2 = max(self.roi_selection_start_x, x)
            y2 = max(self.roi_selection_start_y, y)
            
            # 이미지 상대 좌표 계산
            rel_x1 = (x1 - offset_x) / (w * zoom)
            rel_y1 = (y1 - offset_y) / (h * zoom)
            rel_x2 = (x2 - offset_x) / (w * zoom)
            rel_y2 = (y2 - offset_y) / (h * zoom)
            
            # 좌표 범위 제한 (0~1)
            rel_x1 = max(0, min(1, rel_x1))
            rel_y1 = max(0, min(1, rel_y1))
            rel_x2 = max(0, min(1, rel_x2))
            rel_y2 = max(0, min(1, rel_y2))
            
            # 선택 정보 업데이트
            field_selections[field]['coords'] = [rel_x1, rel_y1, rel_x2, rel_y2]
            field_selections[field]['label'].set(f"[{rel_x1:.2f}, {rel_y1:.2f}, {rel_x2:.2f}, {rel_y2:.2f}]")
            
            # 선택 영역 크기 계산
            width_px = abs(x2 - x1)
            height_px = abs(y2 - y1)
            
            # 정보 표시
            if roi_info_label:
                roi_info_label.config(text=f"'{field}' 선택: ({rel_x1:.3f}, {rel_y1:.3f}) - ({rel_x2:.3f}, {rel_y2:.3f}) | "
                                   f"크기: {width_px}x{height_px}px")

    def on_roi_selection_end(self, event, canvas, field, field_selections, field_rectangles, roi_info_label):
        """ROI 선택 종료 (마우스 버튼 놓기)"""
        if not hasattr(self, 'roi_selection_start_x') or self.roi_selection_start_x is None:
            return
        
        # 선택 완료 메시지
        if field in field_selections and field_selections[field]['coords'] is not None:
            coords = field_selections[field]['coords']
            logger.info(f"ROI 선택 완료: 필드={field}, 좌표={coords}")
            
            # 필드 이름 표시
            if field in field_rectangles:
                # 사각형 좌표 가져오기
                px1, py1, px2, py2 = canvas.coords(field_rectangles[field])
                
                # 필드 이름 라벨 추가
                canvas.create_text(
                    px1 + 5, py1 + 5,
                    text=field,
                    fill=self.field_colors[field],
                    font=("Gulim", 10, "bold"),
                    anchor=tk.NW,
                    tags=f"label_{field}"
                )
        
        # 선택 시작 위치 초기화
        self.roi_selection_start_x = None
        self.roi_selection_start_y = None
        
        # ROI 선택값 업데이트
        self.update_roi_selections(field_selections)

    def update_roi_selections(self, field_selections):
        """ROI 선택값 업데이트"""
        for field, data in field_selections.items():
            if data['coords'] is not None:
                self.roi_selections[field] = data['coords']

    def clear_roi_selection(self, canvas, field, field_selections, field_rectangles):
        """선택된 필드의 ROI 초기화"""
        if field in field_selections:
            # 선택 영역 초기화
            field_selections[field]['coords'] = None
            field_selections[field]['label'].set("미설정")
            
            # 캔버스에서 사각형 삭제 (캔버스가 제공된 경우)
            if canvas and field in field_rectangles:
                canvas.delete(field_rectangles[field])
                canvas.delete(f"label_{field}")
                field_rectangles.pop(field, None)
            
            # 저장된 ROI에서도 제거
            if field in self.roi_selections:
                del self.roi_selections[field]
            
            logger.info(f"ROI 초기화: 필드={field}")

    def save_all_roi_selections(self, window, field_selections):
        """모든 ROI 선택 영역 저장"""
        # 설정된 ROI 영역 확인
        valid_fields = {}
        empty_fields = []
        
        for field, data in field_selections.items():
            if data['coords'] is not None:
                valid_fields[field] = data['coords']
            else:
                empty_fields.append(field)
        
        # 설정되지 않은 필드가 있으면 확인
        if empty_fields:
            confirm = messagebox.askyesno(
                "확인",
                f"다음 필드의 ROI가 설정되지 않았습니다: {', '.join(empty_fields)}\n계속 진행하시겠습니까?"
            )
            if not confirm:
                return False
        
        # ROI 설정 저장
        self.roi_selections = valid_fields.copy()
        success = self.save_roi_config()
        
        if success:
            messagebox.showinfo("성공", "모든 ROI 영역이 저장되었습니다.")
            
            # 창 닫기 여부 확인
            if window:
                if messagebox.askyesno("확인", "저장 완료. 창을 닫으시겠습니까?"):
                    window.destroy()
            
            return True
        else:
            messagebox.showerror("오류", "ROI 설정 저장 중 오류가 발생했습니다.")
            return False

    def save_roi_as_preset(self, window, preset_name, field_selections):
        """현재 ROI 설정을 프리셋으로 저장"""
        preset_name = preset_name.strip()
        if not preset_name:
            messagebox.showwarning("경고", "프리셋 이름을 입력하세요.")
            return
        
        # 저장 전 ROI 설정 유효성 확인
        valid_selections = {}
        for field, data in field_selections.items():
            if data['coords'] is not None:
                valid_selections[field] = data['coords']
        
        if not valid_selections:
            messagebox.showwarning("경고", "저장할 ROI 설정이 없습니다.")
            return
        
        # 이미 있는 이름이면 확인
        if preset_name in self.roi_presets and not messagebox.askyesno("확인", f"'{preset_name}' 프리셋이 이미 존재합니다. 덮어쓰시겠습니까?"):
            return
        
        # 프리셋 저장
        self.roi_presets[preset_name] = valid_selections
        success = self.save_roi_presets()
        
        if success:
            # 기본 ROI 설정도 함께 업데이트
            self.roi_selections = valid_selections.copy()
            self.save_roi_config()
            
            messagebox.showinfo("완료", f"ROI 설정이 '{preset_name}' 프리셋으로 저장되었습니다.")
            
            # 추가 후 계속 편집하거나 창 닫기 선택
            if window and messagebox.askyesno("확인", "저장되었습니다. 창을 닫으시겠습니까?"):
                window.destroy()
        else:
            messagebox.showerror("오류", "프리셋 저장 중 오류가 발생했습니다.")

    def apply_preset(self, preset_name):
        """저장된 프리셋 적용"""
        if preset_name not in self.roi_presets:
            messagebox.showwarning("경고", f"'{preset_name}' 프리셋을 찾을 수 없습니다.")
            return False
        
        # 프리셋 로드
        preset_data = self.roi_presets[preset_name]
        
        # ROI 설정 업데이트
        self.roi_selections = preset_data.copy()
        success = self.save_roi_config()
        
        if success:
            messagebox.showinfo("성공", f"'{preset_name}' 프리셋이 적용되었습니다.")
            return True
        else:
            messagebox.showerror("오류", "프리셋 적용 중 오류가 발생했습니다.")
            return False

    def get_roi_selections(self):
        """현재 ROI 선택값 반환"""
        return self.roi_selections.copy()