from backend.auto_decision.position_manager import *
from backend.polymarket_api.gamma_markets import GammaMarketsAPI
a=GammaMarketsAPI().get_market_by_slug("will-a-balloon-deflate-during-the-2025-macys-thanksgiving-day-parade")
print(a)
print(convert_to_simple_market(a))
