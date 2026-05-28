# config.py
# 크롤링 관련 설정
MAX_PAGES = 2000
MIN_YEAR = 2025

TARGET_BOARDS_CS = [
    {"category": "학사공지", "url": "https://cs.kookmin.ac.kr/news/notice/"},
    {"category": "취업공지", "url": "https://cs.kookmin.ac.kr/news/jobs/"},
    {"category": "장학공지", "url": "https://cs.kookmin.ac.kr/news/scholarship/"},
    {"category": "특강 및 행사", "url": "https://cs.kookmin.ac.kr/news/event/"}
] # 국민대학교 소프트웨어융합대학 공지사항

TARGET_BOARDS_SW = [
    {"category": "프로그램 및 행사", "url": "https://software.kookmin.ac.kr/software/bulletin/notice.do?mode=list&srCategoryId=350"},
    {"category": "산학협력", "url": "https://software.kookmin.ac.kr/software/bulletin/notice.do?mode=list&srCategoryId=351"},
    {"category": "학생지원", "url": "https://software.kookmin.ac.kr/software/bulletin/notice.do?mode=list&srCategoryId=352"},
    {"category": "기타", "url": "https://software.kookmin.ac.kr/software/bulletin/notice.do?mode=list&srCategoryId=353"}
] # SW중심대학사업단 공지사항

TARGET_BOARDS_KMU = [
    {"category": "국민대 학사공지", "url": "https://www.kookmin.ac.kr/user/kmuNews/notice/4/index.do?notcLwprtCatgrCd="},
    {"category": "국민대 장학공지", "url": "https://www.kookmin.ac.kr/user/kmuNews/notice/7/index.do?notcLwprtCatgrCd="}
] # 국민대학교 학사공지
