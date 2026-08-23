[3차시] Luca Visits Our School - Do you have ~?

1. 대화 흐름
로그인 → 개인화 인사 → 학생 인사 → 기분 대화 → 루카의 질문
→ 학생 응답 → 학생 질문 2회 → 선택 질문 1회 → 이탈리아 초대 → 자동 종료

2. 구글 시트
- 파일: vibecoding-chatbot-Do you have
- 탭: Italy
- 연결 ID는 config.py의 SPREADSHEET_ID에 입력되어 있습니다.
- 배포 환경에는 기존과 동일한 GOOGLE_SERVICE_ACCOUNT 값을 설정해야 합니다.

3. 학생 질문용 물품과 루카의 응답
- pencil: No
- ruler: Yes
- eraser: No
- pencil case: Yes
- book: Yes
- notebook: No
- school bag: Yes
- soccer ball: No

물품별 응답은 data/characters.json의 inventory에서 바꿀 수 있습니다.
음성인식 별칭은 data/items.json에서 추가할 수 있습니다.

4. 화면 자료
현재 한국 학교 배경 이미지가 없어 임시 교실색 배경을 사용합니다.
한국 학교 배경 파일을 준비한 뒤 data/characters.json의 backgrounds에
파일명을 추가하면 슬라이드 배경으로 사용할 수 있습니다.

5. 배포
- Build Command: pip install -r requirements.txt
- Start Command: gunicorn app:app
- 환경변수: GOOGLE_SERVICE_ACCOUNT, FLASK_SECRET_KEY
