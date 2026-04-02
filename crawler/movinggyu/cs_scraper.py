# scraper.py
import requests
from bs4 import BeautifulSoup
import time
import re
from config import MAX_PAGES

class CsScraper:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def fetch_links(self, board_url):
        all_links = []
        
        # 1페이지부터 MAX_PAGES(예: 200)까지 반복
        for page in range(0, MAX_PAGES):
            # URL 끝에 '?pn=페이지번호'를 붙여서 새로운 주소 생성
            # (예: https://cs.kookmin.ac.kr/news/jobs/?pn=2)
            page_url = f"{board_url}?&pn={page}"
            print(f"👉 [{page}/{MAX_PAGES}] 페이지 탐색 중... ({page_url})")
            
            try:
                res = requests.get(page_url, headers=self.headers)
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # 아까 찾은 알맞은 선택자('li.subject a') 사용
                page_links = []
                for a in soup.select('li.subject a'):
                    if a.has_attr('href'):
                        href = a['href']
                        if href.startswith('./'):
                            full_url = board_url + href[1:]
                        elif href.startswith('/'):
                            full_url = board_url + href
                        else:
                            full_url = href
                        page_links.append(full_url.split('?pn')[0])
                
                # 💡 핵심 방어 로직: 만약 이 페이지에 긁어올 링크가 0개라면?
                # -> 더 이상 글이 없다는 뜻이므로 200페이지까지 안 가고 반복문을 마칩니다(break).
                if len(page_links) == 0:
                    print(f"   🚨 더 이상 게시글이 없습니다. {page}페이지에서 수집을 종료합니다.")
                    break
                    
                all_links.extend(page_links) # 긁어온 링크를 큰 보따리에 합치기
                
                # 서버에 공격(DDoS)으로 오해받지 않기 위해 1초 대기 (매우 중요!)
                time.sleep(1)
                
            except Exception as e:
                print(f"   ❌ {page}페이지 접속 중 에러 발생: {e}")
                break # 에러가 나면 다음 게시판으로 넘어가도록 멈춤
                
        # 중복 제거 후 반환
        final_links = list(set(all_links))
        print(f"✅ 이 게시판에서 총 {len(final_links)}개의 링크를 찾았습니다!\n")
        return final_links
    
    
    def fetch_content(self, url, category):
        """상세 페이지에서 텍스트, 본문 내 링크, 이미지 주소 추출"""
        try:
            res = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 1. 제목 & 날짜
            title_element = soup.select_one('td.view-title')
            title = title_element.text.strip() if title_element else "제목 없음"
            
            date_element = soup.select_one('th.aricle-subject + td')
            date = date_element.text.strip() if date_element else "날짜 없음"
            
            # 2. 본문 상자 찾기
            content_element = soup.select_one('div#view-detail-data') 
            
            content_text = "본문 없음"
            content_links = []  # 본문 속 하이퍼링크들을 담을 빈 보따리
            content_images = [] # 본문 속 이미지 주소들을 담을 빈 보따리

            if content_element:
                # (1) 줄바꿈 역할을 하는 태그 뒤에만 \n 추가
                for block in content_element.find_all(['p', 'div', 'tr', 'li', 'br']):
                    if block.name == 'br':
                        block.replace_with('\n')
                    else:
                        block.append('\n')
                
                # (2) 텍스트 추출 (separator=""로 글자 조각남 방지)
                raw_text = content_element.get_text(separator="")
                
                # (3) 특수 공백(\xa0) 제거 및 각 줄 앞뒤 공백 깎기
                text = raw_text.replace('\xa0', ' ')
                lines = [line.strip() for line in text.splitlines()]
                
                # (4) 문장 중간 중복 스페이스 압축
                processed_lines = [re.sub(r' +', ' ', line) for line in lines]
                intermediate_text = '\n'.join(processed_lines)

                # (5) 🎯 요청하신 개행 정제 규칙 (핵심)
                # 4개 이상 연속 개행 -> 임시 마커로 변환 (나중에 \n\n이 됨)
                cleaned_text = re.sub(r'\n{4,}', '___DBL_NL___', intermediate_text)
                # 2~3개 연속 개행 -> 1개(\n)로 압축 (문단 붙이기)
                cleaned_text = re.sub(r'\n{2,3}', '\n', cleaned_text)
                # 마커를 다시 \n\n으로 복구
                content_text = cleaned_text.replace('___DBL_NL___', '\n\n').strip()
                
                # 2-2. 본문 속 <a> 태그(링크) 모두 찾기
                for a_tag in content_element.find_all('a'):
                    if a_tag.has_attr('href'):
                        href = a_tag['href']
                        # 불필요한 자바스크립트 실행 링크 등은 제외하고 저장
                        if not href.startswith('javascript:'):
                            content_links.append(href)
                            
                # 2-3. 본문 속 <img> 태그(이미지) 모두 찾기
                for img_tag in content_element.find_all('img'):
                    if img_tag.has_attr('src'):
                        src = img_tag['src']
                        # 이미지 주소가 //로 시작하면 https: 를 붙여줌 (예: //wfile... -> https://wfile...)
                        if src.startswith('//'):
                            src = "https:" + src
                        content_images.append(src)

            # 3. 첨부파일 찾기
            attachments = []
            # 클래스가 attach-file인 td 태그 안의 모든 a 태그(링크)를 찾습니다.
            for a_tag in soup.select('td.attach-file a'):
                if a_tag.has_attr('href'):
                    href = a_tag['href']
                    attachments.append(href)

            return {
                "title": title, 
                "date": date, 
                "content": content_text,
                "attachments": list(set(attachments)),
                "attached_links": list(set(content_links)),   # 리스트 형태로 저장됨
                "attached_images": list(set(content_images)), # 리스트 형태로 저장됨
                "url": url, 
                "category": category
            }
            
        except Exception as e:
            print(f"내용 추출 에러: {e}")
            return None
        
