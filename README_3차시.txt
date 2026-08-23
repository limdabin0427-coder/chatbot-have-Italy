[3차시] Luca Visits Our School - Do you have ~?

1. 대화 흐름
로그인 → 개인화 인사 → 학생 인사 → 기분 대화 → 루카의 질문
→ 학생 응답 → 학생 질문 2회 → 선택 질문 1회 → 이탈리아 초대 → 자동 종료

2. 구글 시트
- 파일: vibecoding-chatbot-Do you have
- 탭: Italy
- 연결 ID는 config.py의 SPREADSHEET_ID에 입력되어 있습니다.
- 배포 환경에는 기존과 동일한 GOOGLE_SERVICE_ACCOUNT 값을 설정해야 합니다.

3. OpenAI 생성형 AI
- 모델: gpt-4o-mini
- 배포 환경에 OPENAI_API_KEY를 설정해야 합니다.
- 정해진 상태 흐름은 백엔드가 관리합니다.
- GPT는 기분 표현, 예상 밖 응답의 의미 이해, 짧은 재진술과 힌트에 사용됩니다.
- GPT 오류가 발생해도 기본 규칙 응답으로 대화가 계속됩니다.

4. 학생 질문용 물품과 루카의 응답
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

5. 화면 자료
- 학교 배경 파일은 ZIP에 포함되어 있지 않습니다.
- GitHub 프로젝트 최상위 폴더에 다음 두 원본 GIF를 별도로 올려야 합니다.
  school background 1.gif
  school background 2.gif
- data/characters.json에는 위 파일명이 이미 연결되어 있습니다.
- 두 배경은 8초 간격으로 전환되며 16초 주기로 반복됩니다.
- 파일명은 띄어쓰기, 숫자, 소문자 확장자까지 정확히 같아야 합니다.

6. 배포
- Build Command: pip install -r requirements.txt
- Start Command: gunicorn app:app
- 환경변수: GOOGLE_SERVICE_ACCOUNT, OPENAI_API_KEY, FLASK_SECRET_KEY
