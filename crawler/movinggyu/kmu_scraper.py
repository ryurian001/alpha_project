import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin
from config import MAX_PAGES, MIN_YEAR
from date_utils import extract_year, find_date_text

class KmuScraper:
    """국민대학교(KMU) 추가 크롤러 기본 뼈대(Skeleton)"""
    
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def fetch_links(self, board_url):
        """목록 페이지에서 페이지를 넘겨가며 상세 링크를 수집합니다."""
        all_links = []
        
        for page in range(1, MAX_PAGES + 1):
            stop_by_year = False
            page_url = f"{board_url}&currentPageNo={page}"
            print(f"👉 [KMU {page}/{MAX_PAGES}] 페이지 탐색 중... ({page_url})")
            
            try:
                res = requests.get(page_url, headers=self.headers)
                soup = BeautifulSoup(res.text, 'html.parser')
                
                items = soup.select('div.board_list > ul > li')
                
                page_links = []
                for item in items:
                    # 상단 고정 공지(li.notice)는 목록에 날짜가 없으므로 
                    # 날짜가 존재하는 일반 게시글(div.board_etc) 위주로 날짜 체크
                    date_area = item.select_one('div.board_etc span')
                    if date_area:
                        date_text = date_area.text.strip() # 예: "2026.05.22"
                        year = extract_year(date_text)
                        
                        if year and year < MIN_YEAR:
                            print(f"   🛑 {date_text} 게시글이 발견되어 {MIN_YEAR}년 이전 탐색을 종료합니다.")
                            stop_by_year = True
                            break

                    a = item.select_one('a')
                    if a and a.has_attr('href'):
                        href = a['href']
                        # urljoin을 이용해 상대/절대경로 병합
                        full_url = urljoin(board_url, href)
                        page_links.append(full_url)

                if len(page_links) == 0 and page > 1:
                    print(f"   🚨 더 이상 게시글이 없습니다. {page}페이지에서 수집을 종료합니다.")
                    break
                    
                all_links.extend(page_links)

                if stop_by_year:
                    break

                time.sleep(1)
                
            except Exception as e:
                print(f"   ❌ {page}페이지 접속 중 에러 발생: {e}")
                break
                
        final_links = list(dict.fromkeys(all_links))
        print(f"✅ 이 게시판에서 총 {len(final_links)}개의 링크를 찾았습니다!\n")
        return final_links

    def fetch_content(self, url, category):
        """상세 페이지에서 내용 추출"""
        try:
            res = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 제목 추출
            title_element = soup.select_one('p.view_tit')
            title = title_element.text.strip() if title_element else "제목 없음"
            
            # 날짜 추출 ('작성일 ' 텍스트 제거)
            date_element = soup.select_one('div.board_etc span')
            date = "날짜 없음"
            if date_element:
                date = date_element.text.replace("작성일", "").strip()

            # 첨부파일 링크 추출
            attachments = []
            for a_tag in soup.select('div.board_atc.file ul li a'):
                if a_tag.has_attr('href'):
                    href = a_tag['href']
                    attachments.append(urljoin(url, href))

            # 본문 영역 추출
            content_element = soup.select_one('div.view_inner') 
            content_text = "본문 없음"
            content_links = []
            content_images = []

            if content_element:
                for br in content_element.find_all('br'):
                    br.replace_with('\n')
                for block in content_element.find_all(['p', 'div', 'li']):
                    block.append('\n')
                
                raw_text = content_element.get_text()
                content_text = re.sub(r'\n\s*\n', '\n\n', raw_text).strip()
                
                # 본문 내 링크 추출
                for a_tag in content_element.find_all('a'):
                    if a_tag.has_attr('href'):
                        href = a_tag['href']
                        if not href.startswith('javascript:'):
                            content_links.append(urljoin(url, href))
                            
                # 본문 내 이미지 주소 추출
                for img_tag in content_element.find_all('img'):
                    if img_tag.has_attr('src'):
                        src = img_tag['src']
                        content_images.append(urljoin(url, src))

                # 혹시모르는 전처리 한번 더 (본문 내 개행 정제)
                # 1. <br> 태그를 실제 개행(\n)으로 치환
                for br in content_element.find_all('br'):
                    br.replace_with('\n')
                
                # 2. 주요 블록 태그 뒤에 개행을 붙여서 텍스트가 붙어버리는 현상 방지
                for block in content_element.find_all(['p', 'div', 'li']):
                    block.append('\n')
                
                # 3. 전체 텍스트 추출 및 특수 공백(\xa0) 제거
                raw_text = content_element.get_text().replace('\xa0', ' ')
                
                # 4. 각 줄별로 쪼개어 앞뒤 공백을 trim 처리
                lines = [line.strip() for line in raw_text.split('\n')]
                
                # 5. 불필요하게 낭비되는 빈 줄 압축 (연속된 빈 줄은 1개만 인정)
                compact_lines = []
                for line in lines:
                    if line:
                        compact_lines.append(line)
                    elif compact_lines and compact_lines[-1] != "":
                        compact_lines.append("")
                
                # 6. ⭐ 핵심: 모든 줄을 단 하나의 '개행(\n)'으로만 엮어서 완전한 단일 문자열 생성
                content_text = '\n'.join(compact_lines).strip()

            return {
                "title": title, 
                "date": date, 
                "content": content_text, 
                "attachments": list(set(attachments)), 
                "attached_links": list(set(content_links)), 
                "attached_images": list(set(content_images)), 
                "url": url, 
                "category": category
            }
            
        except Exception as e:
            print(f"내용 추출 에러: {e}")
            return None
        

if __name__ == "__main__":
    # 테스트 실행 구역
    sc = KmuScraper()
    test_board = "https://www.kookmin.ac.kr/user/kmuNews/notice/4/index.do?notcLwprtCatgrCd="
    print("🚀 국민대학교 학사공지 수집 테스트를 시작합니다.")
    links = sc.fetch_links(test_board)
    
    if links:
        print(f"🔎 수집된 첫 번째 글 샘플 파싱 중... ({links[0]})")
        sample_data = sc.fetch_content(links[0], "학사공지")
        print(sample_data)