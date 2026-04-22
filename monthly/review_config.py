"""
monthly/review_config.py
-------------------------
히어로 제품 리뷰 크롤링 셀렉터 설정.

각 채널의 리뷰 페이지 CSS 셀렉터를 아래에 직접 입력하세요.
wait_selector가 비어있으면 해당 채널 리뷰 크롤링을 건너뜁니다.

셀렉터 필드 설명:
  wait_selector : 리뷰 목록이 로드됐는지 확인하는 요소 (필수)
  container     : 리뷰 1건을 감싸는 요소
  date          : 작성일 텍스트 요소
  rating        : 별점 숫자 텍스트 요소
  reviewer      : 작성자명 텍스트 요소
  content       : 리뷰 본문 텍스트 요소
  next_btn      : 다음 페이지 버튼 (없으면 빈 문자열)
  max_pages     : 최대 크롤링 페이지 수 (기본 3)
"""

REVIEW_SELECTORS = {
    "naver": {
        "review_btn":    "#content > div > div.fUgLLODhD8 > div:nth-child(1) > div > div > div.PSOcMLEJuY > button",         # '리뷰전체보기' 버튼 셀렉터
        "wait_selector": "#MODAL_ROOT_ID > div > div.qc8qCgj4u2.b3VJJSdlmJ > div > div > div.ckqgS03UN6 > div > div > div:nth-child(1) > div > div.ZDSfEuYSzZ > strong",         # 리뷰 목록 로드 완료 확인용 (필수)
        "container":     ".PYRRKjHPB6",         # 리뷰 1건 감싸는 요소
        "date":          ".dgOMiF9qbL span:nth-child(2)",
        "rating":        ".F6N7Rr56mQ",
        "reviewer":      ".dgOMiF9qbL span:nth-child(1)",
        "content":       "p.Uv4T3VkhKU",
        "scroll_container": "div.ckqgS03UN6",  # 리뷰 모달 스크롤 컨테이너
        "next_btn":      "",         # 네이버는 무한스크롤이므로 보통 불필요
        "max_pages":     1,
    },
    "coupang": {
        "wait_selector": "",
        "container":     "",
        "date":          "",
        "rating":        "",
        "reviewer":      "",
        "content":       "",
        "next_btn":      "",
        "max_pages":     3,
    },
    "oliveyoung": {
        "wait_selector": "",
        "container":     "",
        "date":          "",
        "rating":        "",
        "reviewer":      "",
        "content":       "",
        "next_btn":      "",
        "max_pages":     3,
    },
    "kakao": {
        "wait_selector": "",
        "container":     "",
        "date":          "",
        "rating":        "",
        "reviewer":      "",
        "content":       "",
        "next_btn":      "",
        "max_pages":     3,
    },
    "daiso": {
        "wait_selector": "",
        "container":     "",
        "date":          "",
        "rating":        "",
        "reviewer":      "",
        "content":       "",
        "next_btn":      "",
        "max_pages":     3,
    },
}
