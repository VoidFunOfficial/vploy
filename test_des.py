# 注意：此文件已过时，convert_to_simple_market 函数不存在
# 请使用 convert_gamma_market_to_simple_market 并传入 GammaMarket 对象
from backend.auto_decision import allocate, SimpleMarket
from backend.purse import get_purse

# 示例：直接创建 SimpleMarket 对象
allocate(
    markets_today=[
        SimpleMarket(
            id=1,
            m=0.6,  # YES价格
            p_yes=0.7,  # AI预测的YES概率
            d=30,  # 结算日期（天数索引）
            p_no=0.3  # AI预测的NO概率
        )
    ]
)