# ui/__init__.py - FC 온라인 선수 카드 인식 시스템 UI 패키지 초기화

"""
FC 온라인 선수 카드 인식 시스템의 사용자 인터페이스 패키지

이 패키지는 다음과 같은 모듈을 포함합니다:
- main_window: 애플리케이션 메인 윈도우
- settings_dialog: 설정 대화상자
- roi_selector: ROI 선택 인터페이스
- training_dialog: 모델 학습 대화상자
- batch_processor: 배치 처리 인터페이스
"""

import logging
import tkinter as tk
from tkinter import ttk
import os
import sys

# 로거 설정
logger = logging.getLogger("FC_Online_Recognition.ui")

# 버전 정보
__version__ = "2.0.0"

# UI 모듈 임포트
from .main_window import MainWindow
from .settings_dialog import SettingsDialog
from .roi_selector import ROISelector
from .training_dialog import TrainingDialog
from .batch_processor import BatchProcessor

# UI 리소스 경로
def get_resource_path(relative_path):
    """리소스 파일의 절대 경로 반환"""
    try:
        # PyInstaller로 생성된 실행 파일인 경우
        base_path = sys._MEIPASS
    except Exception:
        # 일반 Python 스크립트인 경우
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# UI 스타일 초기화
def initialize_styles(scale_factor=1.0, theme=None):
    """UI 스타일 초기화"""
    style = ttk.Style()
    
    # 테마 설정
    if theme is None or theme == 'system':
        # 시스템 기본 테마 사용
        if os.name == 'nt':  # Windows
            style.theme_use('vista')
        else:  # Linux/Mac
            style.theme_use('clam')
    elif theme == 'light':
        style.theme_use('clam')
        
        # 밝은 테마 색상 설정
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabelframe', background='#f0f0f0')
        style.configure('TLabelframe.Label', background='#f0f0f0', foreground='#000000')
        style.configure('TLabel', background='#f0f0f0', foreground='#000000')
        style.configure('TButton', background='#e0e0e0')
        style.configure('TCheckbutton', background='#f0f0f0')
        style.configure('TRadiobutton', background='#f0f0f0')
    elif theme == 'dark':
        style.theme_use('clam')
        
        # 어두운 테마 색상 설정
        style.configure('TFrame', background='#2d2d2d')
        style.configure('TLabelframe', background='#2d2d2d')
        style.configure('TLabelframe.Label', background='#2d2d2d', foreground='#ffffff')
        style.configure('TLabel', background='#2d2d2d', foreground='#ffffff')
        style.configure('TButton', background='#404040')
        style.configure('TCheckbutton', background='#2d2d2d', foreground='#ffffff')
        style.configure('TRadiobutton', background='#2d2d2d', foreground='#ffffff')
        style.configure('TEntry', fieldbackground='#404040', foreground='#ffffff')
        style.configure('TCombobox', fieldbackground='#404040', foreground='#ffffff')
    
    # 글꼴 크기 조정
    default_font_size = int(10 * scale_factor)
    button_font_size = int(9 * scale_factor)
    title_font_size = int(12 * scale_factor)
    
    # 글꼴 설정
    try:
        if os.name == 'nt':  # Windows
            default_font = ('Malgun Gothic', default_font_size)
            button_font = ('Malgun Gothic', button_font_size)
            title_font = ('Malgun Gothic', title_font_size, 'bold')
        else:  # Linux/Mac
            default_font = ('Helvetica', default_font_size)
            button_font = ('Helvetica', button_font_size)
            title_font = ('Helvetica', title_font_size, 'bold')
        
        # 글꼴 적용
        style.configure('TLabel', font=default_font)
        style.configure('TButton', font=button_font)
        style.configure('TCheckbutton', font=default_font)
        style.configure('TRadiobutton', font=default_font)
        style.configure('TEntry', font=default_font)
        style.configure('TCombobox', font=default_font)
        
        # 특별 스타일
        style.configure('Title.TLabel', font=title_font)
        style.configure('Big.TButton', font=button_font)
        
        # 신뢰도 표시 스타일
        style.configure("High.TEntry", foreground="green", font=default_font)
        style.configure("Medium.TEntry", foreground="orange", font=default_font)
        style.configure("Low.TEntry", foreground="red", font=default_font)
        
        logger.info(f"UI 스타일 초기화 완료 (스케일: {scale_factor}, 테마: {theme})")
        return True
    except Exception as e:
        logger.error(f"UI 스타일 초기화 오류: {e}")
        return False

