"""KiwoomRestAPI 전체 테스트 스크립트"""
import asyncio
import logging
from decimal import Decimal
from app.trading.external_api.kiwoom import KiwoomRestAPI
from app.common.config import settings

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_all():
    api = KiwoomRestAPI()
    
    print('='*50)
    print('🚀 KiwoomRestAPI 전체 테스트')
    print('='*50)
    
    try:
        # 1. 토큰 발급
        print('\n[1] get_token()')
        token = await api.get_token()
        print(f'    ✅ 토큰: {token[:20]}...')
        
        # 2. 현재가 조회
        print(f'\n[2] get_price("{settings.trading_symbol}")')
        price = await api.get_price(settings.trading_symbol)
        print(f'    ✅ {price.symbol_name}: {price.current_price:,}원 ({price.change_rate}%)')
        
        # 3. 예수금 조회
        print('\n[3] get_balance()')
        balance = await api.get_balance()
        print(f'    ✅ 예수금: {balance.total_deposit:,}원')
        print(f'    ✅ 주문가능: {balance.available_amount:,}원')
        
        # 4. 보유종목 조회
        print('\n[4] get_holdings()')
        holdings = await api.get_holdings()
        print(f'    ✅ 보유종목: {len(holdings)}개')
        for h in holdings[:5]:
            print(f'       - {h.symbol_name}: {h.quantity}주 (수익률: {h.profit_rate}%)')
        
        # 5. 미체결 조회
        print('\n[5] get_pending_orders()')
        orders = await api.get_pending_orders()
        print(f'    ✅ 미체결: {len(orders)}건')
        for o in orders[:5]:
            print(f'       - {o.order_id}: {o.symbol} {o.order_type} {o.quantity}주')
        
        # 6. 매수/매도/취소는 실제 주문이므로 스킵
        print('\n[6] buy() - ⚠️ 실제 주문 발생하므로 테스트 스킵')
        print('[7] sell() - ⚠️ 실제 주문 발생하므로 테스트 스킵')
        print('[8] cancel_order() - ⚠️ 미체결 필요하므로 테스트 스킵')
        
        print('\n' + '='*50)
        print('✅ 전체 테스트 완료!')
        print('='*50)
        
    except Exception as e:
        print(f'\n❌ 에러 발생: {e}')
        import traceback
        traceback.print_exc()
    finally:
        await api.close()

if __name__ == "__main__":
    asyncio.run(test_all())
