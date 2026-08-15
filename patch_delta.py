import sys
import re

with open('delta_scalp.py', 'r', encoding='utf-8') as f:
    content = f.read()

parts = content.split('signal = strategy.evaluate(bt)')
if len(parts) == 2:
    p1 = parts[0]
    p2 = parts[1]
    p2_new = re.sub(
        r'if signal is None:.*?continue',
        '''if signal is None:
                bid_size = float(bt.get("bidSize", 0))
                ask_size = float(bt.get("askSize", 0))
                current_imbalance = strategy.compute_imbalance(bid_size, ask_size)
                status_msg = f"Scanning — Imbalance: {current_imbalance:+.2f} (Threshold: ±{strategy.IMBALANCE_THRESHOLD})"
                update_state(ledger, status=status_msg)
                if int(time.time()) % 15 < POLL_SECONDS:
                    print(f"[DELTA SCALP] {status_msg}")
                time.sleep(POLL_SECONDS)
                continue''',
        p2,
        flags=re.DOTALL
    )
    with open('delta_scalp.py', 'w', encoding='utf-8') as f:
        f.write(p1 + 'signal = strategy.evaluate(bt)\n            ' + p2_new)
    print('Patched delta_scalp.py successfully!')
else:
    print('Failed to split!')