# 스플래시 화면 생성
def create_splash_screen(root, width=600, height=300):
    """시작 스플래시 화면 생성"""
    try:
        # 메인 창 숨기기
        root.withdraw()
        
        # 스플래시 창 생성
        splash = tk.Toplevel(root)
        splash.title("FC 온라인 선수 카드 정보 인식 시스템")
        
        # 화면 중앙에 표시
        screen_width = splash.winfo_screenwidth()
        screen_height = splash.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        splash.geometry(f"{width}x{height}+{x}+{y}")
        
        # 창 속성 설정 (테두리 없음)
        splash.overrideredirect(True)
        
        # 배경 프레임
        bg_frame = tk.Frame(splash, bg="#003366")
        bg_frame.pack(fill=tk.BOTH, expand=True)
        
        # 타이틀
        title_label = tk.Label(bg_frame, text="FC 온라인 선수 카드 정보 인식 시스템",
                             font=("Malgun Gothic", 20, "bold"), fg="white", bg="#003366")
        title_label.pack(pady=(30, 10))
        
        # 버전 정보
        version_label = tk.Label(bg_frame, text=f"버전 {__version__}",
                               font=("Malgun Gothic", 12), fg="lightgray", bg="#003366")
        version_label.pack(pady=5)
        
        # 로딩 메시지
        loading_var = tk.StringVar(value="시스템 초기화 중...")
        loading_label = tk.Label(bg_frame, textvariable=loading_var,
                               font=("Malgun Gothic", 12), fg="white", bg="#003366")
        loading_label.pack(pady=10)
        
        # 진행 바
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(bg_frame, variable=progress_var, length=400)
        progress_bar.pack(pady=10)
        
        logger.info("스플래시 화면 생성 완료")
        
        return {
            'window': splash,
            'progress_var': progress_var,
            'loading_var': loading_var
        }
    except Exception as e:
        logger.error(f"스플래시 화면 생성 오류: {e}")
        # 오류 발생 시 메인 창 다시 표시
        root.deiconify()
        return None

# 애플리케이션 초기화
def initialize_app(root, system_manager):
    """애플리케이션 초기화"""
    try:
        # 스타일 초기화
        scale_factor = float(system_manager.config.get('Settings', 'ui_scale', fallback='1.0'))
        theme = system_manager.config.get('Settings', 'theme', fallback='system')
        initialize_styles(scale_factor, theme)
        
        # 메인 윈도우 생성
        main_window = MainWindow(root, system_manager)
        
        logger.info("애플리케이션 초기화 완료")
        return main_window
    except Exception as e:
        logger.error(f"애플리케이션 초기화 오류: {e}")
        return None

def show_error_dialog(title, message):
    """오류 대화상자 표시"""
    try:
        error_window = tk.Tk()
        error_window.title(title)
        error_window.geometry("400x200")
        
        # 오류 메시지
        tk.Label(error_window, text=message, wraplength=380,
              font=("Malgun Gothic", 10), pady=20).pack()
        
        # 닫기 버튼
        tk.Button(error_window, text="닫기", command=error_window.destroy,
               font=("Malgun Gothic", 10), padx=20, pady=5).pack(pady=10)
        
        error_window.mainloop()
    except Exception as e:
        print(f"오류 대화상자 표시 실패: {e}")
        print(f"원본 오류: {message}")

__all__ = [
    'MainWindow',
    'SettingsDialog',
    'ROISelector',
    'TrainingDialog',
    'BatchProcessor',
    'initialize_styles',
    'create_splash_screen',
    'initialize_app',
    'get_resource_path',
    'show_error_dialog'
]