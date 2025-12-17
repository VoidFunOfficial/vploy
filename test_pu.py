from backend.polymarket_api.clob_api import get_client, get_orders, get_trades, get_balance_allowance, get_collateral_balance, get_conditional_balance,AssetType

client = get_client()  # 需要配置私钥
print(
    get_balance_allowance(AssetType.CONDITIONAL,token_id="56276805013784365240532397666629746005996536102664929866963805009029990630692")
)