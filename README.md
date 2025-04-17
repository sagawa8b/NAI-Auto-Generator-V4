# NAI-Auto-Generator V4
Novel AI의 이미지 생성을 자동으로 생성 할 수 있도록 하게 구현한 윈도우 어플리케이션.


버전업 히스토리

version 1.5.3.20

- 버그 투성이 릴리즈



version 1.5.3.21

- 장시간 사용 시 안정성 향상

- 시나리오별 프롬프트 생성을 위한 순차적 와일드카드 적용

- 폴더 지정시 다운되는 문제 해결



version 1.5.3.23

- 세션 관리 시스템 개선: 통합된 NAISessionManager 클래스 추가로 세션 안정성 향상

- 토큰 갱신 로직 최적화: 불필요한 재인증 감소로 계정 보안 강화 및 서버 부하 감소

- 이미지 생성 추적: 세션당 최대 이미지(450개) 도달 시 자동 토큰 갱신

- 연결 복구 메커니즘: 네트워크 중단 감지 및 자동 복구 기능 추가



version 1.5.3.25

- 세션 관리 시스템 대규모 개선

- Anlas 표시 복구 

- 세션 만료 시 불필요한 로그인 요청 반복 문제 해결

- 연속 생성 중 세션 오류로 인한 작업 중단 개선

- 각 세션의 이미지 생성 한계와 지속 시간 자동 학습



version 1.5.3.26

- 메타데이터 표시 개선

- Advanced 설정 UI 업데이트

- "bytes-like object is required, not tuple" 오류 수정

- Legacy Prompt Conditioning Mode 기능 신설



version 1.5.3.27/28

- 시스템 로그 기능 추가 및 업데이트

- 랜덤 프롬프트 체크 해제 해도 기억하도록 수정

- 인터넷 연결이 끊어졌을때 내부적으로 에러 처리되는 로직 개선

- Numeric Emphasis 가중치 하이라이트 기능 추가

- 태그 자동완성 기능 이슈 해결



version 1.5.4.02

- 자동생성에 아이콘 버튼 추가 (20/30/50/100)



version 1.5.4.03

- 샘플러 업데이트



version 1.5.4.15

- 설정 파일 저장/불러오기 개선

- 세팅별 연속 생성 수정

- 이미지 메타 데이터 처리 개선


# 주의사항
자동 생성의 과도한 사용시 밴을 당할 수 있습니다. 주의하세요.
가능한 자동 생성버튼을 눌렀을 때 나오는 '지연 시간'을 설정하길 추천합니다.
해당 프로그램을 사용함으로써 발생하는 책임은 모두 사용자에게 있습니다.


# 크레딧
원작자
https://github.com/DCP-arca/NAI-Auto-Generator/


참고
https://github.com/neggles/sd-webui-stealth-pnginfo/

https://huggingface.co/baqu2213/

https://github.com/pythongosssss/ComfyUI-WD14-Tagger/

https://huggingface.co/SmilingWolf
