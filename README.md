# 🚀 무한매수법 자동매매 시스템

라오어 무한매수법 전략을 기반으로 한 국내 주식 자동매매 시스템입니다.  
키움 REST API를 사용하여 실시간으로 매수/매도 주문을 실행합니다.

## 📋 주요 기능

| 기능 | 설명 |
|------|------|
| **자동 분할 매수** | 현재가 기준 40분할 매수 |
| **목표가 매도** | 평단가 +10% 도달 시 자동 매도 |
| **미체결 관리** | 미체결 주문 조회 및 취소 |
| **텔레그램 알림** | 주문 체결/에러 알림 발송 |

## 🛠 기술 스택

- **Python 3.11+**
- **키움 REST API**
- **APScheduler** (스케줄러)
- **PostgreSQL** (포지션/주문 기록)
- **Docker Compose**

## 📁 프로젝트 구조

```
kang_stock/
├── app/
│   ├── common/             # 공통 모듈 (설정, 유틸, DB)
│   ├── trading/
│   │   ├── external_api/   # 키움 API 클라이언트
│   │   │   ├── base.py     # 추상 인터페이스
│   │   │   ├── kiwoom.py   # 키움 REST API 구현
│   │   │   └── mock.py     # 테스트용 Mock
│   │   ├── models/         # DB 모델 (Position, Order)
│   │   ├── repository/     # 데이터 접근 계층
│   │   ├── services/       # 비즈니스 로직
│   │   │   ├── trading.py  # 매매 서비스
│   │   │   └── scheduler.py # 스케줄러
│   │   └── strategy/       # 무한매수법 전략
│   └── notifications/      # 텔레그램 알림
│       ├── telegram.py     # 알림 서비스
│       └── decorators.py   # 알림 데코레이터
├── alembic/                # DB 마이그레이션
├── tests/                  # 테스트
├── main.py                 # 진입점
├── docker-compose.yml
└── pyproject.toml
```

## ⚙️ 설치 및 실행

### 0. 키움 REST API 키 발급 (필수)

1. [키움 Open API](https://openapi.koreainvestment.com/) 접속
2. 회원가입 및 로그인
3. **마이페이지 → API 키 발급** 메뉴에서 앱 등록
4. **APP KEY**와 **APP SECRET** 발급
5. **계좌번호** 확인

> ⚠️ 실전투자와 모의투자 API 키가 다릅니다. 모의투자로 먼저 테스트 권장!

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일 편집
```

```env
# 키움 REST API
KIWOOM_APP_KEY=your_app_key
KIWOOM_APP_SECRET=your_app_secret
KIWOOM_ACCOUNT_NO=your_account_no
KIWOOM_IS_MOCK=false

# 데이터베이스
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/kang_stock

# 텔레그램
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 트레이딩 설정
TRADING_SYMBOL=379800          # 투자할 종목코드
TOTAL_INVESTMENT=10000000      # 총 투자금
NUM_SPLITS=40                  # 분할 횟수
PROFIT_TARGET=1.10             # 목표 수익률 (+10%)
```

### 2. 의존성 설치

```bash
# uv 사용 (권장)
uv sync

# 또는 pip
pip install -e .
```

### 3. Docker (PostgreSQL)

```bash
docker-compose up -d
```

### 4. DB 마이그레이션

```bash
uv run alembic upgrade head
```

### 5. 실행

```bash
uv run python main.py
```

## 📊 API 테스트

```bash
# 전체 API 테스트
uv run python test_api.py
```

### 개별 API 테스트

```python
import asyncio
from app.trading.external_api.kiwoom import KiwoomRestAPI

async def test():
    api = KiwoomRestAPI()
    
    # 현재가 조회
    price = await api.get_price("379800")
    print(f"현재가: {price.current_price:,}원")
    
    # 잔고 조회
    balance = await api.get_balance()
    print(f"주문가능: {balance.available_amount:,}원")
    
    # 보유종목
    holdings = await api.get_holdings()
    for h in holdings:
        print(f"{h.symbol_name}: {h.quantity}주")
    
    # 매수 주문 (1주)
    result = await api.buy("379800", 1, price.current_price)
    print(f"주문번호: {result.order_id}")
    
    await api.close()

asyncio.run(test())
```

## 📈 매매 전략

### 무한매수법 (Infinite Buy Strategy)

| 단계 | 동작 |
|------|------|
| **매수** | 매일 현재가 기준 1회분(총 투자금/40) 수량 계산 → 현재가로 지정가 매수 |
| **매도** | 평단가 × 1.10 (+10%) 도달 시 전량 매도 |
| **40회 소진** | 1/4 손절 후 재매수 또는 대기 |

### 스케줄

| 시간 | 동작 |
|------|------|
| **09:00** | 매도 주문 설정 (목표가) |
| **14:30** | 매수 주문 실행 (1회분) |
| **15:40** | 체결 확인 및 포지션 업데이트 |

## 🔑 키움 REST API

| API ID | 용도 | 엔드포인트 |
|--------|------|-----------|
| `kt00001` | 예수금 조회 | `/api/dostk/acnt` |
| `kt00018` | 보유종목 조회 | `/api/dostk/acnt` |
| `ka10075` | 미체결 조회 | `/api/dostk/acnt` |
| `ka10001` | 현재가 조회 | `/api/dostk/stkinfo` |
| `kt10000` | 매수 주문 | `/api/dostk/ordr` |
| `kt10001` | 매도 주문 | `/api/dostk/ordr` |
| `kt10003` | 취소 주문 | `/api/dostk/ordr` |

## 🔔 알림 시스템

데코레이터 패턴으로 알림 분리:

```python
from app.notifications.decorators import notify_on_buy, notify_on_sell

@notify_on_buy
async def execute_daily_buy_order(self) -> Order | None:
    # 주문 성공 시 자동으로 텔레그램 알림 발송
    ...
    return order
```

### 알림 종류
- 📥 매수 주문
- 📤 매도 주문
- ✅ 체결 완료
- ⚠️ 긴급 매도
- 🎉 사이클 완료
- 🚨 에러 발생

## ⚠️ 주의사항

- **실전 투자 시 손실 위험**이 있습니다.
- 장 시간(09:00-15:30)에만 주문이 체결됩니다.
- `KIWOOM_IS_MOCK=true`로 설정하면 모의투자 서버를 사용합니다.

## 📄 라이선스

MIT License
