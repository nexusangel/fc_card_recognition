# ui/settings_dialog.py - FC 온라인 선수 카드 인식 시스템 설정 대화상자

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Scale
import logging
from pathlib import Path

# 로거 설정
logger = logging.getLogger("FC_Online_Recognition.ui.settings_dialog")

class SettingsDialog:
    """설정 대화상자 클래스"""
    
    def __init__(self, parent, system_manager):
        """
        설정 대화상자 초기화
        
        Args:
            parent: 부모 윈도우
            system_manager: SystemManager 인스턴스
        """
        self.parent = parent
        self.system_manager = system_manager
        
        # 설정 대화상자 생성
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("설정")
        self.dialog.geometry("750x650")
        self.dialog.minsize(600, 500)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 대화상자를 화면 중앙에 배치
        self._center_window()
        
        # 설정 값 로드
        self._load_settings()
        
        # UI 구성
        self._create_widgets()
        
        # 대화상자 모달로 설정
        self.dialog.focus_set()
        
        logger.info("설정 대화상자 초기화 완료")
    
    def _center_window(self):
        """대화상자를 화면 중앙에 배치"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def _load_settings(self):
        """설정 값 로드"""
        # 일반 설정
        self.ui_scale_var = tk.DoubleVar(value=float(self.system_manager.config.get('Settings', 'ui_scale', fallback='1.0')))
        self.theme_var = tk.StringVar(value=self.system_manager.config.get('Settings', 'theme', fallback='system'))
        self.capture_interval_var = tk.DoubleVar(value=float(self.system_manager.config.get('Settings', 'capture_interval', fallback='1.0')))
        self.auto_backup_var = tk.BooleanVar(value=self.system_manager.config.getboolean('Settings', 'auto_backup', fallback=True))
        
        # 성능 최적화 설정
        self.enable_caching_var = tk.BooleanVar(value=self.system_manager.config.getboolean('Settings', 'enable_caching', fallback=True))
        self.confidence_threshold_var = tk.DoubleVar(value=float(self.system_manager.config.get('Settings', 'confidence_threshold', fallback='0.7')))
        self.parallel_jobs_var = tk.IntVar(value=int(self.system_manager.config.get('Batch', 'parallel_jobs', fallback='4')))
        
        # 고급 설정
        self.tesseract_path_var = tk.StringVar(value=self.system_manager.config.get('Settings', 'tesseract_path', fallback=''))
        self.auto_learning_var = tk.BooleanVar(value=self.system_manager.config.getboolean('Settings', 'auto_learning', fallback=True))
        self.debug_mode_var = tk.BooleanVar(value=self.system_manager.config.getboolean('Settings', 'debug_mode', fallback=True))
        self.use_manual_roi_var = tk.BooleanVar(value=self.system_manager.config.getboolean('Settings', 'use_manual_roi', fallback=True))
        
        # 경로 설정
        self.captures_dir_var = tk.StringVar(value=self.system_manager.config.get('Paths', 'captures_dir', fallback=self.system_manager.captures_dir))
        self.models_dir_var = tk.StringVar(value=self.system_manager.config.get('Paths', 'models_dir', fallback=self.system_manager.models_dir))
        self.training_data_dir_var = tk.StringVar(value=self.system_manager.config.get('Paths', 'training_data_dir', fallback=self.system_manager.training_data_dir))
        self.backup_dir_var = tk.StringVar(value=self.system_manager.config.get('Paths', 'backup_dir', fallback=self.system_manager.backup_dir))
        
        # 배치 처리 설정
        self.max_batch_size_var = tk.IntVar(value=int(self.system_manager.config.get('Batch', 'max_batch_size', fallback='50')))
    
    def _create_widgets(self):
        """UI 위젯 생성"""
        # 노트북 (탭) 컨트롤
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 일반 설정 탭
        general_tab = ttk.Frame(notebook)
        notebook.add(general_tab, text="일반 설정")
        self._create_general_tab(general_tab)
        
        # 성능 최적화 탭
        performance_tab = ttk.Frame(notebook)
        notebook.add(performance_tab, text="성능 최적화")
        self._create_performance_tab(performance_tab)
        
        # 경로 설정 탭
        paths_tab = ttk.Frame(notebook)
        notebook.add(paths_tab, text="경로 설정")
        self._create_paths_tab(paths_tab)
        
        # 고급 설정 탭
        advanced_tab = ttk.Frame(notebook)
        notebook.add(advanced_tab, text="고급 설정")
        self._create_advanced_tab(advanced_tab)
        
        # 시스템 정보 탭
        system_tab = ttk.Frame(notebook)
        notebook.add(system_tab, text="시스템 정보")
        self._create_system_tab(system_tab)
        
        # 버튼 영역
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 저장 버튼
        save_btn = ttk.Button(button_frame, text="설정 저장", command=self._save_settings)
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # 취소 버튼
        cancel_btn = ttk.Button(button_frame, text="취소", command=self.dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
    
    def _create_general_tab(self, parent):
        """일반 설정 탭 생성"""
        # UI 스케일 설정
        scale_frame = ttk.LabelFrame(parent, text="UI 크기 설정")
        scale_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(scale_frame, text="UI 크기:").pack(side=tk.LEFT, padx=5)
        
        scale_scale = Scale(scale_frame, from_=0.8, to=2.0, resolution=0.1,
                         orient=tk.HORIZONTAL, variable=self.ui_scale_var,
                         label="", length=300)
        scale_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        ttk.Label(scale_frame, text="(변경 시 재시작 필요)").pack(side=tk.LEFT, padx=5)
        
        # 테마 설정
        theme_frame = ttk.LabelFrame(parent, text="테마 설정")
        theme_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(theme_frame, text="테마:").pack(side=tk.LEFT, padx=5)
        
        theme_values = {"system": "시스템", "light": "밝게", "dark": "어둡게"}
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var,
                                 values=list(theme_values.values()), state='readonly')
        theme_combo.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 콤보박스 선택 변경 이벤트
        def on_theme_changed(event):
            # 한글 값을 영어 키로 변환
            selected = theme_combo.get()
            for key, value in theme_values.items():
                if value == selected:
                    self.theme_var.set(key)
                    break
        
        theme_combo.bind('<<ComboboxSelected>>', on_theme_changed)
        
        # 현재 테마 값 설정 (영어 키를 한글 값으로 변환)
        current_theme = self.theme_var.get()
        if current_theme in theme_values:
            theme_combo.set(theme_values[current_theme])
        
        # 캡처 설정
        capture_frame = ttk.LabelFrame(parent, text="캡처 설정")
        capture_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(capture_frame, text="캡처 간격(초):").pack(side=tk.LEFT, padx=5)
        
        capture_spinbox = ttk.Spinbox(capture_frame, from_=0.1, to=10.0, increment=0.1,
                                    textvariable=self.capture_interval_var, width=5)
        capture_spinbox.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 자동 백업 설정
        backup_frame = ttk.LabelFrame(parent, text="자동 백업 설정")
        backup_frame.pack(fill=tk.X, padx=10, pady=5)
        
        backup_check = ttk.Checkbutton(backup_frame, text="자동 백업 사용", variable=self.auto_backup_var)
        backup_check.pack(padx=5, pady=5)
        
        ttk.Label(backup_frame, text="자동 백업은 6시간마다 설정과 모델을 백업합니다.").pack(padx=5, pady=5)
    
    def _create_performance_tab(self, parent):
        """성능 최적화 탭 생성"""
        # 캐싱 설정
        cache_frame = ttk.LabelFrame(parent, text="OCR 결과 캐싱")
        cache_frame.pack(fill=tk.X, padx=10, pady=5)
        
        cache_check = ttk.Checkbutton(cache_frame, text="OCR 결과 캐싱 활성화", variable=self.enable_caching_var)
        cache_check.pack(padx=5, pady=5)
        
        ttk.Label(cache_frame, text="캐싱을 활성화하면 동일한 이미지에 대한 OCR 인식 속도가 빨라집니다.").pack(padx=5, pady=5)
        
        cache_btn_frame = ttk.Frame(cache_frame)
        cache_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        clear_cache_btn = ttk.Button(cache_btn_frame, text="캐시 정리", command=self._clear_cache)
        clear_cache_btn.pack(side=tk.LEFT, padx=5)
        
        # 신뢰도 임계값 설정
        threshold_frame = ttk.LabelFrame(parent, text="인식 신뢰도 임계값")
        threshold_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(threshold_frame, text="신뢰도 임계값:").pack(side=tk.LEFT, padx=5)
        
        threshold_scale = Scale(threshold_frame, from_=0.1, to=1.0, resolution=0.05,
                              orient=tk.HORIZONTAL, variable=self.confidence_threshold_var,
                              label="", length=300)
        threshold_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        ttk.Label(threshold_frame, text=f"현재: {self.confidence_threshold_var.get():.2f}").pack(side=tk.LEFT, padx=5)
        
        # 병렬 처리 설정
        parallel_frame = ttk.LabelFrame(parent, text="병렬 처리 설정")
        parallel_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(parallel_frame, text="최대 병렬 작업 수:").pack(side=tk.LEFT, padx=5)
        
        parallel_spinbox = ttk.Spinbox(parallel_frame, from_=1, to=16, 
                                     textvariable=self.parallel_jobs_var, width=5)
        parallel_spinbox.pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(parallel_frame, text="(배치 처리 시 사용)").pack(side=tk.LEFT, padx=5)
        
        # 배치 크기 설정
        batch_frame = ttk.LabelFrame(parent, text="배치 처리 설정")
        batch_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(batch_frame, text="최대 배치 크기:").pack(side=tk.LEFT, padx=5)
        
        batch_spinbox = ttk.Spinbox(batch_frame, from_=10, to=500, increment=10,
                                  textvariable=self.max_batch_size_var, width=5)
        batch_spinbox.pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(batch_frame, text="(한 번에 처리할 최대 파일 수)").pack(side=tk.LEFT, padx=5)
        
        # 메모리 관리
        memory_frame = ttk.LabelFrame(parent, text="메모리 관리")
        memory_frame.pack(fill=tk.X, padx=10, pady=5)
        
        clean_memory_btn = ttk.Button(memory_frame, text="메모리 정리", command=self._clean_memory)
        clean_memory_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 메모리 사용량 표시
        self.memory_label = ttk.Label(memory_frame, text="")
        self.memory_label.pack(side=tk.LEFT, padx=5)
        
        # 현재 메모리 사용량 업데이트
        self._update_memory_usage()
    
    def _create_paths_tab(self, parent):
        """경로 설정 탭 생성"""
        # 캡처 디렉토리 설정
        captures_frame = ttk.LabelFrame(parent, text="캡처 이미지 저장 경로")
        captures_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(captures_frame, text="캡처 폴더:").pack(side=tk.LEFT, padx=5)
        
        captures_entry = ttk.Entry(captures_frame, textvariable=self.captures_dir_var, width=50)
        captures_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        captures_btn = ttk.Button(captures_frame, text="찾아보기", 
                                command=lambda: self._select_directory(self.captures_dir_var))
        captures_btn.pack(side=tk.LEFT, padx=5)
        
        # 모델 디렉토리 설정
        models_frame = ttk.LabelFrame(parent, text="모델 파일 저장 경로")
        models_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(models_frame, text="모델 폴더:").pack(side=tk.LEFT, padx=5)
        
        models_entry = ttk.Entry(models_frame, textvariable=self.models_dir_var, width=50)
        models_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        models_btn = ttk.Button(models_frame, text="찾아보기", 
                              command=lambda: self._select_directory(self.models_dir_var))
        models_btn.pack(side=tk.LEFT, padx=5)
        
        # 학습 데이터 디렉토리 설정
        training_frame = ttk.LabelFrame(parent, text="학습 데이터 저장 경로")
        training_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(training_frame, text="학습 데이터 폴더:").pack(side=tk.LEFT, padx=5)
        
        training_entry = ttk.Entry(training_frame, textvariable=self.training_data_dir_var, width=50)
        training_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        training_btn = ttk.Button(training_frame, text="찾아보기", 
                                command=lambda: self._select_directory(self.training_data_dir_var))
        training_btn.pack(side=tk.LEFT, padx=5)
        
        # 백업 디렉토리 설정
        backup_frame = ttk.LabelFrame(parent, text="백업 파일 저장 경로")
        backup_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(backup_frame, text="백업 폴더:").pack(side=tk.LEFT, padx=5)
        
        backup_entry = ttk.Entry(backup_frame, textvariable=self.backup_dir_var, width=50)
        backup_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        backup_btn = ttk.Button(backup_frame, text="찾아보기", 
                              command=lambda: self._select_directory(self.backup_dir_var))
        backup_btn.pack(side=tk.LEFT, padx=5)
        
        # 백업 관리 버튼
        backup_mgmt_frame = ttk.Frame(parent)
        backup_mgmt_frame.pack(fill=tk.X, padx=10, pady=5)
        
        backup_now_btn = ttk.Button(backup_mgmt_frame, text="지금 백업", 
                                  command=self._backup_now)
        backup_now_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        manage_backup_btn = ttk.Button(backup_mgmt_frame, text="백업 관리", 
                                     command=self._manage_backups)
        manage_backup_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        restore_backup_btn = ttk.Button(backup_mgmt_frame, text="백업 복원", 
                                      command=self._restore_backup)
        restore_backup_btn.pack(side=tk.LEFT, padx=5, pady=5)
    
    def _create_advanced_tab(self, parent):
        """고급 설정 탭 생성"""
        # Tesseract 경로 설정
        tesseract_frame = ttk.LabelFrame(parent, text="Tesseract OCR 경로")
        tesseract_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(tesseract_frame, text="Tesseract 경로:").pack(side=tk.LEFT, padx=5)
        
        tesseract_entry = ttk.Entry(tesseract_frame, textvariable=self.tesseract_path_var, width=50)
        tesseract_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        tesseract_btn = ttk.Button(tesseract_frame, text="찾아보기", 
                                 command=self._select_tesseract_path)
        tesseract_btn.pack(side=tk.LEFT, padx=5)
        
        # 자동 학습 설정
        learning_frame = ttk.LabelFrame(parent, text="자동 학습 설정")
        learning_frame.pack(fill=tk.X, padx=10, pady=5)
        
        auto_learning_check = ttk.Checkbutton(learning_frame, text="수정 시 자동 학습 데이터 저장", 
                                            variable=self.auto_learning_var)
        auto_learning_check.pack(padx=5, pady=5)
        
        ttk.Label(learning_frame, text="수정된 인식 결과를 자동으로 학습 데이터로 저장하여 모델 성능을 향상시킵니다.").pack(padx=5, pady=5)
        
        # 디버그 모드 설정
        debug_frame = ttk.LabelFrame(parent, text="디버그 모드")
        debug_frame.pack(fill=tk.X, padx=10, pady=5)
        
        debug_check = ttk.Checkbutton(debug_frame, text="디버그 모드 사용", 
                                    variable=self.debug_mode_var)
        debug_check.pack(padx=5, pady=5)
        
        ttk.Label(debug_frame, text="디버그 모드를 사용하면 인식 과정의 중간 결과가 저장됩니다.").pack(padx=5, pady=5)
        
        # 수동 ROI 설정
        roi_frame = ttk.LabelFrame(parent, text="ROI 설정")
        roi_frame.pack(fill=tk.X, padx=10, pady=5)
        
        roi_check = ttk.Checkbutton(roi_frame, text="수동 ROI 설정 사용", 
                                  variable=self.use_manual_roi_var)
        roi_check.pack(padx=5, pady=5)
        
        ttk.Label(roi_frame, text="수동 ROI 설정을 사용하면 사용자가 지정한 영역만 인식합니다.").pack(padx=5, pady=5)
        
        # 학습 데이터 검증 버튼
        validate_frame = ttk.Frame(parent)
        validate_frame.pack(fill=tk.X, padx=10, pady=5)
        
        validate_btn = ttk.Button(validate_frame, text="학습 데이터 검증", 
                                command=self._validate_training_data)
        validate_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        cleanup_btn = ttk.Button(validate_frame, text="학습 데이터 정리", 
                               command=self._cleanup_training_data)
        cleanup_btn.pack(side=tk.LEFT, padx=5, pady=5)
    
    def _create_system_tab(self, parent):
        """시스템 정보 탭 생성"""
        # 시스템 정보 표시
        info_frame = ttk.LabelFrame(parent, text="시스템 정보")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 텍스트 영역
        self.system_info_text = tk.Text(info_frame, height=20, wrap=tk.WORD, font=('Courier', 10))
        self.system_info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(self.system_info_text, orient="vertical", 
                                command=self.system_info_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.system_info_text.config(yscrollcommand=scrollbar.set)
        
        # 시스템 정보 업데이트
        self._update_system_info()
        
        # 새로고침 버튼
        refresh_btn = ttk.Button(info_frame, text="새로고침", 
                               command=self._update_system_info)
        refresh_btn.pack(pady=5)
    
    def _select_directory(self, var):
        """디렉토리 선택 대화상자"""
        directory = filedialog.askdirectory(initialdir=var.get())
        if directory:
            var.set(directory)
    
    def _select_tesseract_path(self):
        """Tesseract 실행 파일 선택 대화상자"""
        if os.name == 'nt':  # Windows
            filetypes = [("실행 파일", "*.exe"), ("모든 파일", "*.*")]
        else:  # Linux/Mac
            filetypes = [("모든 파일", "*")]
        
        file_path = filedialog.askopenfilename(
            title="Tesseract 실행 파일 선택",
            filetypes=filetypes,
            initialdir=os.path.dirname(self.tesseract_path_var.get())
        )
        
        if file_path:
            self.tesseract_path_var.set(file_path)
            
            # 경로 유효성 검사
            self._verify_tesseract_path(file_path)
    
    def _verify_tesseract_path(self, path):
        """Tesseract 경로 유효성 검사"""
        try:
            if not os.path.exists(path):
                messagebox.showwarning("경고", "선택한 파일이 존재하지 않습니다.")
                return False
            
            # 실행 파일 확인
            if os.name == 'nt' and not path.lower().endswith('.exe'):
                messagebox.showwarning("경고", "Windows에서는 .exe 파일을 선택해야 합니다.")
                return False
            
            # Tesseract 버전 확인
            import subprocess
            
            try:
                result = subprocess.run([path, '--version'], 
                                      capture_output=True, text=True, timeout=3)
                
                if result.returncode == 0 and 'tesseract' in result.stdout.lower():
                    messagebox.showinfo("성공", f"Tesseract OCR 경로가 유효합니다.\n버전: {result.stdout.split()[1]}")
                    return True
                else:
                    messagebox.showwarning("경고", "선택한 파일이 Tesseract OCR이 아닌 것 같습니다.")
                    return False
            except subprocess.TimeoutExpired:
                messagebox.showwarning("경고", "Tesseract 버전 확인 시간 초과")
                return False
            except Exception as e:
                messagebox.showwarning("경고", f"Tesseract 버전 확인 오류: {e}")
                return False
        except Exception as e:
            messagebox.showwarning("경고", f"Tesseract 경로 확인 오류: {e}")
            return False
    
    def _clear_cache(self):
        """OCR 캐시 정리"""
        # 캐시 정리 확인
        if messagebox.askyesno("확인", "OCR 캐시를 정리하시겠습니까?"):
            try:
                # 시스템 메모리 정리
                self.system_manager.clean_memory()
                
                messagebox.showinfo("완료", "OCR 캐시가 정리되었습니다.")
                
                # 메모리 사용량 업데이트
                self._update_memory_usage()
            except Exception as e:
                messagebox.showerror("오류", f"캐시 정리 중 오류 발생: {e}")
    
    def _clean_memory(self):
        """메모리 정리"""
        try:
            # 시스템 메모리 정리
            self.system_manager.clean_memory()
            
            messagebox.showinfo("완료", "메모리 정리가 완료되었습니다.")
            
            # 메모리 사용량 업데이트
            self._update_memory_usage()
        except Exception as e:
            messagebox.showerror("오류", f"메모리 정리 중 오류 발생: {e}")
    
    def _update_memory_usage(self):
        """메모리 사용량 업데이트"""
        try:
            # 메모리 사용량 조회
            memory_usage = self.system_manager.get_memory_usage()
            
            if memory_usage:
                self.memory_label.config(text=f"현재 메모리 사용량: {memory_usage['rss_mb']:.1f} MB")
            else:
                self.memory_label.config(text="메모리 사용량 조회 실패")
        except Exception as e:
            self.memory_label.config(text=f"메모리 사용량 조회 오류: {e}")
    
    def _update_system_info(self):
        """시스템 정보 업데이트"""
        try:
            # 시스템 정보 조회
            system_info = self.system_manager.get_system_info()
            
            # 정보 텍스트 초기화
            self.system_info_text.config(state=tk.NORMAL)
            self.system_info_text.delete(1.0, tk.END)
            
            # 시스템 정보 표시
            if 'error' in system_info:
                self.system_info_text.insert(tk.END, f"시스템 정보 조회 오류: {system_info['error']}")
            else:
                # 기본 시스템 정보
                self.system_info_text.insert(tk.END, "=== 시스템 정보 ===\n\n")
                self.system_info_text.insert(tk.END, f"플랫폼: {system_info['platform']} {system_info['release']}\n")
                self.system_info_text.insert(tk.END, f"시스템 버전: {system_info['version']}\n")
                self.system_info_text.insert(tk.END, f"머신: {system_info['machine']}\n")
                self.system_info_text.insert(tk.END, f"프로세서: {system_info['processor']}\n\n")
                
                # 소프트웨어 버전
                self.system_info_text.insert(tk.END, "=== 소프트웨어 버전 ===\n\n")
                self.system_info_text.insert(tk.END, f"Python: {system_info['python_version']}\n")
                self.system_info_text.insert(tk.END, f"TensorFlow: {system_info['tensorflow_version']}\n")
                self.system_info_text.insert(tk.END, f"OpenCV: {system_info['opencv_version']}\n")
                self.system_info_text.insert(tk.END, f"NumPy: {system_info['numpy_version']}\n\n")
                
                # GPU 정보
                self.system_info_text.insert(tk.END, "=== GPU 정보 ===\n\n")
                if system_info['gpu_available']:
                    self.system_info_text.insert(tk.END, f"GPU 개수: {system_info['gpu_count']}\n")
                    for i, gpu in enumerate(system_info['gpu_info']):
                        self.system_info_text.insert(tk.END, f"GPU {i+1}: {gpu['name']}\n")
                else:
                    self.system_info_text.insert(tk.END, "GPU를 사용할 수 없습니다. CPU를 사용합니다.\n\n")
                
                # 메모리 사용량
                self.system_info_text.insert(tk.END, "\n=== 메모리 사용량 ===\n\n")
                if system_info['memory_usage']:
                    self.system_info_text.insert(tk.END, f"실제 메모리 사용량: {system_info['memory_usage']['rss_mb']:.1f} MB\n")
                    self.system_info_text.insert(tk.END, f"가상 메모리 사용량: {system_info['memory_usage']['vms_mb']:.1f} MB\n")
                else:
                    self.system_info_text.insert(tk.END, "메모리 사용량을 조회할 수 없습니다.\n")
            
            # 읽기 전용으로 설정
            self.system_info_text.config(state=tk.DISABLED)
        except Exception as e:
            # 오류 발생 시
            self.system_info_text.config(state=tk.NORMAL)
            self.system_info_text.delete(1.0, tk.END)
            self.system_info_text.insert(tk.END, f"시스템 정보 업데이트 오류: {e}")
            self.system_info_text.config(state=tk.DISABLED)
    
    def _backup_now(self):
        """수동 백업 실행"""
        try:
            # 백업 실행
            result = self.system_manager.backup_now()
            
            if result['success']:
                messagebox.showinfo("완료", f"백업이 성공적으로 생성되었습니다.\n\n위치: {result['backup_dir']}")
            else:
                messagebox.showerror("오류", f"백업 생성 중 오류 발생: {result['error']}")
        except Exception as e:
            messagebox.showerror("오류", f"백업 생성 중 오류 발생: {e}")
    
    def _manage_backups(self):
        """백업 관리"""
        # 백업 목록 가져오기
        backup_list = self.system_manager.get_backup_list()
        
        if not backup_list:
            messagebox.showinfo("알림", "관리할 백업이 없습니다.")
            return
        
        # 백업 관리 창
        manage_window = tk.Toplevel(self.dialog)
        manage_window.title("백업 관리")
        manage_window.geometry("800x600")
        manage_window.transient(self.dialog)
        manage_window.grab_set()
        
        # 백업 목록 프레임
        list_frame = ttk.LabelFrame(manage_window, text="백업 목록")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 백업 목록
        columns = ('name', 'date', 'size', 'type')
        backup_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        backup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 열 설정
        backup_tree.heading('name', text='백업 이름')
        backup_tree.heading('date', text='생성 날짜')
        backup_tree.heading('size', text='크기')
        backup_tree.heading('type', text='유형')
        
        backup_tree.column('name', width=300)
        backup_tree.column('date', width=150)
        backup_tree.column('size', width=100)
        backup_tree.column('type', width=100)
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=backup_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        backup_tree.configure(yscrollcommand=scrollbar.set)
        
        # 백업 정보 프레임
        info_frame = ttk.LabelFrame(manage_window, text="백업 정보")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 백업 정보 텍스트
        info_text = tk.Text(info_frame, height=8, wrap=tk.WORD, font=('Courier', 10))
        info_text.pack(fill=tk.X, padx=5, pady=5)
        
        # 읽기 전용으로 설정
        info_text.config(state=tk.DISABLED)
        
        # 백업 목록 채우기
        for backup in backup_list:
            backup_tree.insert('', tk.END, values=(
                backup['name'],
                backup['date'],
                f"{backup['size_mb']:.1f} MB",
                backup['type']
            ))
        
        # 백업 선택 시 정보 표시
        def on_select(event):
            selected = backup_tree.selection()
            if selected:
                # 선택된 항목의 이름 가져오기
                backup_name = backup_tree.item(selected[0])['values'][0]
                
                # 해당 백업 정보 찾기
                for backup in backup_list:
                    if backup['name'] == backup_name:
                        # 정보 표시
                        info_text.config(state=tk.NORMAL)
                        info_text.delete(1.0, tk.END)
                        
                        for key, value in backup['info'].items():
                            info_text.insert(tk.END, f"{key}: {value}\n")
                        
                        info_text.config(state=tk.DISABLED)
                        break
        
        backup_tree.bind('<<TreeviewSelect>>', on_select)
        
        # 버튼 프레임
        button_frame = ttk.Frame(manage_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 백업 삭제 함수
        def delete_backup():
            selected = backup_tree.selection()
            if not selected:
                messagebox.showinfo("알림", "삭제할 백업을 선택하세요.")
                return
            
            # 선택된 백업 이름 가져오기
            backup_name = backup_tree.item(selected[0])['values'][0]
            
            # 삭제 확인
            if messagebox.askyesno("확인", f"'{backup_name}' 백업을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다."):
                # 해당 백업 정보 찾기
                for backup in backup_list:
                    if backup['name'] == backup_name:
                        # 백업 삭제
                        if self.system_manager.delete_backup(backup['path']):
                            messagebox.showinfo("완료", f"'{backup_name}' 백업이 삭제되었습니다.")
                            
                            # 트리에서 항목 제거
                            backup_tree.delete(selected[0])
                            
                            # 정보 초기화
                            info_text.config(state=tk.NORMAL)
                            info_text.delete(1.0, tk.END)
                            info_text.config(state=tk.DISABLED)
                        else:
                            messagebox.showerror("오류", f"'{backup_name}' 백업 삭제 중 오류가 발생했습니다.")
                        break
        
        # 백업 버튼
        backup_btn = ttk.Button(button_frame, text="새 백업 생성", 
                              command=lambda: [manage_window.destroy(), self._backup_now()])
        backup_btn.pack(side=tk.LEFT, padx=5)
        
        # 삭제 버튼
        delete_btn = ttk.Button(button_frame, text="선택 삭제", command=delete_backup)
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        # 복원 버튼
        restore_btn = ttk.Button(button_frame, text="선택 복원", 
                               command=lambda: [manage_window.destroy(), self._restore_selected_backup(backup_tree, backup_list)])
        restore_btn.pack(side=tk.LEFT, padx=5)
        
        # 닫기 버튼
        close_btn = ttk.Button(button_frame, text="닫기", command=manage_window.destroy)
        close_btn.pack(side=tk.RIGHT, padx=5)
    
    def _restore_selected_backup(self, backup_tree, backup_list):
        """선택된 백업 복원"""
        selected = backup_tree.selection()
        if not selected:
            messagebox.showinfo("알림", "복원할 백업을 선택하세요.")
            return
        
        # 선택된 백업 이름 가져오기
        backup_name = backup_tree.item(selected[0])['values'][0]
        
        # 백업 복원
        self._restore_backup(backup_name)
    
    def _restore_backup(self, backup_name=None):
        """백업 복원"""
        # 백업 목록 가져오기
        backup_list = self.system_manager.get_backup_list()
        
        if not backup_list:
            messagebox.showinfo("알림", "복원할 백업이 없습니다.")
            return
        
        # 백업 선택 (이름이 제공되지 않은 경우)
        if backup_name is None:
            # 백업 선택 창
            select_window = tk.Toplevel(self.dialog)
            select_window.title("백업 복원")
            select_window.geometry("600x400")
            select_window.transient(self.dialog)
            select_window.grab_set()
            
            # 백업 목록 프레임
            list_frame = ttk.LabelFrame(select_window, text="복원할 백업 선택")
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 백업 목록
            columns = ('name', 'date', 'type')
            backup_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
            backup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # 열 설정
            backup_tree.heading('name', text='백업 이름')
            backup_tree.heading('date', text='생성 날짜')
            backup_tree.heading('type', text='유형')
            
            backup_tree.column('name', width=300)
            backup_tree.column('date', width=150)
            backup_tree.column('type', width=100)
            
            # 스크롤바
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=backup_tree.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            backup_tree.configure(yscrollcommand=scrollbar.set)
            
            # 백업 목록 채우기
            for backup in backup_list:
                backup_tree.insert('', tk.END, values=(
                    backup['name'],
                    backup['date'],
                    backup['type']
                ))
            
            # 복원 옵션 프레임
            options_frame = ttk.LabelFrame(select_window, text="복원 옵션")
            options_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # 옵션 변수
            config_var = tk.BooleanVar(value=True)
            roi_var = tk.BooleanVar(value=True)
            presets_var = tk.BooleanVar(value=True)
            player_dict_var = tk.BooleanVar(value=True)
            models_var = tk.BooleanVar(value=True)
            stats_var = tk.BooleanVar(value=True)
            
            # 옵션 체크박스
            ttk.Checkbutton(options_frame, text="설정 파일", variable=config_var).pack(anchor=tk.W, padx=5, pady=2)
            ttk.Checkbutton(options_frame, text="ROI 설정", variable=roi_var).pack(anchor=tk.W, padx=5, pady=2)
            ttk.Checkbutton(options_frame, text="ROI 프리셋", variable=presets_var).pack(anchor=tk.W, padx=5, pady=2)
            ttk.Checkbutton(options_frame, text="선수 이름 사전", variable=player_dict_var).pack(anchor=tk.W, padx=5, pady=2)
            ttk.Checkbutton(options_frame, text="모델 파일", variable=models_var).pack(anchor=tk.W, padx=5, pady=2)
            ttk.Checkbutton(options_frame, text="학습 통계", variable=stats_var).pack(anchor=tk.W, padx=5, pady=2)
            
            # 버튼 프레임
            button_frame = ttk.Frame(select_window)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # 복원 함수
            def do_restore():
                selected = backup_tree.selection()
                if not selected:
                    messagebox.showinfo("알림", "복원할 백업을 선택하세요.")
                    return
                
                # 선택된 백업 이름 가져오기
                backup_name = backup_tree.item(selected[0])['values'][0]
                
                # 해당 백업 정보 찾기
                for backup in backup_list:
                    if backup['name'] == backup_name:
                        # 복원 옵션
                        options = {
                            'config': config_var.get(),
                            'roi': roi_var.get(),
                            'presets': presets_var.get(),
                            'player_dict': player_dict_var.get(),
                            'models': models_var.get(),
                            'stats': stats_var.get()
                        }
                        
                        # 복원 확인
                        if messagebox.askyesno("확인", f"'{backup_name}' 백업에서 복원하시겠습니까?\n\n현재 설정이 덮어쓰여집니다."):
                            # 창 닫기
                            select_window.destroy()
                            
                            # 백업 복원
                            self._do_restore(backup['path'], options)
                        
                        break
            
            # 복원 버튼
            restore_btn = ttk.Button(button_frame, text="복원", command=do_restore)
            restore_btn.pack(side=tk.LEFT, padx=5)
            
            # 취소 버튼
            cancel_btn = ttk.Button(button_frame, text="취소", command=select_window.destroy)
            cancel_btn.pack(side=tk.RIGHT, padx=5)
            
            # 첫 번째 항목 선택
            if backup_list:
                backup_tree.selection_set(backup_tree.get_children()[0])
            
            return
        
        # 이름으로 백업 찾기
        backup_path = None
        
        for backup in backup_list:
            if backup['name'] == backup_name:
                backup_path = backup['path']
                break
        
        if backup_path:
            # 복원 옵션
            options = {
                'config': True,
                'roi': True,
                'presets': True,
                'player_dict': True,
                'models': True,
                'stats': True
            }
            
            # 복원 확인
            if messagebox.askyesno("확인", f"'{backup_name}' 백업에서 복원하시겠습니까?\n\n현재 설정이 덮어쓰여집니다."):
                # 백업 복원
                self._do_restore(backup_path, options)
        else:
            messagebox.showerror("오류", f"'{backup_name}' 백업을 찾을 수 없습니다.")
    
    def _do_restore(self, backup_path, options):
        """백업 복원 실행"""
        try:
            # 백업 복원
            result = self.system_manager.restore_from_backup(backup_path, options)
            
            if result['success']:
                # 복원 항목 목록
                items_str = "\n".join(result['restored_items'])
                
                messagebox.showinfo("완료", f"백업에서 복원이 완료되었습니다.\n\n복원된 항목:\n{items_str}\n\n일부 설정은 프로그램 재시작 후 적용됩니다.")
                
                # 설정 값 다시 로드
                self._load_settings()
            else:
                messagebox.showerror("오류", f"백업 복원 중 오류 발생: {result['error']}")
        except Exception as e:
            messagebox.showerror("오류", f"백업 복원 중 오류 발생: {e}")
    
    def _validate_training_data(self):
        """학습 데이터 유효성 검사"""
        try:
            # 학습 데이터 유효성 검사 창
            validate_window = tk.Toplevel(self.dialog)
            validate_window.title("학습 데이터 검증")
            validate_window.geometry("700x500")
            validate_window.transient(self.dialog)
            validate_window.grab_set()
            
            # 메시지
            ttk.Label(validate_window, text="학습 데이터를 검증하는 중입니다...",
                    font=('Gulim', 12, 'bold')).pack(pady=10)
            
            # 진행 상황
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(validate_window, variable=progress_var, length=500)
            progress_bar.pack(pady=10)
            
            # 결과 텍스트
            result_text = tk.Text(validate_window, height=20, wrap=tk.WORD, font=('Courier', 10))
            result_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 스크롤바
            scrollbar = ttk.Scrollbar(result_text, orient="vertical", command=result_text.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            result_text.config(yscrollcommand=scrollbar.set)
            
            # 버튼 프레임
            button_frame = ttk.Frame(validate_window)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # 닫기 버튼
            close_btn = ttk.Button(button_frame, text="닫기", command=validate_window.destroy)
            close_btn.pack(side=tk.RIGHT, padx=5)
            
            # 유효성 검사 함수
            def do_validate():
                try:
                    # 결과 텍스트 초기화
                    result_text.delete(1.0, tk.END)
                    result_text.insert(tk.END, "학습 데이터 검증 중...\n\n")
                    
                    # 필드 목록
                    fields = ['overall', 'position', 'salary', 'enhance_level', 'season_icon', 'boost_level']
                    total_fields = len(fields)
                    
                    # 검증 결과
                    results = {}
                    total_files = 0
                    total_valid = 0
                    total_invalid = 0
                    
                    # 각 필드 검증
                    for i, field in enumerate(fields):
                        field_dir = os.path.join(self.system_manager.training_data_dir, field)
                        
                        # 진행 상황 업데이트
                        progress_var.set((i / total_fields) * 100)
                        validate_window.update_idletasks()
                        
                        # 필드 디렉토리 확인
                        if not os.path.exists(field_dir):
                            results[field] = {
                                'exists': False,
                                'classes': [],
                                'files': 0,
                                'valid': 0,
                                'invalid': 0,
                                'invalid_files': []
                            }
                            continue
                        
                        # 클래스 디렉토리 확인
                        classes = [d for d in os.listdir(field_dir) if os.path.isdir(os.path.join(field_dir, d))]
                        
                        field_files = 0
                        field_valid = 0
                        field_invalid = 0
                        invalid_files = []
                        
                        # 각 클래스 검증
                        for class_name in classes:
                            class_dir = os.path.join(field_dir, class_name)
                            
                            # 이미지 파일 확인
                            image_files = [f for f in os.listdir(class_dir) 
                                         if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
                            
                            # 각 이미지 파일 검증
                            for image_file in image_files:
                                image_path = os.path.join(class_dir, image_file)
                                field_files += 1
                                
                                try:
                                    # 파일 크기 확인
                                    if os.path.getsize(image_path) == 0:
                                        field_invalid += 1
                                        invalid_files.append({
                                            'path': image_path,
                                            'class': class_name,
                                            'reason': '빈 파일'
                                        })
                                        continue
                                    
                                    # 이미지 로드 시도
                                    import cv2
                                    img = cv2.imread(image_path)
                                    
                                    if img is None:
                                        field_invalid += 1
                                        invalid_files.append({
                                            'path': image_path,
                                            'class': class_name,
                                            'reason': '이미지 로드 실패'
                                        })
                                        continue
                                    
                                    # 이미지 크기 확인
                                    if img.shape[0] < 5 or img.shape[1] < 5:
                                        field_invalid += 1
                                        invalid_files.append({
                                            'path': image_path,
                                            'class': class_name,
                                            'reason': f'이미지 크기가 너무 작음 ({img.shape[1]}x{img.shape[0]})'
                                        })
                                        continue
                                    
                                    # 유효한 이미지
                                    field_valid += 1
                                
                                except Exception as e:
                                    field_invalid += 1
                                    invalid_files.append({
                                        'path': image_path,
                                        'class': class_name,
                                        'reason': f'검증 중 오류: {e}'
                                    })
                        
                        # 필드 결과 저장
                        results[field] = {
                            'exists': True,
                            'classes': classes,
                            'files': field_files,
                            'valid': field_valid,
                            'invalid': field_invalid,
                            'invalid_files': invalid_files
                        }
                        
                        # 전체 통계 업데이트
                        total_files += field_files
                        total_valid += field_valid
                        total_invalid += field_invalid
                    
                    # 진행 상황 완료
                    progress_var.set(100)
                    
                    # 결과 표시
                    result_text.delete(1.0, tk.END)
                    result_text.insert(tk.END, "=== 학습 데이터 검증 결과 ===\n\n")
                    
                    for field, result in results.items():
                        if result['exists']:
                            result_text.insert(tk.END, f"[{field}]\n", "field")
                            result_text.insert(tk.END, f"  클래스 수: {len(result['classes'])}\n")
                            result_text.insert(tk.END, f"  총 파일 수: {result['files']}\n")
                            result_text.insert(tk.END, f"  유효한 파일: {result['valid']}\n")
                            result_text.insert(tk.END, f"  유효하지 않은 파일: {result['invalid']}\n")
                            
                            if result['invalid'] > 0:
                                result_text.insert(tk.END, "\n  유효하지 않은 파일 목록:\n", "invalid_header")
                                
                                for invalid in result['invalid_files']:
                                    filename = os.path.basename(invalid['path'])
                                    result_text.insert(tk.END, f"    - {invalid['class']}/{filename}: {invalid['reason']}\n", "invalid_file")
                            
                            result_text.insert(tk.END, "\n")
                        else:
                            result_text.insert(tk.END, f"[{field}]\n", "field")
                            result_text.insert(tk.END, f"  디렉토리가 존재하지 않습니다.\n\n")
                    
                    # 전체 통계
                    result_text.insert(tk.END, "=== 전체 통계 ===\n\n", "total")
                    result_text.insert(tk.END, f"총 파일 수: {total_files}\n")
                    result_text.insert(tk.END, f"유효한 파일: {total_valid} ({total_valid/total_files*100:.1f}%)\n")
                    result_text.insert(tk.END, f"유효하지 않은 파일: {total_invalid} ({total_invalid/total_files*100:.1f}%)\n")
                    
                    # 스타일 설정
                    result_text.tag_configure("field", foreground="blue", font=('Courier', 12, 'bold'))
                    result_text.tag_configure("invalid_header", foreground="red", font=('Courier', 11, 'bold'))
                    result_text.tag_configure("invalid_file", foreground="red")
                    result_text.tag_configure("total", foreground="green", font=('Courier', 12, 'bold'))
                    
                    # 정리 버튼 활성화
                    if total_invalid > 0:
                        cleanup_btn = ttk.Button(button_frame, text=f"{total_invalid}개 파일 정리", 
                                              command=lambda: self._cleanup_invalid_files(results))
                        cleanup_btn.pack(side=tk.LEFT, padx=5)
                
                except Exception as e:
                    # 오류 발생 시
                    result_text.insert(tk.END, f"\n오류 발생: {e}\n")
                    import traceback
                    result_text.insert(tk.END, traceback.format_exc())
            
            # 별도 스레드에서 검증 실행
            import threading
            threading.Thread(target=do_validate, daemon=True).start()
        
        except Exception as e:
            messagebox.showerror("오류", f"학습 데이터 검증 중 오류 발생: {e}")
    
    def _cleanup_invalid_files(self, validation_results):
        """유효하지 않은 학습 데이터 파일 정리"""
        try:
            # 삭제할 파일 목록
            files_to_delete = []
            
            # 각 필드의 유효하지 않은 파일 수집
            for field, result in validation_results.items():
                if result['exists'] and result['invalid'] > 0:
                    for invalid in result['invalid_files']:
                        files_to_delete.append(invalid['path'])
            
            # 확인 대화상자
            if messagebox.askyesno("확인", f"{len(files_to_delete)}개의 유효하지 않은 파일을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다."):
                # 파일 삭제
                deleted = 0
                
                for file_path in files_to_delete:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            deleted += 1
                    except Exception as e:
                        logger.error(f"파일 삭제 오류 ({file_path}): {e}")
                
                messagebox.showinfo("완료", f"{deleted}개 파일이 삭제되었습니다.")
        
        except Exception as e:
            messagebox.showerror("오류", f"파일 정리 중 오류 발생: {e}")
    
    def _cleanup_training_data(self):
        """학습 데이터 정리"""
        try:
            # 정리 옵션 선택 창
            cleanup_window = tk.Toplevel(self.dialog)
            cleanup_window.title("학습 데이터 정리")
            cleanup_window.geometry("500x400")
            cleanup_window.transient(self.dialog)
            cleanup_window.grab_set()
            
            # 메시지
            ttk.Label(cleanup_window, text="학습 데이터 정리 옵션 선택",
                    font=('Gulim', 12, 'bold')).pack(pady=10)
            
            # 옵션 프레임
            options_frame = ttk.LabelFrame(cleanup_window, text="정리 옵션")
            options_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 옵션 변수
            empty_class_var = tk.BooleanVar(value=True)
            small_image_var = tk.BooleanVar(value=True)
            invalid_image_var = tk.BooleanVar(value=True)
            duplicate_var = tk.BooleanVar(value=True)
            
            # 옵션 체크박스
            ttk.Checkbutton(options_frame, text="빈 클래스 폴더 제거", 
                          variable=empty_class_var).pack(anchor=tk.W, padx=5, pady=5)
            ttk.Label(options_frame, text="아무 이미지도 없는 클래스 폴더를 삭제합니다.").pack(anchor=tk.W, padx=20, pady=2)
            
            ttk.Checkbutton(options_frame, text="너무 작은 이미지 제거", 
                          variable=small_image_var).pack(anchor=tk.W, padx=5, pady=5)
            ttk.Label(options_frame, text="5x5 픽셀 미만의 작은 이미지를 삭제합니다.").pack(anchor=tk.W, padx=20, pady=2)
            
            ttk.Checkbutton(options_frame, text="유효하지 않은 이미지 제거", 
                          variable=invalid_image_var).pack(anchor=tk.W, padx=5, pady=5)
            ttk.Label(options_frame, text="로드할 수 없거나 손상된 이미지 파일을 삭제합니다.").pack(anchor=tk.W, padx=20, pady=2)
            
            ttk.Checkbutton(options_frame, text="중복 이미지 제거", 
                          variable=duplicate_var).pack(anchor=tk.W, padx=5, pady=5)
            ttk.Label(options_frame, text="동일한 내용을 가진 중복 이미지를 삭제합니다.").pack(anchor=tk.W, padx=20, pady=2)
            
            # 버튼 프레임
            button_frame = ttk.Frame(cleanup_window)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # 정리 함수
            def do_cleanup():
                try:
                    # 정리 옵션
                    options = {
                        'empty_class': empty_class_var.get(),
                        'small_image': small_image_var.get(),
                        'invalid_image': invalid_image_var.get(),
                        'duplicate': duplicate_var.get()
                    }
                    
                    # 확인 대화상자
                    if messagebox.askyesno("확인", "선택한 옵션으로 학습 데이터를 정리하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다."):
                        # 창 닫기
                        cleanup_window.destroy()
                        
                        # 정리 진행 창
                        progress_window = tk.Toplevel(self.dialog)
                        progress_window.title("학습 데이터 정리 중")
                        progress_window.geometry("500x300")
                        progress_window.transient(self.dialog)
                        progress_window.grab_set()
                        
                        # 메시지
                        message_var = tk.StringVar(value="학습 데이터를 정리하는 중...")
                        message_label = ttk.Label(progress_window, textvariable=message_var,
                                                font=('Gulim', 12, 'bold'))
                        message_label.pack(pady=10)
                        
                        # 진행 상황
                        progress_var = tk.DoubleVar()
                        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, length=400)
                        progress_bar.pack(pady=10)
                        
                        # 결과 텍스트
                        result_text = tk.Text(progress_window, height=10, wrap=tk.WORD, font=('Courier', 10))
                        result_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                        
                        # 스크롤바
                        scrollbar = ttk.Scrollbar(result_text, orient="vertical", command=result_text.yview)
                        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                        result_text.config(yscrollcommand=scrollbar.set)
                        
                        # 닫기 버튼
                        close_btn = ttk.Button(progress_window, text="닫기", command=progress_window.destroy)
                        close_btn.pack(pady=10)
                        close_btn.config(state=tk.DISABLED)
                        
                        # 정리 작업 함수
                        def cleanup_worker():
                            try:
                                # 결과 초기화
                                deleted_files = 0
                                deleted_dirs = 0
                                
                                # 필드 목록
                                fields = ['overall', 'position', 'salary', 'enhance_level', 'season_icon', 'boost_level']
                                total_fields = len(fields)
                                
                                # 각 필드 처리
                                for i, field in enumerate(fields):
                                    field_dir = os.path.join(self.system_manager.training_data_dir, field)
                                    
                                    # 진행 상황 업데이트
                                    progress_var.set((i / total_fields) * 100)
                                    message_var.set(f"'{field}' 필드 정리 중...")
                                    progress_window.update_idletasks()
                                    
                                    # 필드 디렉토리 확인
                                    if not os.path.exists(field_dir):
                                        continue
                                    
                                    # 클래스 디렉토리 확인
                                    classes = [d for d in os.listdir(field_dir) if os.path.isdir(os.path.join(field_dir, d))]
                                    
                                    # 각 클래스 처리
                                    for class_name in classes:
                                        class_dir = os.path.join(field_dir, class_name)
                                        
                                        # 이미지 파일 확인
                                        image_files = [f for f in os.listdir(class_dir) 
                                                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
                                        
                                        # 빈 클래스 처리
                                        if options['empty_class'] and not image_files:
                                            # 빈 디렉토리 삭제
                                            os.rmdir(class_dir)
                                            deleted_dirs += 1
                                            result_text.insert(tk.END, f"빈 클래스 삭제: {field}/{class_name}\n")
                                            result_text.see(tk.END)
                                            progress_window.update_idletasks()
                                            continue
                                        
                                        # 중복 이미지 확인 (옵션 활성화 시)
                                        if options['duplicate']:
                                            # 이미지 해시 사전
                                            image_hashes = {}
                                            
                                            # 각 이미지 파일 처리
                                            for image_file in image_files[:]:  # 복사본으로 반복
                                                image_path = os.path.join(class_dir, image_file)
                                                
                                                try:
                                                    # 이미지 로드
                                                    img = cv2.imread(image_path)
                                                    
                                                    if img is not None:
                                                        # 이미지 해시 계산 (간단한 방법)
                                                        img_hash = hash(img.tobytes())
                                                        
                                                        # 중복 확인
                                                        if img_hash in image_hashes:
                                                            # 중복 이미지 삭제
                                                            os.remove(image_path)
                                                            deleted_files += 1
                                                            result_text.insert(tk.END, f"중복 이미지 삭제: {field}/{class_name}/{image_file}\n")
                                                            result_text.see(tk.END)
                                                            progress_window.update_idletasks()
                                                            
                                                            # 처리 목록에서 제거
                                                            image_files.remove(image_file)
                                                        else:
                                                            # 해시 저장
                                                            image_hashes[img_hash] = image_file
                                                except Exception as e:
                                                    logger.error(f"이미지 해시 계산 오류 ({image_path}): {e}")
                                        
                                        # 각 이미지 파일 처리
                                        for image_file in image_files:
                                            image_path = os.path.join(class_dir, image_file)
                                            
                                            try:
                                                # 이미지 로드 시도
                                                img = cv2.imread(image_path)
                                                
                                                # 유효하지 않은 이미지 처리
                                                if options['invalid_image'] and img is None:
                                                    os.remove(image_path)
                                                    deleted_files += 1
                                                    result_text.insert(tk.END, f"유효하지 않은 이미지 삭제: {field}/{class_name}/{image_file}\n")
                                                    result_text.see(tk.END)
                                                    progress_window.update_idletasks()
                                                    continue
                                                
                                                # 너무 작은 이미지 처리
                                                if options['small_image'] and img is not None:
                                                    if img.shape[0] < 5 or img.shape[1] < 5:
                                                        os.remove(image_path)
                                                        deleted_files += 1
                                                        result_text.insert(tk.END, f"작은 이미지 삭제: {field}/{class_name}/{image_file} ({img.shape[1]}x{img.shape[0]})\n")
                                                        result_text.see(tk.END)
                                                        progress_window.update_idletasks()
                                            except Exception as e:
                                                logger.error(f"이미지 처리 오류 ({image_path}): {e}")
                                
                                # 진행 상황 완료
                                progress_var.set(100)
                                message_var.set("학습 데이터 정리 완료")
                                
                                # 결과 요약
                                result_text.insert(tk.END, "\n=== 정리 결과 ===\n", "summary")
                                result_text.insert(tk.END, f"삭제된 파일: {deleted_files}개\n", "summary")
                                result_text.insert(tk.END, f"삭제된 디렉토리: {deleted_dirs}개\n", "summary")
                                
                                # 스타일 설정
                                result_text.tag_configure("summary", foreground="blue", font=('Courier', 12, 'bold'))
                                
                                # 닫기 버튼 활성화
                                close_btn.config(state=tk.NORMAL)
                            
                            except Exception as e:
                                # 오류 발생 시
                                message_var.set(f"오류 발생: {e}")
                                result_text.insert(tk.END, f"\n오류 발생: {e}\n", "error")
                                import traceback
                                result_text.insert(tk.END, traceback.format_exc(), "error")
                                
                                # 스타일 설정
                                result_text.tag_configure("error", foreground="red")
                                
                                # 닫기 버튼 활성화
                                close_btn.config(state=tk.NORMAL)
                        
                        # 별도 스레드에서 정리 작업 실행
                        import threading
                        threading.Thread(target=cleanup_worker, daemon=True).start()
                
                except Exception as e:
                    messagebox.showerror("오류", f"학습 데이터 정리 중 오류 발생: {e}")
            
            # 정리 버튼
            cleanup_btn = ttk.Button(button_frame, text="정리 시작", command=do_cleanup)
            cleanup_btn.pack(side=tk.LEFT, padx=5)
            
            # 취소 버튼
            cancel_btn = ttk.Button(button_frame, text="취소", command=cleanup_window.destroy)
            cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        except Exception as e:
            messagebox.showerror("오류", f"학습 데이터 정리 초기화 중 오류 발생: {e}")
    
    def _save_settings(self):
        """설정 저장"""
        try:
            # 설정 검증
            if not self._validate_settings():
                return
            
            # 일반 설정
            self.system_manager.config['Settings']['ui_scale'] = str(self.ui_scale_var.get())
            self.system_manager.config['Settings']['theme'] = self.theme_var.get()
            self.system_manager.config['Settings']['capture_interval'] = str(self.capture_interval_var.get())
            self.system_manager.config['Settings']['auto_backup'] = str(self.auto_backup_var.get())
            
            # 성능 최적화 설정
            self.system_manager.config['Settings']['enable_caching'] = str(self.enable_caching_var.get())
            self.system_manager.config['Settings']['confidence_threshold'] = str(self.confidence_threshold_var.get())
            self.system_manager.config['Batch']['parallel_jobs'] = str(self.parallel_jobs_var.get())
            
            # 고급 설정
            self.system_manager.config['Settings']['tesseract_path'] = self.tesseract_path_var.get()
            self.system_manager.config['Settings']['auto_learning'] = str(self.auto_learning_var.get())
            self.system_manager.config['Settings']['debug_mode'] = str(self.debug_mode_var.get())
            self.system_manager.config['Settings']['use_manual_roi'] = str(self.use_manual_roi_var.get())
            
            # 경로 설정
            self.system_manager.config['Paths']['captures_dir'] = self.captures_dir_var.get()
            self.system_manager.config['Paths']['models_dir'] = self.models_dir_var.get()
            self.system_manager.config['Paths']['training_data_dir'] = self.training_data_dir_var.get()
            self.system_manager.config['Paths']['backup_dir'] = self.backup_dir_var.get()
            
            # 배치 처리 설정
            self.system_manager.config['Batch']['max_batch_size'] = str(self.max_batch_size_var.get())
            
            # 설정 저장
            self.system_manager.save_config()
            
            # 설정 적용
            self._apply_settings()
            
            # 성공 메시지
            messagebox.showinfo("완료", "설정이 저장되었습니다. 일부 설정은 프로그램 재시작 후 적용됩니다.")
            
            # 대화상자 닫기
            self.dialog.destroy()
        
        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 중 오류 발생: {e}")
    
    def _validate_settings(self):
        """설정 유효성 검사"""
        # 디렉토리 경로 확인
        for path_var, path_name in [
            (self.captures_dir_var, "캡처 저장 경로"),
            (self.models_dir_var, "모델 저장 경로"),
            (self.training_data_dir_var, "학습 데이터 경로"),
            (self.backup_dir_var, "백업 저장 경로")
        ]:
            path = path_var.get()
            
            # 경로가 비어있는지 확인
            if not path:
                messagebox.showwarning("경고", f"{path_name}를 입력하세요.")
                return False
            
            # 경로가 존재하는지 확인
            if not os.path.exists(path):
                # 디렉토리 생성 확인
                if messagebox.askyesno("확인", f"{path_name} '{path}'가 존재하지 않습니다. 생성하시겠습니까?"):
                    try:
                        os.makedirs(path, exist_ok=True)
                    except Exception as e:
                        messagebox.showerror("오류", f"{path_name} 생성 실패: {e}")
                        return False
                else:
                    return False
        
        # Tesseract 경로 확인
        tesseract_path = self.tesseract_path_var.get()
        if tesseract_path and not os.path.exists(tesseract_path):
            messagebox.showwarning("경고", f"Tesseract 경로 '{tesseract_path}'가 존재하지 않습니다.")
            return False
        
        return True
    
    def _apply_settings(self):
        """설정 적용"""
        try:
            # Tesseract 경로 업데이트
            tesseract_path = self.tesseract_path_var.get()
            if tesseract_path and os.path.exists(tesseract_path):
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            # 디렉토리 경로 업데이트
            self.system_manager.captures_dir = self.captures_dir_var.get()
            self.system_manager.models_dir = self.models_dir_var.get()
            self.system_manager.training_data_dir = self.training_data_dir_var.get()
            self.system_manager.backup_dir = self.backup_dir_var.get()
            
            # 디버그 모드 업데이트
            debug_mode = self.debug_mode_var.get()
            if debug_mode:
                # 디버그 디렉토리 확인
                os.makedirs(self.system_manager.debug_dir, exist_ok=True)
            
            return True
        except Exception as e:
            logger.error(f"설정 적용 오류: {e}")
            return False