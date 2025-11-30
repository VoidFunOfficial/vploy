from backend.polymarket_api import *
from backend.filter import *
a = GammaMarketsAPI()
b = a.get_better_events(limit=10)
c = filter_events(b)