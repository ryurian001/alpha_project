# config.py
# 크롤링 관련 설정
MAX_PAGES = 5

TARGET_BOARDS_CS = [
    {"category": "학사공지", "url": "https://cs.kookmin.ac.kr/news/notices/"},
    {"category": "취업공지", "url": "https://cs.kookmin.ac.kr/news/jobs/"},
    {"category": "장학공지", "url": "https://cs.kookmin.ac.kr/news/scholarship/"},
    {"category": "특강 및 행사", "url": "https://cs.kookmin.ac.kr/news/event/"}
]

TARGET_BOARDS_SW = [
    {},
    {}
]