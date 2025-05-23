# fc_card_recognition/ui/main_window.py
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import threading
import mss
import cv2
import numpy as np
from PIL import Image, ImageTk
from datetime import datetime

from ui.roi_selector import ROISelector
from ui.settings_dialog import SettingsDialog
from utils.file_manager import FileManager

logger = logging.getLogger("FC_Online_Recognition")

class MainWindow:
    """메인 창 UI 클래스"""
    def __init__(self, root, system):
        """초기화"""
        self.root = root
        self.system = system
        self.config = system.config
        
        # 창 설정
        self.root.title("FC 온라인 선수 카드 정보 인식 시스템")
        self.root.geometry("1400x900")
        self.root.minsize(1280, 800)
        
        # 파일 관리자
        self.file_manager = FileManager(self.config)
        
        # 캡처 관련 변수
        self.is_capturing = False
        self.capture_thread = None
        self.sct = mss.mss()
        
        # 현재 표시 중인 이미지 및 인식 정보
        self.current_image = None
        self.current_image_path = None
        
        # 줌/패닝 관련 변수
        self.zoom_factor = 1.0
        self.is_panning = False
        self.pan_start_x = None
        self.pan_start_y = None
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.old_zoom_factor = 1.0
        self.auto_resize = tk.BooleanVar(value=True)
        
        # UI 설정
        self.setup_ui()
        
        # 이미지 목록 로드
        self.refresh_image_list()
        
        # 창 크기 변경 이벤트 바인딩
        self.root.bind("<Configure>", self.on_window_resize)
        
        logger.info("메인 창 UI 초기화 완료")
    
    def setup_ui(self):
        """UI 구성 요소 설정"""
        # UI 크기 조정 비율
        ui_scale = float(self.config.get('settings', 'ui_scale', fallback='1.0'))
        
        # 기본 글꼴 크기
        default_font_size = int(10 * ui_scale)
        button_font_size = int(9 * ui_scale)
        
        # 글꼴 설정
        default_font = ('Gulim', default_font_size)
        button_font = ('Gulim', button_font_size)
        title_font = ('Gulim', int(12 * ui_scale), 'bold')
        
        # 테마 설정 (시스템/밝은/어두운)
        theme = self.config.get('settings', 'theme', fallback='system')
        self.apply_theme(theme)
        
        # 기본 글꼴 설정
        self.root.option_add('*Font', default_font)
        
        # 메인 프레임 (전체 레이아웃)
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 좌측 패널 (이미지 표시 및 확대/축소)
        self.left_panel = ttk.Frame(self.main_frame)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 이미지 표시 영역
        self.image_frame = ttk.LabelFrame(self.left_panel, text="카드 이미지")
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 컨트롤 프레임 추가
        control_frame = ttk.Frame(self.image_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        # 자동 크기 조정 옵션
        auto_resize_check = ttk.Checkbutton(
            control_frame,
            text="창 크기에 맞춤",
            variable=self.auto_resize,
            command=self.toggle_auto_resize
        )
        auto_resize_check.pack(side=tk.LEFT, padx=10)
        
        # 줌 버튼들
        zoom_btn_frame = ttk.Frame(control_frame)
        zoom_btn_frame.pack(side=tk.RIGHT, padx=5)
        
        # 1:1 원본 크기 버튼
        original_btn = ttk.Button(zoom_btn_frame, text="1:1 원본",
                            command=self.set_original_zoom)
        original_btn.pack(side=tk.LEFT, padx=5)
        
        # 창에 맞춤 버튼
        fit_btn = ttk.Button(zoom_btn_frame, text="창에 맞춤",
                        command=self.fit_image_to_canvas)
        fit_btn.pack(side=tk.LEFT, padx=5)
        
        # 이미지를 담을 캔버스 (스크롤 기능 포함)
        self.canvas_frame = ttk.Frame(self.image_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg='#f0f0f0', highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 스크롤바 추가
        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.h_scrollbar = ttk.Scrollbar(self.image_frame, orient="horizontal", command=self.canvas.xview)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)
        
        # 이미지 표시 레이블
        self.image_label = ttk.Label(self.canvas)
        self.canvas.create_window((0, 0), window=self.image_label, anchor="nw")
        
        # 캔버스 이벤트 바인딩 (줌/팬 기능)
        for widget in [self.canvas, self.image_label]:
            widget.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows
            widget.bind("<Button-4>", self.on_mouse_wheel)  # Linux 위로 스크롤
            widget.bind("<Button-5>", self.on_mouse_wheel)  # Linux 아래로 스크롤
            widget.bind("<ButtonPress-1>", self.on_pan_start)
            widget.bind("<B1-Motion>", self.on_pan_move)
            widget.bind("<ButtonRelease-1>", self.on_pan_end)
        
        # 컨텍스트 메뉴 (우클릭 메뉴) 바인딩
        self.canvas.bind("<ButtonPress-3>", self.show_context_menu)
        
        # 줌 컨트롤
        zoom_frame = ttk.Frame(self.image_frame)
        zoom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        ttk.Label(zoom_frame, text="줌:").pack(side=tk.LEFT, padx=5)
        
        self.zoom_scale = tk.Scale(zoom_frame, from_=0.5, to=3.0, resolution=0.1,
                                 orient=tk.HORIZONTAL, command=self.on_zoom_change, length=200)
        self.zoom_scale.set(1.0)
        self.zoom_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        zoom_reset_btn = ttk.Button(zoom_frame, text="리셋", command=lambda: self.zoom_scale.set(1.0))
        zoom_reset_btn.pack(side=tk.LEFT, padx=5)
        
        # 디버그 영역 (인식된 영역 표시)
        self.debug_frame = ttk.LabelFrame(self.left_panel, text="인식 영역")
        self.debug_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.debug_canvas = tk.Canvas(self.debug_frame, height=150, bg='#f0f0f0')
        self.debug_canvas.pack(fill=tk.X, padx=5, pady=5)
        
        # 우측 패널 (컨트롤 및 결과)
        self.right_panel = ttk.Frame(self.main_frame, width=int(320 * ui_scale))
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)
        self.right_panel.pack_propagate(False)  # 크기 고정
        
        # 탭 컨트롤 추가 (기본 기능 / 배치 처리 / 설정)
        self.tab_control = ttk.Notebook(self.right_panel)
        self.tab_control.pack(fill=tk.BOTH, expand=True)
        
        # 기본 기능 탭
        self.basic_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.basic_tab, text="기본 기능")
        
        # 배치 처리 탭
        self.batch_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.batch_tab, text="배치 처리")
        
        # 설정 탭
        self.settings_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.settings_tab, text="설정")
        
        # 각 탭 내용 설정
        self.setup_basic_tab()
        self.setup_batch_tab()
        self.setup_settings_tab()
        
        # 상태 표시줄
        self.status_var = tk.StringVar()
        self.status_var.set("준비됨")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                                  relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 진행 상태 표시 프로그레스 바
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(self.root, mode='determinate', variable=self.progress_var)
        self.progress_bar.pack(side=tk.BOTTOM, fill=tk.X, before=self.status_bar)
        self.progress_bar.pack_forget()  # 기본적으로 숨김
    
    def setup_basic_tab(self):
        """기본 기능 탭 설정"""
        # 캡처 컨트롤
        self.capture_frame = ttk.LabelFrame(self.basic_tab, text="화면 캡처")
        self.capture_frame.pack(fill=tk.X, padx=3, pady=2)
        
        # 캡처 디렉토리 설정
        dir_frame = ttk.Frame(self.capture_frame)
        dir_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(dir_frame, text="캡처 폴더:").pack(side=tk.LEFT, padx=5)
        
        self.dir_var = tk.StringVar(value=self.config.get_path('captures_dir'))
        dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var)
        dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        dir_btn = ttk.Button(dir_frame, text="변경", command=self.change_captures_dir)
        dir_btn.pack(side=tk.LEFT, padx=5)
        
        # 캡처 버튼 (크게 만들기)
        capture_btn_frame = ttk.Frame(self.capture_frame)
        capture_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.capture_btn = ttk.Button(capture_btn_frame, text="연속 캡처 시작", 
                                    command=self.toggle_capture, style='Big.TButton')
        self.capture_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=5)
        
        self.single_capture_btn = ttk.Button(capture_btn_frame, text="한 번 캡처", 
                                           command=self.capture_once, style='Big.TButton')
        self.single_capture_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=2, pady=5)
        
        # 이미지 로드 버튼
        self.load_image_btn = ttk.Button(self.capture_frame, text="이미지 파일 로드", 
                                       command=self.load_image, style='Big.TButton')
        self.load_image_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # 옵션 프레임
        options_frame = ttk.Frame(self.capture_frame)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 자동 학습 옵션
        self.auto_learning_var = tk.BooleanVar(value=self.config.get('settings', 'auto_learning'))
        self.auto_learning_check = ttk.Checkbutton(
            options_frame, 
            text="자동 학습", 
            variable=self.auto_learning_var,
            command=self.toggle_auto_learning
        )
        self.auto_learning_check.pack(side=tk.LEFT, padx=5)
        
        # 수동 ROI 설정 옵션
        self.use_manual_roi_var = tk.BooleanVar(value=self.config.get('settings', 'use_manual_roi'))
        self.use_manual_roi_check = ttk.Checkbutton(
            options_frame,
            text="수동 ROI",
            variable=self.use_manual_roi_var,
            command=self.toggle_manual_roi
        )
        self.use_manual_roi_check.pack(side=tk.LEFT, padx=5)
        
        # 디버그 모드 옵션
        self.debug_mode_var = tk.BooleanVar(value=self.config.get('settings', 'debug_mode'))
        self.debug_mode_check = ttk.Checkbutton(
            options_frame,
            text="디버그 모드",
            variable=self.debug_mode_var,
            command=self.toggle_debug_mode
        )
        self.debug_mode_check.pack(side=tk.LEFT, padx=5)
        
        # 인식 결과 표시 영역
        self.result_frame = ttk.LabelFrame(self.basic_tab, text="인식 결과")
        self.result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 스타일 설정 (높은 신뢰도 = 녹색, 낮은 신뢰도 = 빨간색)
        style = ttk.Style()
        style.configure("High.TEntry", foreground="green")
        style.configure("Medium.TEntry", foreground="orange")
        style.configure("Low.TEntry", foreground="red")
        style.configure("Big.TButton", padding=5)
        
        # 인식 결과 필드
        self.result_fields = {}
        self.result_entries = {}
        self.confidence_labels = {}
        
        # 필드별 레이블 설정
        fields = [
            ('overall', '오버롤'),
            ('position', '포지션'),
            ('season_icon', '시즌 아이콘'),
            ('salary', '급여'),
            ('player_name', '선수 이름'),
            ('enhance_level', '강화 레벨'),
            ('boost_level', '부스트 레벨(%)')
        ]
        
        for field, label in fields:
            frame = tk.Frame(self.result_frame)
            frame.pack(fill=tk.X, padx=2, pady=2)
            
            lbl = tk.Label(frame, text=f"{label}:", width=12, anchor='e')
            lbl.pack(side=tk.LEFT, padx=2)

            var = tk.StringVar()
            entry = ttk.Entry(frame, textvariable=var, width=15)
            entry.pack(side=tk.LEFT, padx=2)
            
            # 신뢰도 표시 레이블
            conf_var = tk.StringVar(value="")
            conf_label = tk.Label(frame, textvariable=conf_var, width=15)
            conf_label.pack(side=tk.LEFT, padx=3)
            
            self.result_fields[field] = var
            self.result_entries[field] = entry
            self.confidence_labels[field] = conf_var
        
        # 수정 적용 버튼
        self.apply_btn = ttk.Button(self.result_frame, text="수정 적용 및 학습", 
                                  command=self.apply_correction, style='Big.TButton')
        self.apply_btn.pack(fill=tk.X, padx=10, pady=10)
        
        # 이미지 브라우저
        self.browser_frame = ttk.LabelFrame(self.basic_tab, text="이미지 브라우저")
        self.browser_frame.pack(fill=tk.BOTH, padx=5, pady=5)
        
        # 검색 프레임 추가
        search_frame = ttk.Frame(self.browser_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(search_frame, text="검색:").pack(side=tk.LEFT, padx=2)
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        search_entry.bind("<KeyRelease>", self.filter_image_list)
        
        ttk.Button(search_frame, text="✕", width=3, 
                command=lambda: [self.search_var.set(""), self.filter_image_list(None)]).pack(side=tk.LEFT)
        
        # 이미지 목록
        self.image_listbox = tk.Listbox(self.browser_frame, height=4)
        self.image_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.image_listbox.bind('<<ListboxSelect>>', self.on_image_select)
        
        # 이미지 목록 스크롤바
        image_scrollbar = ttk.Scrollbar(self.image_listbox, orient="vertical", command=self.image_listbox.yview)
        image_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.image_listbox.configure(yscrollcommand=image_scrollbar.set)
        
        browser_btn_frame = ttk.Frame(self.browser_frame)
        browser_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.refresh_btn = ttk.Button(browser_btn_frame, text="새로고침", 
                                    command=self.refresh_image_list)
        self.refresh_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.delete_btn = ttk.Button(browser_btn_frame, text="삭제", 
                                   command=self.delete_selected_image)
        self.delete_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # 추가 버튼들 프레임
        buttons_frame = ttk.Frame(self.basic_tab)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 첫 번째 줄 버튼들
        btn_row1 = ttk.Frame(buttons_frame)
        btn_row1.pack(fill=tk.X, pady=2)
        
        self.show_training_btn = ttk.Button(btn_row1, text="학습 상태 확인", 
                                          command=self.show_training_stats, style='Big.TButton')
        self.show_training_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        debug_btn = ttk.Button(btn_row1, text="ROI 영역 디버깅", 
                             command=self.debug_roi_detection, style='Big.TButton')
        debug_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # 두 번째 줄 버튼들
        btn_row2 = ttk.Frame(buttons_frame)
        btn_row2.pack(fill=tk.X, pady=2)
        
        manual_roi_btn = ttk.Button(btn_row2, text="수동 ROI 설정", 
                                  command=self.show_roi_selector, style='Big.TButton')
        manual_roi_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        export_btn = ttk.Button(btn_row2, text="결과 내보내기", 
                             command=self.export_results, style='Big.TButton')
        export_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
    
    def setup_batch_tab(self):
        """배치 처리 탭 설정"""
        # 배치 처리 프레임
        batch_frame = ttk.LabelFrame(self.batch_tab, text="배치 이미지 처리")
        batch_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 소스 디렉토리 선택
        source_frame = ttk.Frame(batch_frame)
        source_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(source_frame, text="소스 폴더:").pack(side=tk.LEFT, padx=5)
        
        self.batch_source_var = tk.StringVar(value=self.config.get_path('captures_dir'))
        source_entry = ttk.Entry(source_frame, textvariable=self.batch_source_var)
        source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        source_btn = ttk.Button(source_frame, text="선택", 
                               command=self.select_batch_source)
        source_btn.pack(side=tk.LEFT, padx=5)
        
        # 결과 저장 디렉토리 선택
        dest_frame = ttk.Frame(batch_frame)
        dest_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(dest_frame, text="결과 폴더:").pack(side=tk.LEFT, padx=5)
        
        self.batch_dest_var = tk.StringVar(value=os.path.join(self.config.get_path('base_dir'), "batch_results"))
        dest_entry = ttk.Entry(dest_frame, textvariable=self.batch_dest_var)
        dest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        dest_btn = ttk.Button(dest_frame, text="선택", 
                             command=self.select_batch_dest)
        dest_btn.pack(side=tk.LEFT, padx=5)
        
        # 파일 필터 프레임
        filter_frame = ttk.Frame(batch_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="파일 필터:").pack(side=tk.LEFT, padx=5)
        
        self.batch_filter_var = tk.StringVar(value="*.jpg;*.jpeg;*.png")
        filter_entry = ttk.Entry(filter_frame, textvariable=self.batch_filter_var)
        filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 배치 설정 프레임
        config_frame = ttk.Frame(batch_frame)
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 병렬 처리 수
        ttk.Label(config_frame, text="병렬 처리:").pack(side=tk.LEFT, padx=5)
        
        self.batch_parallel_var = tk.IntVar(value=int(self.config.get('batch', 'parallel_jobs')))
        parallel_spinbox = ttk.Spinbox(config_frame, from_=1, to=16, textvariable=self.batch_parallel_var, width=5)
        parallel_spinbox.pack(side=tk.LEFT, padx=5)
        
        # 자동 교정 옵션
        self.batch_autocorrect_var = tk.BooleanVar(value=True)
        autocorrect_check = ttk.Checkbutton(
            config_frame,
            text="자동 교정",
            variable=self.batch_autocorrect_var
        )
        autocorrect_check.pack(side=tk.LEFT, padx=5)
        
        # 오류 시 중지 옵션
        self.batch_stop_on_error_var = tk.BooleanVar(value=False)
        stop_on_error_check = ttk.Checkbutton(
            config_frame,
            text="오류 시 중지",
            variable=self.batch_stop_on_error_var
        )
        stop_on_error_check.pack(side=tk.LEFT, padx=5)
        
        # 결과 형식 선택
        format_frame = ttk.Frame(batch_frame)
        format_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(format_frame, text="결과 형식:").pack(side=tk.LEFT, padx=5)
        
        self.batch_format_var = tk.StringVar(value="CSV")
        format_combo = ttk.Combobox(format_frame, textvariable=self.batch_format_var,
                                   values=["CSV", "JSON", "텍스트", "엑셀"], state='readonly')
        format_combo.pack(side=tk.LEFT, padx=5)
        
        # 파일 찾기 버튼
        find_frame = ttk.Frame(batch_frame)
        find_frame.pack(fill=tk.X, padx=5, pady=5)
        
        find_btn = ttk.Button(find_frame, text="파일 찾기", 
                            command=self.find_batch_files, style='Big.TButton')
        find_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # 찾은 파일 목록
        list_frame = ttk.LabelFrame(batch_frame, text="처리할 파일 목록")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.batch_files_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        self.batch_files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 파일 목록 스크롤바
        files_scrollbar = ttk.Scrollbar(self.batch_files_listbox, orient="vertical", 
                                      command=self.batch_files_listbox.yview)
        files_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.batch_files_listbox.configure(yscrollcommand=files_scrollbar.set)
        
        # 배치 버튼 프레임
        batch_btn_frame = ttk.Frame(batch_frame)
        batch_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.batch_count_label = ttk.Label(batch_btn_frame, text="선택된 파일: 0개")
        self.batch_count_label.pack(side=tk.LEFT, padx=5)
        
        # 선택 삭제 버튼
        remove_selected_btn = ttk.Button(batch_btn_frame, text="선택 삭제", 
                                       command=self.remove_selected_batch_files)
        remove_selected_btn.pack(side=tk.LEFT, padx=5)
        
        # 모두 선택 버튼
        select_all_btn = ttk.Button(batch_btn_frame, text="모두 선택", 
                                  command=self.select_all_batch_files)
        select_all_btn.pack(side=tk.LEFT, padx=5)
        
        # 모두 해제 버튼
        clear_all_btn = ttk.Button(batch_btn_frame, text="모두 해제", 
                                 command=self.clear_all_batch_files)
        clear_all_btn.pack(side=tk.LEFT, padx=5)
        
        # 배치 처리 실행 버튼
        process_frame = ttk.Frame(batch_frame)
        process_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.batch_process_btn = ttk.Button(process_frame, text="배치 처리 시작", 
                                         command=self.start_batch_processing, style='Big.TButton')
        self.batch_process_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # 배치 처리 상태 레이블
        self.batch_status_var = tk.StringVar(value="준비됨")
        batch_status_label = ttk.Label(batch_frame, textvariable=self.batch_status_var)
        batch_status_label.pack(fill=tk.X, padx=5, pady=5)
    
    def setup_settings_tab(self):
        """설정 탭 설정"""
        # 설정 관리는 별도 대화상자로 처리
        settings_btn = ttk.Button(self.settings_tab, text="설정 관리", 
                                command=self.show_settings_dialog, style='Big.TButton')
        settings_btn.pack(padx=20, pady=20)
        
        # 백업 관리 프레임
        backup_frame = ttk.LabelFrame(self.settings_tab, text="백업 관리")
        backup_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 백업 버튼
        backup_btn = ttk.Button(backup_frame, text="백업 생성", 
                              command=self.create_backup, style='Big.TButton')
        backup_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # 복원 버튼
        restore_btn = ttk.Button(backup_frame, text="백업 복원", 
                               command=self.restore_backup, style='Big.TButton')
        restore_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # 백업 관리 버튼
        manage_btn = ttk.Button(backup_frame, text="백업 관리", 
                              command=self.manage_backups, style='Big.TButton')
        manage_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # 유틸리티 프레임
        utils_frame = ttk.LabelFrame(self.settings_tab, text="유틸리티")
        utils_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 캐시 지우기 버튼
        clear_cache_btn = ttk.Button(utils_frame, text="캐시 지우기", 
                                   command=self.clear_cache, style='Big.TButton')
        clear_cache_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # 학습 데이터 정리 버튼
        cleanup_train_btn = ttk.Button(utils_frame, text="학습 데이터 정리", 
                                     command=self.cleanup_training_data, style='Big.TButton')
        cleanup_train_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # 테마 변경 프레임
        theme_frame = ttk.Frame(utils_frame)
        theme_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(theme_frame, text="테마:").pack(side=tk.LEFT, padx=5)
        
        self.theme_var = tk.StringVar(value=self.config.get('settings', 'theme'))
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var,
                                 values=["system", "light", "dark"], state='readonly')
        theme_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        theme_apply_btn = ttk.Button(theme_frame, text="적용", 
                                   command=lambda: self.apply_theme(self.theme_var.get()))
        theme_apply_btn.pack(side=tk.LEFT, padx=5)
        
        # 시스템 정보 프레임
        info_frame = ttk.LabelFrame(self.settings_tab, text="시스템 정보")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 정보 텍스트
        info_text = tk.Text(info_frame, height=10, wrap=tk.WORD)
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 시스템 정보 추가
        info_text.insert(tk.END, "FC 온라인 선수 카드 정보 인식 시스템\n\n")
        
        try:
            # TensorFlow 버전
            import tensorflow as tf
            info_text.insert(tk.END, f"TensorFlow 버전: {tf.__version__}\n")
            
            # GPU 정보
            gpus = tf.config.list_physical_devices('GPU')
            gpu_info = f"{len(gpus)}개 발견" if gpus else "사용 불가"
            info_text.insert(tk.END, f"GPU: {gpu_info}\n")
        except:
            info_text.insert(tk.END, "TensorFlow: 설치되지 않음\n")
            info_text.insert(tk.END, "GPU: 확인 불가\n")
        
        # OpenCV 버전
        info_text.insert(tk.END, f"OpenCV 버전: {cv2.__version__}\n")
        
        # Tesseract 경로
        tesseract_path = self.config.get('settings', 'tesseract_path')
        info_text.insert(tk.END, f"Tesseract 경로: {tesseract_path}\n")
        
        # 캐시 정보
        cache_size = 0
        if hasattr(self.system.recognizer, 'ocr_cache'):
            cache_size = len(self.system.recognizer.ocr_cache)
        info_text.insert(tk.END, f"OCR 캐시 항목: {cache_size}개\n")
        
        # 읽기 전용 설정
        info_text.config(state=tk.DISABLED)
    
    def apply_theme(self, theme):
        """UI 테마 적용"""
        # 테마 설정 저장
        self.config.set('settings', 'theme', theme)
        
        try:
            style = ttk.Style()
            
            if theme == "system":
                # 시스템 테마 (Windows의 경우 vista, macOS/Linux의 경우 clam)
                if os.name == 'nt':
                    style.theme_use('vista')
                else:
                    style.theme_use('clam')
            elif theme == "light":
                # 밝은 테마
                style.theme_use('clam')
                
                # 배경색 및 전경색 설정
                style.configure('TFrame', background='#f0f0f0')
                style.configure('TLabelframe', background='#f0f0f0')
                style.configure('TLabelframe.Label', background='#f0f0f0', foreground='#000000')
                style.configure('TLabel', background='#f0f0f0', foreground='#000000')
                style.configure('TButton', background='#e0e0e0', foreground='#000000')
                style.configure('TCheckbutton', background='#f0f0f0', foreground='#000000')
                style.configure('TRadiobutton', background='#f0f0f0', foreground='#000000')
                style.configure('TEntry', fieldbackground='#ffffff', foreground='#000000')
                style.configure('TCombobox', fieldbackground='#ffffff', foreground='#000000')
                style.configure('TNotebook', background='#f0f0f0')
                style.configure('TNotebook.Tab', background='#e0e0e0', foreground='#000000')
                
                # 캔버스 배경색 변경
                if hasattr(self, 'canvas'):
                    self.canvas.config(bg='#f0f0f0')
                if hasattr(self, 'debug_canvas'):
                    self.debug_canvas.config(bg='#f0f0f0')
            elif theme == "dark":
                # 어두운 테마
                style.theme_use('clam')
                
                # 배경색 및 전경색 설정
                style.configure('TFrame', background='#2d2d2d')
                style.configure('TLabelframe', background='#2d2d2d')
                style.configure('TLabelframe.Label', background='#2d2d2d', foreground='#ffffff')
                style.configure('TLabel', background='#2d2d2d', foreground='#ffffff')
                style.configure('TButton', background='#404040', foreground='#ffffff')
                style.configure('TCheckbutton', background='#2d2d2d', foreground='#ffffff')
                style.configure('TRadiobutton', background='#2d2d2d', foreground='#ffffff')
                style.configure('TEntry', fieldbackground='#404040', foreground='#ffffff')
                style.configure('TCombobox', fieldbackground='#404040', foreground='#ffffff')
                style.configure('TNotebook', background='#2d2d2d')
                style.configure('TNotebook.Tab', background='#404040', foreground='#ffffff')
                
                # 캔버스 배경색 변경
                if hasattr(self, 'canvas'):
                    self.canvas.config(bg='#404040')
                if hasattr(self, 'debug_canvas'):
                    self.debug_canvas.config(bg='#404040')
            
            logger.info(f"테마 적용됨: {theme}")
            self.status_var.set(f"테마 변경됨: {theme}")
            return True
        except Exception as e:
            logger.error(f"테마 적용 오류: {e}")
            self.status_var.set(f"테마 적용 오류: {e}")
            return False
    
    def on_window_resize(self, event):
        """창 크기 변경 이벤트 처리"""
        # 이벤트 발생 위젯이 루트 윈도우일 때만 처리
        if event.widget == self.root:
            # 자동 크기 조정이 활성화되어 있으면 이미지 크기 조정
            if hasattr(self, 'auto_resize') and self.auto_resize.get():
                # 약간의 지연 후 조정 (너무 빈번한 업데이트 방지)
                self.root.after(100, self.fit_image_to_canvas)
    
    def toggle_auto_resize(self):
        """자동 크기 조정 토글"""
        if self.auto_resize.get():
            self.fit_image_to_canvas()
        else:
            # 현재 줌 유지
            self.update_zoom()
    
    def set_original_zoom(self):
        """이미지를 원본 크기(1:1)로 설정"""
        self.zoom_factor = 1.0
        self.auto_resize.set(False)
        self.update_zoom()
        self.zoom_scale.set(1.0)
    
    def fit_image_to_canvas(self):
        """이미지를 캔버스에 맞게 조정"""
        if self.current_image is None:
            return
        
        # 캔버스 크기 가져오기
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # 캔버스 크기가 유효하지 않으면 부모 위젯 크기 사용
        if canvas_width <= 1:
            canvas_width = self.canvas_frame.winfo_width() - 30  # 스크롤바 공간 고려
        if canvas_height <= 1:
            canvas_height = self.canvas_frame.winfo_height() - 30  # 스크롤바 공간 고려
        
        # 이미지 크기
        h, w = self.current_image.shape[:2]
        
        # 캔버스에 맞는 줌 계산
        width_ratio = canvas_width / w
        height_ratio = canvas_height / h
        
        # 이미지가 캔버스에 딱 맞게 (작은 쪽 비율 사용)
        fit_zoom = min(width_ratio, height_ratio) * 0.9  # 여유 공간 10%
        
        # 줌 팩터 업데이트
        self.zoom_factor = fit_zoom
        
        # 줌 스케일 업데이트
        if hasattr(self, 'zoom_scale'):
            self.zoom_scale.set(fit_zoom)
        
        # 이미지 업데이트
        self.update_zoom()
    
    def on_mouse_wheel(self, event):
        """마우스 휠 이벤트 핸들러 (줌 기능)"""
        if self.current_image is None:
            return
        
        # 자동 크기 조정 비활성화
        self.auto_resize.set(False)
        
        # 스크롤 방향에 따른 줌 조정
        delta = 0.1  # 줌 단위
        
        # 이벤트 플랫폼 분기
        if event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):  # 아래로 스크롤 - 축소
            new_zoom = max(0.1, self.zoom_factor - delta)
        elif event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):  # 위로 스크롤 - 확대
            new_zoom = min(5.0, self.zoom_factor + delta)
        else:
            return  # 알 수 없는 이벤트
        
        # 이전 줌 저장
        old_zoom = self.zoom_factor
        
        # 줌 스케일 및 팩터 업데이트
        self.zoom_factor = new_zoom
        if hasattr(self, 'zoom_scale'):
            self.zoom_scale.set(new_zoom)
        
        # 마우스 위치 (캔버스 좌표계)
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # 특정 지점(마우스 위치)을 중심으로 줌
        self.update_zoom(center_x=x, center_y=y)
        
        # 상태 업데이트
        self.status_var.set(f"줌: {self.zoom_factor:.1f}x")
    
    def on_zoom_change(self, val):
        """줌 슬라이더 변경 이벤트 핸들러"""
        # 자동 크기 조정 비활성화
        self.auto_resize.set(False)
        
        # 줌 팩터 업데이트
        self.zoom_factor = float(val)
        
        # 이미지 업데이트
        self.update_zoom()
    
    def update_zoom(self, center_x=None, center_y=None):
        """현재 줌 팩터에 따라 이미지 업데이트"""
        if self.current_image is None:
            return
        
        # 이미지 크기 계산 (비율 유지)
        height, width = self.current_image.shape[:2]
        new_width = int(width * self.zoom_factor)
        new_height = int(height * self.zoom_factor)
        
        # 이미지 크기 조정 (비율 유지)
        resized_image = cv2.resize(self.current_image, (new_width, new_height), 
                                interpolation=cv2.INTER_AREA)
        
        # 이미지를 Tkinter에서 표시 가능한 형식으로 변환
        img_rgb = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
        img_tk = ImageTk.PhotoImage(image=Image.fromarray(img_rgb))
        
        # 캔버스 크기 및 현재 스크롤 위치 획득
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # 캔버스 크기가 유효하지 않으면 부모 위젯 크기 사용
        if canvas_width <= 1:
            canvas_width = self.canvas_frame.winfo_width() - 30
        if canvas_height <= 1:
            canvas_height = self.canvas_frame.winfo_height() - 30
        
        # 현재 스크롤 위치 (0.0 ~ 1.0)
        try:
            scroll_x = self.canvas.xview()[0]
            scroll_y = self.canvas.yview()[0]
        except:
            scroll_x = 0
            scroll_y = 0
        
        # 기존 오프셋 저장
        old_offset_x = getattr(self, 'image_offset_x', 0)
        old_offset_y = getattr(self, 'image_offset_y', 0)
        
        # 기존 줌 저장
        old_zoom = getattr(self, 'old_zoom_factor', 1.0)
        
        # 스크롤 영역을 이미지보다 약간 크게 설정
        scroll_width = max(new_width + 100, canvas_width)
        scroll_height = max(new_height + 100, canvas_height)
        self.canvas.config(scrollregion=(0, 0, scroll_width, scroll_height))
        
        # 이미지 중앙 위치 계산
        x_center = max(0, (scroll_width - new_width) // 2)
        y_center = max(0, (scroll_height - new_height) // 2)
        
        # 이미지 위치 저장
        self.image_offset_x = x_center
        self.image_offset_y = y_center
        
        # 이미지 라벨 업데이트
        self.image_label.config(image=img_tk)
        self.image_label.image = img_tk  # 참조 유지

        # 이미지 창에 배치
        if hasattr(self, 'image_id'):
            self.canvas.delete(self.image_id)
        self.image_id = self.canvas.create_window((x_center, y_center), window=self.image_label, anchor="nw")

        # 특정 지점을 중심으로 줌 (마우스 휠 이벤트에서 사용)
        if center_x is not None and center_y is not None and old_zoom > 0:
            try:
                # 줌 전 상대적 위치 계산
                rel_x = (center_x - old_offset_x) / (width * old_zoom)
                rel_y = (center_y - old_offset_y) / (height * old_zoom)

                # 상대 위치가 0~1 범위 내에 있는지 확인
                rel_x = max(0, min(1, rel_x))
                rel_y = max(0, min(1, rel_y))
                
                # 줌 후 픽셀 위치 계산
                new_center_x = x_center + (rel_x * new_width)
                new_center_y = y_center + (rel_y * new_height)
                
                # 스크롤 위치 조정
                self.canvas.xview_moveto((new_center_x - canvas_width/2) / scroll_width)
                self.canvas.yview_moveto((new_center_y - canvas_height/2) / scroll_height)
            except Exception as e:
                logger.error(f"줌 중심점 조정 오류: {e}")
                # 오류 발생 시 기본 중앙 위치
                self.canvas.xview_moveto((scroll_width - canvas_width) / (2 * scroll_width))
                self.canvas.yview_moveto((scroll_height - canvas_height) / (2 * scroll_height))
        else:
            # 일반적인 경우 이전 스크롤 위치 유지 또는 중앙으로
            if self.auto_resize.get():
                # 자동 크기 조정 시 중앙으로
                self.canvas.xview_moveto((scroll_width - canvas_width) / (2 * scroll_width))
                self.canvas.yview_moveto((scroll_height - canvas_height) / (2 * scroll_height))
            else:
                # 이전 스크롤 위치 유지
                self.canvas.xview_moveto(scroll_x)
                self.canvas.yview_moveto(scroll_y)
        
        # 현재 줌 저장 (다음 줌에서 참조)
        self.old_zoom_factor = self.zoom_factor
        
        # 상태 업데이트
        self.status_var.set(f"줌: {self.zoom_factor:.1f}x | 이미지 크기: {new_width}x{new_height}")
    
    def on_pan_start(self, event):
        """패닝 시작 이벤트 핸들러"""
        if self.current_image is None:
            return
        
        # 패닝 모드 활성화
        self.is_panning = True
        
        # 시작 지점 저장 (캔버스 좌표계)
        self.pan_start_x = self.canvas.canvasx(event.x)
        self.pan_start_y = self.canvas.canvasy(event.y)
        
        # 커서 변경
        self.canvas.config(cursor="fleur")  # 손 모양 커서
    
    def on_pan_move(self, event):
        """패닝 중 이벤트 핸들러"""
        if not self.is_panning or self.current_image is None:
            return
        
        # 현재 위치 (캔버스 좌표계)
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # 이동 거리 계산
        dx = self.pan_start_x - x
        dy = self.pan_start_y - y
        
        # 캔버스 스크롤 이동 (보정 계수 적용)
        self.canvas.xview_scroll(int(dx/5), "units")
        self.canvas.yview_scroll(int(dy/5), "units")
        
        # 시작점 업데이트 (연속 이동용)
        self.pan_start_x = x
        self.pan_start_y = y
    
    def on_pan_end(self, event):
        """패닝 종료 이벤트 핸들러"""
        # 패닝 모드 비활성화
        self.is_panning = False
        
        # 시작점 초기화
        self.pan_start_x = None
        self.pan_start_y = None
        
        # 커서 복원
        self.canvas.config(cursor="")
    
    def show_context_menu(self, event):
        """컨텍스트 메뉴(우클릭 메뉴) 표시"""
        if self.current_image is None:
            return
        
        context_menu = tk.Menu(self.canvas, tearoff=0)
        
        # 확대/축소 메뉴
        context_menu.add_command(label="원본 크기 (1:1)", command=self.set_original_zoom)
        context_menu.add_command(label="창에 맞춤", command=self.fit_image_to_canvas)
        
        # 구분선
        context_menu.add_separator()
        
        # ROI 관련 메뉴
        context_menu.add_command(label="ROI 영역 설정", command=self.show_roi_selector)
        context_menu.add_command(label="ROI 영역 디버깅", command=self.debug_roi_detection)
        
        # 구분선
        context_menu.add_separator()
        
        # 이미지 관련 메뉴
        context_menu.add_command(label="저장", command=self.save_current_image)
        context_menu.add_command(label="다른 이름으로 저장", command=self.save_current_image_as)
        
        # 팝업 메뉴 표시
        context_menu.tk_popup(event.x_root, event.y_root)
    
    # 이 이후에 구현할 기능들:
    # 1. 캡처 관련 기능들
    # 2. 이미지 처리 기능들
    # 3. 배치 처리 기능들
    # 4. 설정 관련 기능들
    # 5. 백업 관련 기능들
    # 등...