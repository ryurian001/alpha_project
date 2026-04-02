import requests
from bs4 import BeautifulSoup
import time
import re
from config import MAX_PAGES

class SwScraper:
    """SW중심대학(software.kookmin.ac.kr) 전용 크롤러"""
    
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.base_domain = "https://software.kookmin.ac.kr"

    def fetch_links(self, board_url, category):
        """목록 페이지에서 페이지를 넘겨가며 상세 링크를 수집합니다."""
        all_links = []
        
        for page in range(1, MAX_PAGES + 1):
            offset = (page - 1) * 10
            page_url = f"{board_url}&article.offset={offset}"
            print(f"👉 [SW중심대학 {page}/{MAX_PAGES}] 페이지 탐색 중... ({page_url})")
            
            try:
                res = requests.get(page_url, headers=self.headers)
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # 1. 게시판 테이블의 모든 행(tr)을 가져옵니다.
                rows = soup.select('table.board-table tbody tr')
                
                page_links = []
                for tr in rows:
                    tds = tr.find_all('td')
                    # 분류 정보는 보통 두 번째 td(인덱스 1)에 위치합니다.
                    if len(tds) > 1:
                        row_category = tds[1].get_text(strip=True)
                        
                        # 2. 파라미터로 받은 category와 행의 분류가 일치하는지 확인합니다.
                        if row_category == category:
                            # 3. 일치할 경우에만 해당 행 안에서 링크(a 태그)를 찾습니다.
                            a = tr.select_one('div.b-title-box a')
                            if a and a.has_attr('href'):
                                href = a['href']
                                
                                # URL 정제 및 결합 로직
                                if href.startswith('?'):
                                    base_path = board_url.split('?')[0]
                                    full_url = base_path + href
                                elif href.startswith('/'):
                                    full_url = self.base_domain + href
                                else:
                                    full_url = href
                                
                                # &article.offset 이후 파라미터 제거
                                clean_url = full_url.split('&article.offset')[0]
                                page_links.append(clean_url)
                
                if len(page_links) == 0 and page > 1:
                    # 해당 페이지에 조건에 맞는 글이 하나도 없으면 종료 로직 (선택 사항)
                    # 실제로는 다음 페이지에 있을 수 있으므로 break 대신 계속 진행할 수도 있습니다.
                    pass
                    
                all_links.extend(page_links)
                time.sleep(1) 
                
            except Exception as e:
                print(f"   ❌ {page}페이지 접속 중 에러 발생: {e}")
                break
                
        final_links = list(set(all_links))
        print(f"✅ {category} 카테고리에서 총 {len(final_links)}개의 링크를 찾았습니다!\n")
        return final_links

    def fetch_content(self, url, category):
        """상세 페이지에서 텍스트, 본문 링크/이미지, 그리고 '공식 첨부파일' 추출"""
        try:
            res = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 1. 제목
            title_element = soup.select_one('span.b-title')
            title = title_element.text.strip() if title_element else "제목 없음"
            
            # 2. 날짜
            date_element = soup.select_one('li.b-date-box span')
            date = date_element.text.strip() if date_element else "날짜 없음"

            # 3. 공식 첨부파일 찾기
            attachments = []
            for a_tag in soup.select('div.b-popup-file-box ul li a'):
                if a_tag.has_attr('href'):
                    href = a_tag['href']
                    # 첨부파일 링크가 '?mode=download...' 형태이므로 앞부분 주소 합성
                    if href.startswith('?'):
                        base_path = url.split('?')[0] 
                        href = base_path + href
                    elif href.startswith('/'):
                        href = self.base_domain + href
                    attachments.append(href)

            # 4. 본문 텍스트, 본문 속 링크 및 이미지 찾기
            content_element = soup.select_one('div.b-content-box') 
            content_text = "본문 없음"
            content_links = []
            content_images = []

            if content_element:
                # 1. <br> 태그를 실제 엔터키(\n)로 바꿉니다.
                for br in content_element.find_all('br'):
                    br.replace_with('\n')
                    
                # 2. <p>, <div>, <li> 처럼 문단이 나뉘는 태그 끝에도 엔터키(\n)를 붙여줍니다.
                for block in content_element.find_all(['p', 'div', 'li']):
                    block.append('\n')
                
                # 3. 텍스트를 추출합니다.
                raw_text = content_element.get_text()
                
                # 4. 엔터키가 너무 여러 개(\n\n\n\n) 연속으로 있으면 지저분하므로, 최대 2개(\n\n)로 압축합니다.
                content_text = re.sub(r'\n\s*\n', '\n\n', raw_text).strip()
                
                # 본문 내 링크 추출
                for a_tag in content_element.find_all('a'):
                    if a_tag.has_attr('href'):
                        href = a_tag['href']
                        if not href.startswith('javascript:'):
                            if href.startswith('?'):
                                base_path = url.split('?')[0]
                                href = base_path + href
                            elif href.startswith('/'): 
                                href = self.base_domain + href
                            content_links.append(href)
                            
                # 본문 내 이미지 추출
                for img_tag in content_element.find_all('img'):
                    if img_tag.has_attr('src'):
                        src = img_tag['src']
                        if src.startswith('//'): src = "https:" + src
                        elif src.startswith('./'): src = self.base_domain + src[1:]
                        elif src.startswith('/'): src = self.base_domain + src
                        content_images.append(src)

            # 5. 최종 결과 반환
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

