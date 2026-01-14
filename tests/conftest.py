"""테스트 설정"""

import pytest


@pytest.fixture
def sample_position_data():
    """테스트용 포지션 데이터"""
    return {
        "symbol": "133690",
        "symbol_name": "TIGER미국나스닥100",
        "quantity": 10,
        "avg_price": 160000,
        "splits_used": 5,
        "cycle_count": 1,
        "current_investment": 10000000,
        "initial_investment": 10000000,
    }
