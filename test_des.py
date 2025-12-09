from auto_decision.position_manager import convert_to_simple_market, allocate, get_available_balance
allocate(
    markets=[
        convert_to_simple_market({
            "id": 1,
            "outcome_prices": [0.6, 0.4],
            "end_date": "2025-12-31T00:00:00Z",
            "tau": 30
        })
    ]
)