# ==========================================
# 테스트 실행 블록
# ==========================================
if __name__ == "__main__":
    # 1. 크롤러 준비 (SW중심대학 크롤러 기준)
    sc = SwScraper()
    test_board_url = "https://software.kookmin.ac.kr/software/bulletin/notice.do"
    test_board_url = "https://software.kookmin.ac.kr/software/bulletin/notice.do?mode=list&srCategoryId=350"
    
    print("🚀 [테스트 1단계] 게시판 링크 수집을 시작합니다...")
    # 테스트용이므로 1페이지(max_pages=1)만 빠르게 가져옵니다.
    temp_links = sc.fetch_links(test_board_url, "프로그램 및 행사")
    
    # 2. 결과 확인 및 상세 페이지 테스트
    if temp_links:
        for i in temp_links:
            print(i)
        print(f"\n✅ 성공적으로 {len(temp_links)}개의 링크를 수집했습니다.")
        
        # 기본적으로 첫 번째 수집된 글로 테스트하지만,
        # 특정 글을 테스트하고 싶다면 아래 주석을 풀고 주소를 넣으세요!
        test_target = temp_links[0] 
        # test_target = "https://software.kookmin.ac.kr/software/bulletin/notice.do?mode=view&articleNo=5935074"
        
        print(f"\n🚀 [테스트 2단계] 상세 페이지 추출 중... ({test_target})")
        
        # 상세 페이지 수집 함수 실행
        content_data = sc.fetch_content(test_target, category="공지사항")
        
        if content_data:
            print("\n🎉 상세 내용 추출 성공! 데이터 형태는 아래와 같습니다.")
            print("=" * 60)
            print(f"👉 [분류] {content_data['category']}")
            print(f"👉 [제목] {content_data['title']}")
            print(f"👉 [날짜] {content_data['date']}")
            print(f"👉 [본문 미리보기]\n{content_data['content']}") # 너무 길면 터미널 보기 힘드니 200자만
            print("-" * 60)
            
            # 🎯 링크 추출 확인 부분 (has_ 변수 없이 리스트로만 체크)
            print(f"🔗 [본문 속 하이퍼링크] - 총 {len(content_data['attached_links'])}개 발견")
            if content_data['attached_links']:
                for i, link in enumerate(content_data['attached_links'], 1):
                    print(f"   {i}. {link}")
            else:
                print("   (발견된 링크가 없습니다)")
            
            print("-" * 60)
            
            # 🎯 첨부파일 추출 확인 부분
            print(f"📁 [본문 속 첨부파일] - 총 {len(content_data['attachments'])}개 발견")
            if content_data['attachments']:
                for i, link in enumerate(content_data['attachments'], 1):
                    print(f"   {i}. {link}")
            else:
                print("   (발견된 첨부파일이 없습니다)")
            
            print("-" * 60)
            
            # 🎯 이미지 추출 확인 부분
            print(f"🖼️ [본문 속 이미지 주소] - 총 {len(content_data['attached_images'])}개 발견")
            if content_data['attached_images']:
                for i, img in enumerate(content_data['attached_images'], 1):
                    print(f"   {i}. {img}")
            else:
                print("   (발견된 이미지가 없습니다)")
            print("=" * 60)
            
        else:
            print("\n❌ 상세 내용 추출에 실패했습니다.")
    else:
        print("\n❌ 수집된 링크가 없습니다.")