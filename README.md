# 가온전선 DART Financial Agent

[![🔗 대시보드 바로가기](assets/dashboard_badge.svg)](https://hsc-class02.github.io/JY_Gaon/)

> DART(OpenDART)에서 가온전선(000500)의 사업보고서·반기보고서·분기보고서 재무정보를 수집하고, 주요 재무비율을 계산하여 GitHub Pages 대시보드로 공개하는 자동화 프로젝트입니다.

## 🔗 대시보드 바로가기

[![Dashboard](assets/dashboard_badge.svg)](https://hsc-class02.github.io/JY_Gaon/)

### 핵심 기능

- 가온전선 DART 기업 고유번호: `00104768`
- 대상 보고서: 사업보고서(`11011`), 반기보고서(`11012`), 1분기(`11013`), 3분기(`11014`)
- 기본 수집 범위: 2010년부터 현재
- OpenDART 정기보고서 재무정보 API가 제공하는 2015년 이후 자료는 API로 자동 수집
- 2010~2014년은 DART 공시검색 + 공시서류 원본파일 경로를 이용한 legacy 보완 수집 대상으로 분리
- 연결(CFS)을 기본 분석 기준으로 하고, 별도(OFS)도 원자료에 함께 보관할 수 있도록 설계
- 매월 1일 GitHub Actions가 수집·계산·대시보드 생성·Pages 배포
- 수집 원문과 파생 데이터는 GitHub에 버전 관리
- 실패 시 기존 데이터를 덮어쓰지 않도록 atomic write 방식 적용

## 재무분석 범위

첨부된 「재무제표 및 재무비율 실무 가이드」의 지표 체계를 기준으로 다음 항목을 계산합니다.

### 주요 재무수치

총자산, 현금및현금성자산, 매출채권, 재고자산, 유형자산, 총부채, 이자부차입금, 자본총계, 매출액, 매출총이익, 판매비와관리비, 영업이익, 세전이익, 당기순이익, 지배주주순이익, EBITDA(계산 가능 시), 영업활동현금흐름(CFO), 투자활동현금흐름, 재무활동현금흐름, CAPEX, FCF, 순차입금.

### 재무비율

매출총이익률, 영업이익률, 순이익률, EBITDA 마진, ROA, ROE, ROIC, 유동비율, 당좌비율, 부채비율, 자기자본비율, 차입금의존도, 이자보상배율, 순차입금/EBITDA, 총자산회전율, DSO, DIO, DPO, CCC, 매출증가율, CFO/순이익.

> PER/PBR/EV/EBITDA는 주가·시가총액 데이터가 별도로 필요합니다. 현재 기본 agent는 DART 재무자료와 분리하여 설계했으며, 시장데이터 소스를 추가하면 확장할 수 있습니다.

## GitHub 설정

### 1. DART API 키

OpenDART에서 발급받은 인증키를 GitHub repository secret으로 등록합니다.

- Secret 이름: `DART_API_KEY`
- 값: 40자리 OpenDART API 인증키

GitHub:
`Settings → Secrets and variables → Actions → New repository secret`

**API 키를 코드, CSV, README 또는 workflow에 직접 입력하지 마세요.**

### 2. GitHub Pages

`Settings → Pages → Build and deployment → Source → GitHub Actions`로 설정합니다.

workflow가 `actions/configure-pages`, `actions/upload-pages-artifact`, `actions/deploy-pages`를 사용하도록 구성되어 있습니다.

### 3. 매월 자동 업데이트

`.github/workflows/update.yml`에 다음 스케줄이 설정되어 있습니다.

- 매월 1일
- `Asia/Seoul` 기준 새벽 3시
- 수동 실행(`workflow_dispatch`)도 가능

### 4. 최초 실행

1. `DART_API_KEY` 등록
2. Actions에서 `DART Financial Update` 실행
3. 성공하면 `data/`와 `dashboard/`가 갱신되고 GitHub Pages가 배포됩니다.

## Peer firms

전선 제조업의 국내 비교기업 후보를 아래와 같이 정리했습니다. 대시보드와 README 하단에서 함께 확인할 수 있습니다.

| Peer firm | Ticker | Note |
|---|---:|---|
| LS전선 | 비상장 | 전력·산업용 전선 |
| 대한전선 | 001440 | 전력·산업용 전선 |
| 일진전기 | 103590 | 전선 및 전력기기 |
| LS에코에너지 | 229640 | 전선·케이블 |
| 대원전선 | 006340 | 전선 제조 |
| KBI메탈 | 024840 | 전선/전장 관련 사업 |

> Peer는 동일 산업분류와 국내 상장 전선업 비교에 활용하기 위한 후보군입니다. 동등한 사업범위라는 의미는 아닙니다.

## 프로젝트 구조

```text
app/
  dart_client.py          # OpenDART API client
  financial_mapping.py    # 계정과목 mapping
  ratios.py               # 재무비율 계산
  pipeline.py             # 수집→정규화→계산→저장
scripts/
  run_pipeline.py
  build_dashboard.py
data/
  annual.csv
  half_year.csv
  quarterly.csv
reports/
  metadata/
  raw/
dashboard/
  index.html
assets/
  dashboard_badge.svg
.github/
  workflows/
    update.yml
```

## 데이터 기준

재무상태표는 시점 자료, 손익계산서와 현금흐름표는 기간 자료로 구분하고, ROA/ROE/회전율처럼 기간과 시점을 결합하는 비율은 평균 자산·평균 자본을 사용하도록 설계했습니다. 연결과 별도 기준을 섞지 않으며, 일회성 항목은 원자료에 남겨 후속 검토가 가능하도록 합니다.

이 원칙은 첨부된 실무 가이드의 분석 순서와 정의를 따릅니다.
