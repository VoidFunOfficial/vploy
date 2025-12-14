from backend.auto_decision import allocate, SimpleMarket
print(allocate(
    markets_today=[
        SimpleMarket(
            id=1,
            m=0.6,
            p_yes=0.7,
            d=30,
            p_no=0.3
        )
    ]
))