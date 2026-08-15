from core.gamma_enforcer import GammaTSLEnforcer

def test_long_tsl():
    print("--- TESTING LONG TSL MATH ---")
    enforcer = GammaTSLEnforcer()
    state = {
        "symbol": "BTC_USDT.PERP",
        "direction": "long",
        "entry_price": 100.0,
        "watermark": 100.0,
        "trailing_active": False
    }
    
    # 1. Price drops 3% (No kill)
    kill, reason, state = enforcer.process_tsl_math(state, 97.0)
    assert not kill
    
    # 2. Price drops 6% (Hard Stop kill)
    kill, reason, state = enforcer.process_tsl_math(state, 94.0)
    assert kill and "HARD STOP" in reason
    
    # Reset for trailing test
    state['trailing_active'] = False
    
    # 3. Price pumps 6% (Activates Trailing, Watermark = 106)
    kill, reason, state = enforcer.process_tsl_math(state, 106.0)
    assert state['trailing_active']
    assert state['watermark'] == 106.0
    
    # 4. Price drops 1% to 104.94 (Floor is 106 * 0.98 = 103.88). No kill.
    kill, reason, state = enforcer.process_tsl_math(state, 104.94)
    assert not kill
    
    # 5. Price dumps to 103.00 (Below 103.88 floor). Kill.
    kill, reason, state = enforcer.process_tsl_math(state, 103.0)
    assert kill and "TRAILING STOP" in reason
    print("LONG tests passed.\n")

def test_short_tsl():
    print("--- TESTING SHORT TSL MATH ---")
    enforcer = GammaTSLEnforcer()
    state = {
        "symbol": "ETH_USDT.PERP",
        "direction": "short",
        "entry_price": 100.0,
        "watermark": 100.0,
        "trailing_active": False
    }
    
    # 1. Price pumps 3% (No kill)
    kill, reason, state = enforcer.process_tsl_math(state, 103.0)
    assert not kill
    
    # 2. Price pumps 6% (Hard Stop kill)
    kill, reason, state = enforcer.process_tsl_math(state, 106.0)
    assert kill and "HARD STOP" in reason
    
    # Reset for trailing test
    state['trailing_active'] = False
    
    # 3. Price dumps 6% to 94.0 (Activates Trailing, Watermark = 94.0)
    kill, reason, state = enforcer.process_tsl_math(state, 94.0)
    assert state['trailing_active']
    assert state['watermark'] == 94.0
    
    # 4. Price rises to 95.0 (Floor is 94 * 1.02 = 95.88). No kill.
    kill, reason, state = enforcer.process_tsl_math(state, 95.0)
    assert not kill
    
    # 5. Price pumps to 96.0 (Above 95.88 floor). Kill.
    kill, reason, state = enforcer.process_tsl_math(state, 96.0)
    assert kill and "TRAILING STOP" in reason
    print("SHORT tests passed.")

if __name__ == "__main__":
    test_long_tsl()
    test_short_tsl()
    print("[SUCCESS] All TSL Math Logic Verified.")
