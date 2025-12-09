from backend.polymarket_api import GammaMarketsAPI
a = GammaMarketsAPI()
b = a.get_market_outcomes_and_prices( "705811")
print(b)