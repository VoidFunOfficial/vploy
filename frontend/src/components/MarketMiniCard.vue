<template>
  <div class="market-mini-card">
    <!-- 市场问题 -->
    <div class="market-header">
      <h4 class="market-question">{{ market.question }}</h4>
      <div class="market-badges">
        <span v-if="market.active" class="badge badge-success">活跃</span>
        <span v-else class="badge badge-gray">已关闭</span>
      </div>
    </div>

    <!-- 选项和价格 -->
    <div v-if="parsedOutcomes && parsedOutcomes.length > 0" class="outcomes-section">
      <div
        v-for="(outcome, index) in parsedOutcomes"
        :key="index"
        class="outcome-row"
      >
        <span class="outcome-name">{{ outcome }}</span>
        <span class="outcome-price">
          {{ parsedPrices && parsedPrices[index] ? '$' + parsedPrices[index] : '-' }}
        </span>
      </div>
    </div>

    <!-- 市场统计 -->
    <div class="market-stats">
      <div v-if="market.volume" class="stat-item">
        <span class="stat-icon">💰</span>
        <span class="stat-label">交易量:</span>
        <span class="stat-value">${{ formatNumber(market.volume) }}</span>
      </div>
      <div v-if="market.liquidity" class="stat-item">
        <span class="stat-icon">💧</span>
        <span class="stat-label">流动性:</span>
        <span class="stat-value">${{ formatNumber(market.liquidity) }}</span>
      </div>
    </div>

    <!-- 市场ID -->
    <div class="market-id">
      <span class="id-label">ID:</span>
      <span class="id-value">{{ market.id }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MarketMiniCard',
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
  background-color: #fff;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 16px;
  transition: all 0.2s ease;
}

.market-mini-card:hover {
  border-color: #dee2e6;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* 市场头部 */
.market-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f5f5f5;
}

.market-question {
  font-size: 15px;
  font-weight: 600;
  color: #212529;
  margin: 0;
  flex: 1;
  margin-right: 12px;
  line-height: 1.4;
}

.market-badges {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.badge {
  padding: 3px 8px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.badge-success {
  background-color: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}

.badge-gray {
  background-color: #f5f5f5;
  color: #757575;
  border: 1px solid #e0e0e0;
}

/* 选项和价格 */
.outcomes-section {
  margin-bottom: 12px;
}

.outcome-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 6px;
  background-color: #f8f9fa;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.outcome-row:last-child {
  margin-bottom: 0;
}

.outcome-row:hover {
  background-color: #e9ecef;
}

.outcome-name {
  flex: 1;
  font-size: 13px;
  color: #495057;
  font-weight: 500;
}

.outcome-price {
  font-size: 14px;
  font-weight: 600;
  color: #20a53a;
}

/* 市场统计 */
.market-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 10px;
  padding: 10px 12px;
  background-color: #fafafa;
  border-radius: 4px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.stat-icon {
  font-size: 14px;
}

.stat-label {
  color: #6c757d;
}

.stat-value {
  color: #212529;
  font-weight: 600;
}

/* 市场ID */
.market-id {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #6c757d;
  padding-top: 8px;
  border-top: 1px solid #f5f5f5;
}

.id-label {
  font-weight: 500;
}

.id-value {
  font-family: monospace;
  color: #495057;
  word-break: break-all;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .market-mini-card {
    padding: 14px;
  }

  .market-question {
    font-size: 14px;
  }

  .market-stats {
    flex-direction: column;
    gap: 8px;
  }

  .outcome-row {
    padding: 6px 10px;
  }

  .outcome-name {
    font-size: 12px;
  }

  .outcome-price {
    font-size: 13px;
  }
}
</style>

