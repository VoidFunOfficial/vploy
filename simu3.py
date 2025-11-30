import numpy as np
import matplotlib.pyplot as plt

rng = np.random.default_rng(232)

def kelly_fraction_yes(p, m):
    """
    全 Kelly 仓位：买 YES，价格 m，真实概率 p。
    返回的是：下注占总财富的比例 z*。
    """
    if m >= 1.0:
        return 0.0
    denom = 1.0 - m
    if denom <= 0:
        return 0.0
    z = (p - m) / denom
    return max(0.0, z)  # 只取正的

def kelly_fraction_no(p, m):
    """
    全 Kelly 仓位：做 NO，YES 价格 m，真实 YES 概率 p。
    NO 价格为 (1-m)，真实 NO 概率为 (1-p)。
    """
    if m <= 0.0:
        return 0.0
    z = (m - p) / m
    return max(0.0, z)


def simulate_once(
    T=200,
    markets_per_period=8,
    max_lock_periods=10,
    k=0.5,              # 最大锁仓比例
    theta=0.5,          # 分数 Kelly 系数
    sigma_misprice=0.1, # 价格相对我们预测的偏差
    slip_max=0.01       # 最大滑点（线性成本）
):
    """
    返回整条财富路径：np.array 长度 T+1（含初始点）。
    """
    wealth = 1.0
    wealth_path = [wealth]
    
    # 未结算仓位
    # 每个仓位: {side, price, stake, shares, settle_t, slip, p_hat}
    open_positions = []
    
    for t in range(T):
        # 1) 结算到期仓位
        new_open = []
        for pos in open_positions:
            if pos["settle_t"] == t:
                # 真正的概率围绕 p_hat 浮动 +/-50%
                p_hat = pos["p_hat"]
                q = np.clip(p_hat * (1.0 + rng.uniform(-0.5, 0.5)), 0.01, 0.99)
                outcome_yes = rng.random() < q
                
                if pos["side"] == "yes":
                    # 买 YES：若发生事件，拿到 shares * 1；否则 0
                    payoff = pos["shares"] * 1.0 if outcome_yes else 0.0
                else:
                    # 做 NO：若事件不发生，拿到 shares * 1；否则 0
                    payoff = pos["shares"] * 1.0 if not outcome_yes else 0.0
                
                cost = pos["stake"] * (1.0 + pos["slip"])  # 含滑点的实际成本
                wealth += payoff - cost
            else:
                new_open.append(pos)
        open_positions = new_open
        
        # 破产保护
        if wealth <= 0:
            wealth_path.extend([0.0] * (T - t))
            break
        
        # 2) 计算当前锁仓和剩余锁仓空间
        total_locked = sum(p["stake"] * (1.0 + p["slip"]) for p in open_positions)
        max_locked = k * wealth
        remaining_capacity = max(0.0, max_locked - total_locked)
        
        # 3) 生成新市场 & 计算计划下注
        if remaining_capacity > 0:
            n = markets_per_period
            stakes_planned = []
            markets = []
            
            for _ in range(n):
                # 我们自己的预测
                p_hat = rng.uniform(0.05, 0.95)
                # 市场价格 = 我们预测 + 噪声
                mis = rng.normal(0.0, sigma_misprice)
                m = np.clip(p_hat + mis, 0.01, 0.99)
                # 随机滑点
                slip = rng.uniform(0.0, slip_max)
                # 随机锁仓期
                lock_len = rng.integers(1, max_lock_periods + 1)
                settle_t = int(min(T-1, t + lock_len))
                
                # 计算 YES / NO 的 edge
                edge_yes = p_hat - m
                edge_no = m - p_hat  # = (1-p_hat) - (1-m)
                
                if edge_yes <= 0 and edge_no <= 0:
                    continue  # 无 edge，不下
                
                if edge_yes >= edge_no:
                    side = "yes"
                    f_kelly = kelly_fraction_yes(p_hat, m)
                else:
                    side = "no"
                    f_kelly = kelly_fraction_no(p_hat, m)
                
                if f_kelly <= 0:
                    continue
                
                # 分数 Kelly
                f = theta * f_kelly
                stake = f * wealth   # 计划下注金额
                if stake <= 0:
                    continue
                
                markets.append((p_hat, m, slip, settle_t, side, stake))
                stakes_planned.append(stake * (1.0 + slip))
            
            # 4) 根据锁仓约束缩放
            if stakes_planned:
                total_planned = sum(stakes_planned)
                scale = 1.0
                if total_planned > remaining_capacity and total_planned > 0:
                    scale = remaining_capacity / total_planned
                
                for (p_hat, m, slip, settle_t, side, stake) in markets:
                    actual_stake = stake * scale
                    if actual_stake <= 0:
                        continue
                    price = m if side == "yes" else (1.0 - m)
                    shares = actual_stake / price
                    open_positions.append(
                        dict(
                            side=side,
                            price=price,
                            stake=actual_stake,
                            shares=shares,
                            settle_t=settle_t,
                            slip=slip,
                            p_hat=p_hat,
                        )
                    )
        
        wealth_path.append(wealth)
    
    return np.array(wealth_path)


def estimate_log_growth(theta, runs=50, **kwargs):
    """
    用 Monte Carlo 估计给定 theta 的 E[log(W_T)]。
    """
    logs = []
    for _ in range(runs):
        path = simulate_once(theta=theta, **kwargs)
        logs.append(np.log(path[-1] + 1e-12))
    return float(np.mean(logs))


if __name__ == "__main__":
    # 1. 搜索最优 theta
    thetas = np.linspace(0.1, 1.2, 12)
    growths = [estimate_log_growth(theta, runs=50) for theta in thetas]
    best_idx = int(np.argmax(growths))
    best_theta = float(thetas[best_idx])
    print("theta grid:", thetas)
    print("log-growth:", growths)
    print("best theta:", best_theta)
    
    # 2. 用最优 theta 跑一条长路径
    path = simulate_once(theta=best_theta, T=300)
    print("final wealth:", path[-1])
    
    # 3. 画 profit / wealth 曲线
    plt.figure()
    plt.plot(path)
    plt.xlabel("Period")
    plt.ylabel("Wealth")
    plt.title(f"Sample Wealth Path (theta={best_theta:.2f})")
    plt.tight_layout()
    plt.show()
