from backend.polymarket_api import GammaMarketsAPI
a = GammaMarketsAPI()
b = a.get_market_by_id( "705811")
print(b)