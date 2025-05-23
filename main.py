# fc_card_recognition/main.py
import logging
import tkinter as tk
from pathlib import Path
import os
import sys

# 로깅 설정을 위한 기본 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fc_online_recognition.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FC_Online_Recognition")

def show_splash_screen(root):
    """시작 스플래시 화면 표시"""
    # 메인 창 숨기기
    root.withdraw()
    
    # 스플래시 창 생성
    splash = tk.Toplevel(root)
    splash.title("FC 온라인 선수 카드 정보 인식 시스템")
    
    # 화면 중앙에 표시
    window_width = 600
    window_height = 300
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    splash.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # 창 속성 설정 (테두리 없음)
    splash.overrideredirect(True)
    
    # 배경 프레임
    bg_frame = tk.Frame(splash, bg="#003366")
    bg_frame.pack(fill=tk.BOTH, expand=True)
    
    # 타이틀
    title_label = tk.Label(bg_frame, text="FC 온라인 선수 카드 정보 인식 시스템",
                        font=("Gulim", 20, "bold"), fg="white", bg="#003366")
    title_label.pack(pady=(30, 10))
    
    # 버전 정보
    version_label = tk.Label(bg_frame, text="버전 2.0.0",
                          font=("Gulim", 12), fg="lightgray", bg="#003366")
    version_label.pack(pady=5)
    
    # 로딩 메시지
    loading_var = tk.StringVar(value="시스템 초기화 중...")
    loading_label = tk.Label(bg_frame, textvariable=loading_var,
                          font=("Gulim", 12), fg="white", bg="#003366")
    loading_label.pack(pady=10)
    
    # 진행 바
    from tkinter import ttk
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(bg_frame, variable=progress_var, length=400)
    progress_bar.pack(pady=10)
    
    return splash, progress_var, loading_var

def main():
    """메인 함수"""
    try:
        # 시작 로그
        logger.info("FC 온라인 선수 카드 정보 인식 시스템 시작")
        
        # Tkinter 루트 윈도우 생성
        root = tk.Tk()
        
        # 스플래시 화면 표시
        splash, progress_var, loading_var = show_splash_screen(root)
        
        # 모듈 로드 (지연 임포트로 시작 시간 단축)
        def update_progress(value, text):
            progress_var.set(value)
            loading_var.set(text)
            splash.update()
        
        # 단계별 초기화
        update_progress(10, "설정 로드 중...")
        from config import Config
        config = Config()
        
        update_progress(30, "시스템 초기화 중...")
        from core.system import FCCardSystem
        system = FCCardSystem(config)
        
        update_progress(60, "UI 초기화 중...")
        from ui.main_window import MainWindow
        app = MainWindow(root, system)
        
        update_progress(90, "시스템 시작 중...")
        
        # 스플래시 화면 닫고 메인 창 표시
        update_progress(100, "준비 완료!")
        
        # 1초 후 스플래시 닫기
        def close_splash():
            splash.destroy()
            root.deiconify()  # 메인 창 표시
            
        splash.after(1000, close_splash)
        
        # 메인 루프 시작
        root.mainloop()
        
    except Exception as e:
        logger.critical(f"심각한 오류: {e}")
        import traceback
        logger.critical(traceback.format_exc())
        
        try:
            import tkinter.messagebox as msgbox
            msgbox.showerror("심각한 오류", 
                           f"시스템 초기화 중 오류가 발생했습니다:\n\n{str(e)}")
        except:
            pass
    finally:
        # 종료 로그
        logger.info("FC 온라인 선수 카드 정보 인식 시스템 종료")

if __name__ == "__main__":
    main()