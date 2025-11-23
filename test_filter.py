from polymarket_api import *
from backend.filter import *
a = GammaMarketsAPI()
b = a.get_new_events(limit=10)
c = filter_events(b)
print(c)