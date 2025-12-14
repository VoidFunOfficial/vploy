from backend.auto_trade import *
from backend.polymarket_api import *

c = scan_orderbook("34551606549875928972193520396544368029176529083448203019529657908155427866742", "BUY", 9999)
print(c)