if __name__ == "__main__":
    # 1. 크롤러 준비
    sc = CsScraper()
    test_board_url = "https://cs.kookmin.ac.kr/news/jobs/"
    
    print("🚀 [테스트 1단계] 게시판 링크 수집을 시작합니다...")
    temp_links = sc.fetch_links(test_board_url)
    
    # 2. 결과 확인 및 상세 페이지 테스트
    if temp_links:
        for i in temp_links:
            print(i)
        print(f"\n✅ 성공적으로 {len(temp_links)}개의 링크를 수집했습니다.")
        
        # 기본적으로 첫 번째 수집된 글로 테스트하지만,
        # 💡 만약 아까 발견하신 그 특정 글(tikorea-recruit.com 링크가 있던 글)을 
        # 바로 테스트하고 싶다면 아래 test_target 변수에 직접 그 주소를 넣으셔도 됩니다!
        test_target = temp_links[0] 
        test_target = "https://cs.kookmin.ac.kr/news/notice/2800"
        # test_target = "https://cs.kookmin.ac.kr/news/jobs/여기에_그_글_번호"
        
        print(f"\n🚀 [테스트 2단계] 상세 페이지 추출 중... ({test_target})")
        
        # 상세 페이지 수집 함수 실행
        content_data = sc.fetch_content(test_target, category="취업공지")
        
        if content_data:
            print("\n🎉 상세 내용 추출 성공! 데이터 형태는 아래와 같습니다.")
            print("=" * 60)
            print(f"👉 [분류] {content_data['category']}")
            print(f"👉 [제목] {content_data['title']}")
            print(f"👉 [날짜] {content_data['date']}")
            print(f"👉 [본문 미리보기]\n{content_data['content'][:]}") 
            print("-" * 60)
            
            # 🎯 새롭게 추가된 링크 추출 확인 부분
            print(f"🔗 [본문 속 하이퍼링크] - 총 {len(content_data['attached_links'])}개 발견")
            if content_data['attached_links']:
                for i, link in enumerate(content_data['attached_links'], 1):
                    print(f"   {i}. {link}")
            else:
                print("   (발견된 링크가 없습니다)")
            
            print("-" * 60)
            
            # 🎯 새롭게 추가된 링크 추출 확인 부분
            print(f"🔗 [본문 속 첨부파일] - 총 {len(content_data['attachments'])}개 발견")
            if content_data['attachments']:
                for i, link in enumerate(content_data['attachments'], 1):
                    print(f"   {i}. {link}")
            else:
                print("   (발견된 첨부파일이 없습니다)")
            
            print("-" * 60)
            
            # 🎯 새롭게 추가된 이미지 추출 확인 부분
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