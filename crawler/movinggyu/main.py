# main.py
import json
import os
import time
from cs_scraper import CsScraper
from sw_scraper import SwScraper
from config import TARGET_BOARDS_CS, TARGET_BOARDS_SW

def load_existing_data(filename):
    """기존에 수집된 JSON 데이터를 읽어옵니다."""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def main():
    output_filename = "kookmin_notices.json"
    
    # 1. 기존 데이터 로드 및 URL 세트 생성 (중복 체크용)
    existing_data = load_existing_data(output_filename)
    # URL로만 빠르게 대조하기 위해 set을 사용합니다.
    existing_urls = {item['url'] for item in existing_data}
    
    print(f"📂 기존 데이터 {len(existing_urls)}건을 확인했습니다. 중복은 제외하고 수집합니다.")

    cs_scraper = CsScraper()
    sw_scraper = SwScraper()
    
    new_count = 0

    # 2. 소프트웨어융합대학(CS) 공지 수집
    print("\n🚀 [CS] 소프트웨어융합대학 공지사항 수집 시작...")
    for board in TARGET_BOARDS_CS:
        # config.py의 오타가 고쳐진 URL로 링크 수집
        links = cs_scraper.fetch_links(board['url'])
        
        for link in links:
            # 🎯 중복 체크: 이미 있는 URL이면 무시
            if link in existing_urls:
                continue
            
            data = cs_scraper.fetch_content(link, board['category'])
            if data:
                data['source'] = "CS"
                existing_data.append(data)
                existing_urls.add(link) # 새로 추가된 것도 세트에 기록
                new_count += 1
                print(f"   [NEW] {data['title'][:30]}...")

    # 3. SW중심대학사업단(SW) 공지 수집
    print("\n🚀 [SW] SW중심대학사업단 공지사항 수집 시작...")
    for board in TARGET_BOARDS_SW:
        links = sw_scraper.fetch_links(board['url'], board['category'])
        
        for link in links:
            # 🎯 중복 체크: 이미 있는 URL이면 무시
            if link in existing_urls:
                continue
                
            data = sw_scraper.fetch_content(link, board['category'])
            if data:
                data['source'] = "SW"
                existing_data.append(data)
                existing_urls.add(link)
                new_count += 1
                print(f"   [NEW] {data['title'][:30]}...")

    # 4. 최종 결과 저장 (기존 데이터 + 신규 데이터)
    if new_count > 0:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
        print(f"\n✨ 수집 완료! 새롭게 추가된 데이터: {new_count}건")
    else:
        print("\n✨ 새로 수집된 데이터가 없습니다.")

if __name__ == "__main__":
    main()