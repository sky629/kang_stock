"""키움 REST API 클라이언트"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

import httpx

from app.common.config import settings
from app.common.utils import get_kst_now
from app.trading.external_api.base import (
    BalanceInfo,
    HoldingInfo,
    OrderResult,
    PriceInfo,
    StockAPIBase,
)

logger = logging.getLogger(__name__)


class KiwoomAPIError(Exception):
    """키움 API 에러"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class KiwoomRestAPI(StockAPIBase):
    """키움 REST API 클라이언트 구현"""

    def __init__(self):
        self.base_url = settings.kiwoom_base_url
        self.app_key = settings.kiwoom_app_key
        self.app_secret = settings.kiwoom_app_secret
        self.account_no = settings.kiwoom_account_no

        self._token: str | None = None
        self._token_expires_at: datetime | None = None

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
        )

    async def close(self):
        """클라이언트 종료"""
        await self._client.aclose()

    async def _ensure_token(self) -> str:
        """토큰 유효성 확인 및 갱신"""
        now = get_kst_now()

        # 토큰이 없거나 만료 1시간 전이면 갱신
        if (
            self._token is None
            or self._token_expires_at is None
            or now >= self._token_expires_at - timedelta(hours=1)
        ):
            self._token = await self.get_token()

        return self._token

    async def get_token(self) -> str:
        """인증 토큰 발급"""
        response = await self._client.post(
            "/oauth2/token",
            json={
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "secretkey": self.app_secret,
            },
            headers={"Content-Type": "application/json"},
        )

        data = response.json()

        if response.status_code != 200:
            raise KiwoomAPIError(
                code=data.get("error_code", "UNKNOWN"),
                message=data.get("error_description", "토큰 발급 실패"),
            )

        self._token = data["token"]
        # 토큰은 24시간 유효
        self._token_expires_at = get_kst_now() + timedelta(hours=24)

        logger.info("키움 API 토큰 발급 완료")
        return self._token

    async def _request(
        self,
        method: str,
        endpoint: str,
        api_id: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict:
        """API 요청 공통 메서드"""
        token = await self._ensure_token()

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Authorization": f"Bearer {token}",
            "api-id": api_id,
        }

        # 키움 REST API는 대부분 POST + Body 파라미터 사용
        # 문서상 Method: POST, Body parameters
        response = await self._client.post(endpoint, headers=headers, json=params or json_data)

        data = response.json()
        
        # 에러 체크 (return_code != 0 이면 에러)
        if data.get("return_code") and data["return_code"] != 0:
            raise KiwoomAPIError(
                code=str(data.get("return_code", "UNKNOWN")),
                message=data.get("return_msg", "알 수 없는 오류"),
            )

        return data

    async def get_price(self, symbol: str) -> PriceInfo:
        """현재가 조회 (주식기본정보)"""
        # ka10001: 주식기본정보요청 (POST)
        data = await self._request(
            method="POST",
            endpoint="/api/dostk/stkinfo",
            api_id="ka10001",
            params={"stk_cd": symbol},
        )

        # 응답 필드 (output 래퍼 없음)
        # cur_prc: 현재가 (예: "+25525")
        # base_pric: 기준가/전일종가 (예: "25275")
        # flu_rt: 등락률 (예: "+0.99")
        
        current_price = data.get("cur_prc", "0").replace(",", "").lstrip("+-")
        base_price = data.get("base_pric", "0").replace(",", "").lstrip("+-")
        change_rate = data.get("flu_rt", "0").replace(",", "").lstrip("+-")

        return PriceInfo(
            symbol=symbol,
            symbol_name=data.get("stk_nm", ""),
            current_price=Decimal(current_price or "0"),
            prev_close=Decimal(base_price or "0"),
            change_rate=Decimal(change_rate or "0"),
        )

    async def get_balance(self) -> BalanceInfo:
        """계좌 잔고 조회"""
        # kt00001: 예수금상세현황요청
        data = await self._request(
            method="POST",
            endpoint="/api/dostk/acnt",
            api_id="kt00001",
            params={"qry_tp": "2"}, # 일반조회
        )
        
        # 디버깅: 응답 필드 확인용 로그
        logger.info(f"Balance (kt00001) Body: {data}")

        output = data.get("output", data)
        if isinstance(output, list) and output:
             output = output[0]

        return BalanceInfo(
            total_deposit=Decimal(output.get("entr", "0")),
            available_amount=Decimal(output.get("ord_alow_amt", "0")),
        )

    async def get_holdings(self) -> list[HoldingInfo]:
        """보유 종목 조회"""
        # kt00018: 계좌평가잔고내역요청
        data = await self._request(
            method="POST",
            endpoint="/api/dostk/acnt",
            api_id="kt00018",
            params={
                "qry_tp": "2",  # 개별조회
                "dmst_stex_tp": "KRX",  # 한국거래소
            },
        )
        
        # 디버깅
        logger.info(f"Holdings (kt00018) Output Keys: {data.keys()}")

        # 보유종목 리스트: acnt_evlt_remn_indv_tot
        output_list = data.get("acnt_evlt_remn_indv_tot", [])

        holdings = []
        for item in output_list:
            holdings.append(
                HoldingInfo(
                    symbol=item.get("stk_cd", ""),
                    symbol_name=item.get("stk_nm", ""),
                    quantity=int(item.get("rmnd_qty", "0")),
                    avg_price=Decimal(item.get("pur_pric", "0")),
                    current_price=Decimal(item.get("cur_prc", "0")),
                    profit_rate=Decimal(item.get("prft_rt", "0")),
                )
            )

        return holdings

    async def buy(self, symbol: str, quantity: int, price: Decimal) -> OrderResult:
        """지정가 매수 주문 (현재가 기준)"""
        # kt10000: 주식매수주문
        data = await self._request(
            method="POST",
            endpoint="/api/dostk/ordr",
            api_id="kt10000",
            json_data={
                "dmst_stex_tp": "KRX",  # 한국거래소
                "stk_cd": symbol,
                "ord_qty": str(quantity),
                "ord_uv": str(int(price)),  # 현재가
                "trde_tp": "0",  # 지정가
            },
        )

        logger.info(f"Buy order response: {data}")
        
        ord_no = data.get("ord_no")
        if not ord_no:
            raise KiwoomAPIError(
                code=str(data.get("return_code", "NO_ORD_NO")),
                message=data.get("return_msg", "주문번호가 없습니다"),
            )

        return OrderResult(
            order_id=ord_no,
            symbol=symbol,
            order_type="BUY",
            quantity=quantity,
            price=price,
            status="PENDING",
        )

    async def sell(self, symbol: str, quantity: int, price: Decimal) -> OrderResult:
        """지정가 매도 주문 (현재가 기준)"""
        # kt10001: 주식매도주문
        data = await self._request(
            method="POST",
            endpoint="/api/dostk/ordr",
            api_id="kt10001",
            json_data={
                "dmst_stex_tp": "KRX",  # 한국거래소
                "stk_cd": symbol,
                "ord_qty": str(quantity),
                "ord_uv": str(int(price)),  # 현재가
                "trde_tp": "0",  # 지정가
            },
        )

        logger.info(f"Sell order response: {data}")
        
        ord_no = data.get("ord_no")
        if not ord_no:
            raise KiwoomAPIError(
                code=str(data.get("return_code", "NO_ORD_NO")),
                message=data.get("return_msg", "주문번호가 없습니다"),
            )

        return OrderResult(
            order_id=ord_no,
            symbol=symbol,
            order_type="SELL",
            quantity=quantity,
            price=price,
            status="PENDING",
        )

    async def get_pending_orders(self) -> list[OrderResult]:
        """미체결 주문 조회"""
        # ka10075: 미체결요청
        data = await self._request(
            method="POST",
            endpoint="/api/dostk/acnt",
            api_id="ka10075",
            params={
                "all_stk_tp": "0",  # 전체종목
                "trde_tp": "0",     # 전체(매수+매도)
                "stex_tp": "1",     # KRX
            },
        )

        logger.info(f"Pending orders (ka10075) response keys: {data.keys()}")

        orders = []
        for item in data.get("oso", []):
            # trde_tp: 1=매도, 2=매수
            order_type = "BUY" if item.get("trde_tp") == "2" else "SELL"
            orders.append(
                OrderResult(
                    order_id=item.get("ord_no", ""),
                    symbol=item.get("stk_cd", ""),
                    order_type=order_type,
                    quantity=int(item.get("oso_qty", "0")),  # 미체결수량
                    price=Decimal(item.get("ord_pric", "0")),
                    status="PENDING",
                )
            )

        return orders

    async def cancel_order(self, order_id: str, symbol: str = "", quantity: int = 0) -> bool:
        """주문 취소
        
        Args:
            order_id: 원주문번호
            symbol: 종목코드 (필수)
            quantity: 취소수량 (0 = 전량 취소)
        """
        try:
            # kt10003: 주식취소주문
            data = await self._request(
                method="POST",
                endpoint="/api/dostk/ordr",
                api_id="kt10003",
                json_data={
                    "dmst_stex_tp": "KRX",  # 한국거래소
                    "orig_ord_no": order_id,  # 원주문번호
                    "stk_cd": symbol,  # 종목코드
                    "cncl_qty": str(quantity),  # 취소수량 (0=전량)
                },
            )
            
            logger.info(f"Cancel order response: {data}")
            
            # 성공 확인 (ord_no가 있으면 성공)
            if data.get("ord_no"):
                return True
            return False
            
        except KiwoomAPIError as e:
            logger.warning(f"주문 취소 실패: {e}")
            return False

