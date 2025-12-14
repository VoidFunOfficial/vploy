from backend.polymarket_api import *
from backend.filter import *
a = GammaMarketsAPI()
b= a.get_new_events(limit=10)
print(("Up or Down") in str(b[1].tags))