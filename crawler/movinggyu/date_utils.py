import re


DATE_PATTERN = re.compile(r'(\d{2})\.\d{1,2}\.\d{1,2}')


def extract_year(date_text):
    """'25.05.26' 같은 날짜 문자열에서 4자리 연도를 추출합니다."""
    if not date_text:
        return None

    match = DATE_PATTERN.search(date_text)
    if not match:
        return None
    return int("20" + match.group(1))


def find_date_text(element, selectors=None):
    """목록 행 안에서 날짜처럼 보이는 텍스트를 찾습니다."""
    for selector in selectors or []:
        date_element = element.select_one(selector)
        if date_element:
            date_text = date_element.get_text(strip=True)
            if extract_year(date_text):
                return date_text

    match = DATE_PATTERN.search(element.get_text(" ", strip=True))
    return match.group(0) if match else ""
