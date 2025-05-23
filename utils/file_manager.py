# fc_card_recognition/utils/file_manager.py
import os
import shutil
import logging
import csv
import json
from datetime import datetime

logger = logging.getLogger("FC_Online_Recognition")

class FileManager:
    """파일 관리 유틸리티 클래스"""
    def __init__(self, config):
        """초기화"""
        self.config = config
        self.base_dir = config.get_path('base_dir')
        self.captures_dir = config.get_path('captures_dir')
    
    def get_image_files(self, directory=None, sort_by_date=True):
        """디렉토리의 이미지 파일 목록 반환"""
        if directory is None:
            directory = self.captures_dir
        
        try:
            # 이미지 확장자
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
            
            # 파일 목록
            files = []
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                # 파일만 처리
                if not os.path.isfile(file_path):
                    continue
                
                # 이미지 파일만 처리
                ext = os.path.splitext(filename)[1].lower()
                if ext not in image_extensions:
                    continue
                
                # 파일 정보
                file_info = {
                    'name': filename,
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'modified': os.path.getmtime(file_path)
                }
                
                files.append(file_info)
            
            # 정렬
            if sort_by_date:
                files.sort(key=lambda x: x['modified'], reverse=True)
            else:
                files.sort(key=lambda x: x['name'])
            
            return files
            
        except Exception as e:
            logger.error(f"이미지 파일 목록 조회 오류: {e}")
            return []
    
    def search_image_files(self, keyword, directory=None):
        """키워드로 이미지 파일 검색"""
        if directory is None:
            directory = self.captures_dir
        
        try:
            # 모든 이미지 파일
            all_files = self.get_image_files(directory, sort_by_date=False)
            
            # 키워드 검색
            keyword = keyword.lower()
            filtered_files = [f for f in all_files if keyword in f['name'].lower()]
            
            # 최신순 정렬
            filtered_files.sort(key=lambda x: x['modified'], reverse=True)
            
            return filtered_files
            
        except Exception as e:
            logger.error(f"이미지 파일 검색 오류: {e}")
            return []
    
    def delete_file(self, file_path):
        """파일 삭제"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"파일을 찾을 수 없습니다: {file_path}")
                return False
            
            # 파일 삭제
            os.remove(file_path)
            
            logger.info(f"파일 삭제 완료: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"파일 삭제 오류: {e}")
            return False
    
    def export_results(self, results, file_path):
        """인식 결과 내보내기"""
        try:
            # 파일 확장자 확인
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.csv':
                # CSV 내보내기
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # 헤더
                    writer.writerow(['필드', '값', '신뢰도'])
                    
                    # 데이터
                    for field, value in results['results'].items():
                        confidence = results['confidences'].get(field, 0.0)
                        writer.writerow([field, value, f"{confidence:.2f}"])
            
            elif ext == '.json':
                # JSON 내보내기
                export_data = {
                    'results': results['results'],
                    'confidences': results['confidences'],
                    'timestamp': datetime.now().isoformat()
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            else:
                # 텍스트 내보내기
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"FC 온라인 선수 카드 인식 결과\n")
                    f.write(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    
                    for field, value in results['results'].items():
                        confidence = results['confidences'].get(field, 0.0)
                        f.write(f"{field}: {value} (신뢰도: {confidence:.2f})\n")
            
            logger.info(f"인식 결과 내보내기 완료: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"인식 결과 내보내기 오류: {e}")
            return False
    
    def batch_process_export(self, batch_results, file_path):
        """배치 처리 결과 내보내기"""
        try:
            # 파일 확장자 확인
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.csv':
                # CSV 내보내기
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # 헤더
                    writer.writerow(['파일명', '오버롤', '포지션', '시즌 아이콘', '급여', '선수 이름', '강화 레벨', '부스트 레벨'])
                    
                    # 데이터
                    for result in batch_results:
                        if result.get('success', False):
                            data = result['results']
                            writer.writerow([
                                os.path.basename(result['file']),
                                data.get('overall', ''),
                                data.get('position', ''),
                                data.get('season_icon', ''),
                                data.get('salary', ''),
                                data.get('player_name', ''),
                                data.get('enhance_level', ''),
                                data.get('boost_level', '')
                            ])
            
            elif ext == '.json':
                # JSON 내보내기
                export_data = {
                    'timestamp': datetime.now().isoformat(),
                    'total_files': len(batch_results),
                    'success_count': sum(1 for r in batch_results if r.get('success', False)),
                    'error_count': sum(1 for r in batch_results if not r.get('success', False)),
                    'results': batch_results
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            else:
                # 텍스트 내보내기
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"FC 온라인 선수 카드 배치 인식 결과\n")
                    f.write(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"총 파일 수: {len(batch_results)}\n\n")
                    
                    for result in batch_results:
                        f.write(f"\n파일: {os.path.basename(result['file'])}\n")
                        
                        if result.get('success', False):
                            data = result['results']
                            f.write(f"오버롤: {data.get('overall', '')}\n")
                            f.write(f"포지션: {data.get('position', '')}\n")
                            f.write(f"시즌 아이콘: {data.get('season_icon', '')}\n")
                            f.write(f"급여: {data.get('salary', '')}\n")
                            f.write(f"선수 이름: {data.get('player_name', '')}\n")
                            f.write(f"강화 레벨: {data.get('enhance_level', '')}\n")
                            f.write(f"부스트 레벨: {data.get('boost_level', '')}\n")
                        else:
                            f.write(f"오류: {result.get('error', '알 수 없는 오류')}\n")
            
            logger.info(f"배치 처리 결과 내보내기 완료: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"배치 처리 결과 내보내기 오류: {e}")
            return False