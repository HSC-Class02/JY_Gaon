# DART API / GitHub 설정 가이드

## 1. OpenDART API 키 발급

1. https://opendart.fss.or.kr/ 접속
2. 회원가입/로그인
3. 인증키 발급
4. 40자리 인증키를 복사

## 2. GitHub Secret 등록

Repository:
`HSC-Class02/JY_Gaon`

경로:

`Settings → Secrets and variables → Actions → New repository secret`

입력:

- Name: `DART_API_KEY`
- Secret: 발급받은 40자리 DART 인증키

**중요:** README, Python 파일, workflow 파일, CSV 등에 키를 직접 입력하지 않습니다.

## 3. 최초 실행

`Actions → DART Financial Update → Run workflow`

성공하면 다음이 생성/갱신됩니다.

- `reports/raw/` : DART 공시 원본 ZIP
- `reports/metadata/` : API 응답 및 보고서 메타데이터
- `data/annual.csv`
- `data/half_year.csv`
- `data/quarterly.csv`
- `data/raw_periods.csv`
- `dashboard/index.html`

## 4. 자동 업데이트

`.github/workflows/update.yml`에 다음 cron이 설정되어 있습니다.

```text
0 18 1 * *
```

GitHub Actions의 cron은 UTC 기준이므로 한국시간으로 매월 1일 오전 3시입니다.

또한 수동 실행도 가능합니다.

## 5. GitHub Pages

`Settings → Pages → Build and deployment → Source → GitHub Actions`

workflow가 Pages artifact를 생성하고 배포합니다.

기본 URL:

`https://hsc-class02.github.io/JY_Gaon/`

## 6. About 링크

저장소 메인 화면의 `About`에서 Website/Homepage URL에 위 Pages 주소를 입력합니다.

권장 표시:

`📊 Financial Dashboard`

## 7. API 사용 범위

OpenDART 정기보고서 재무정보 API:

- 사업보고서: `11011`
- 반기보고서: `11012`
- 1분기보고서: `11013`
- 3분기보고서: `11014`

가온전선:

- 종목코드: `000500`
- DART 고유번호: `00104768`

OpenDART의 XBRL 재무정보 API는 2015년 이후 재무정보를 제공하므로, 2010~2014년은 `공시검색 → 공시서류원본파일(document.xml)`을 통해 원본 ZIP을 보관하고 legacy parser를 별도로 적용합니다.

legacy 결과는 자동으로 `data/legacy_2010_2014.csv`에 분리 저장되며, XBRL 데이터와 섞이지 않습니다.
