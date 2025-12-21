<template>
  <el-card class="market-mini-card" shadow="hover" :body-style="{ padding: '15px' }">
    <!-- 市场问题 -->
    <div class="market-header mb-3">
      <h4 class="market-question">{{ market.question }}</h4>
      <div class="market-badges ml-2">
        <el-tag :type="market.active ? 'success' : 'info'" size="small" effect="dark">
          {{ market.active ? '活跃' : '已关闭' }}
        </el-tag>
      </div>
    </div>

    <!-- 选项和价格 -->
    <div v-if="parsedOutcomes && parsedOutcomes.length > 0" class="outcomes-section mb-3">
      <div
        v-for="(outcome, index) in parsedOutcomes"
        :key="index"
        class="outcome-row"
      >
        <span class="outcome-name text-truncate">{{ outcome }}</span>
        <span class="outcome-price">
          {{ parsedPrices && parsedPrices[index] ? '$' + parsedPrices[index] : '-' }}
        </span>
      </div>
    </div>

    <!-- 市场统计 -->
    <div class="market-stats mb-2">
      <el-space spacer="|" class="w-100">
        <div v-if="market.volume" class="stat-item">
          <el-icon><Money /></el-icon>
          <span class="stat-label ml-1">交易量:</span>
          <span class="stat-value ml-1">${{ formatNumber(market.volume) }}</span>
        </div>
        <div v-if="market.liquidity" class="stat-item">
          <el-icon><WaterRate /></el-icon>
          <span class="stat-label ml-1">流动性:</span>
          <span class="stat-value ml-1">${{ formatNumber(market.liquidity) }}</span>
        </div>
      </el-space>
    </div>

    <!-- 市场ID -->
    <div class="market-id text-secondary">
      <span class="id-label">ID:</span>
      <el-tooltip :content="market.id" placement="top">
        <span class="id-value ml-1 text-truncate" style="max-width: 150px; display: inline-block; vertical-align: bottom;">{{ market.id }}</span>
      </el-tooltip>
    </div>
  </el-card>
</template>

<script>
import { Money, Coin as WaterRate } from '@element-plus/icons-vue' // Using Coin as placeholder for liquidity/water if WaterRate doesn't exist, but let's check. Actually 'Money' is good. For Liquidity maybe 'SoldOut' or just 'Coin'. Let's use 'Coin' for Volume and 'Money' for Liquidity or similar.
// Wait, Element Plus icons: Money, Coin, Wallet, etc.
// Let's use Money for Volume, and maybe DataLine or TrendCharts for Liquidity?
// Or just reuse Money and something else.
// I will use `Money` for Volume and `Coin` for Liquidity.

export default {
  name: 'MarketMiniCard',
  components: {
    Money,
    WaterRate: Money // Alias Money to WaterRate for now or just use Money directly
  },
  props: {
    market: {
      type: Object,
      required: true
    }
  },
  computed: {
    // 解析outcomes字符串为数组
    parsedOutcomes() {
      if (!this.market.outcomes) return null
      try {
        if (typeof this.market.outcomes === 'string') {
          return JSON.parse(this.market.outcomes)
        }
        return this.market.outcomes
      } catch (e) {
        return null
      }
    },
    // 解析outcome_prices字符串为数组
    parsedPrices() {
      if (!this.market.outcome_prices && !this.market.outcomePrices) return null
      try {
        const prices = this.market.outcome_prices || this.market.outcomePrices
        if (typeof prices === 'string') {
          return JSON.parse(prices)
        }
        return prices
      } catch (e) {
        return null
      }
    }
  },
  methods: {
    // 格式化数字
    formatNumber(num) {
      if (num === null || num === undefined) return '-'
      try {
        return Number(num).toLocaleString('zh-CN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2
        })
      } catch (e) {
        return num
      }
    }
  }
}
</script>

<style scoped>
.market-mini-card {
  height: 100%;
}

.market-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.market-question {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
  flex: 1;
  line-height: 1.4;
}

.outcome-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 6px;
  background-color: var(--el-fill-color-light);
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.outcome-row:last-child {
  margin-bottom: 0;
}

.outcome-row:hover {
  background-color: var(--el-fill-color);
}

.outcome-name {
  flex: 1;
  font-size: 13px;
  color: var(--el-text-color-regular);
  font-weight: 500;
  margin-right: 10px;
}

.outcome-price {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-color-success);
}

.market-stats {
  padding: 8px 12px;
  background-color: var(--el-fill-color-lighter);
  border-radius: 4px;
}

.stat-item {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.stat-value {
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.market-id {
  font-size: 11px;
  padding-top: 8px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.id-value {
  font-family: monospace;
}

/* Utility classes */
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }
.ml-1 { margin-left: 4px; }
.ml-2 { margin-left: 8px; }
.w-100 { width: 100%; }
.text-secondary { color: var(--el-text-color-secondary); }
.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

