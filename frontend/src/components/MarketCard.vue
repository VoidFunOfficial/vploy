<template>
  <div class="market-card">
    <!-- 卡片头部 -->
    <div class="card-header">
      <div class="header-left">
        <h3 class="market-question">{{ market.question }}</h3>
        <div class="market-meta">
          <span v-if="market.category" class="meta-item">
            <span class="meta-icon">📁</span>
            {{ market.category }}
          </span>
          <span v-if="market.end_date" class="meta-item">
            <span class="meta-icon">⏰</span>
            {{ formatDate(market.end_date) }}
          </span>
        </div>
      </div>
      <div class="market-badges">
        <span v-if="market.active" class="badge badge-success">活跃</span>
        <span v-else class="badge badge-gray">已关闭</span>
        <span v-if="market.negRisk" class="badge badge-warning">负风险</span>
      </div>
    </div>

    <!-- 选项和价格 -->
    <div v-if="parsedOutcomes && parsedOutcomes.length > 0" class="market-outcomes">
      <div class="section-title">
        <span class="title-icon">📊</span>
        <span>选项和价格</span>
      </div>
      <div class="outcomes-list">
        <div
          v-for="(outcome, index) in parsedOutcomes"
          :key="index"
          class="outcome-item"
        >
          <span class="outcome-name">{{ outcome }}</span>
          <span class="outcome-price">
            {{ parsedPrices && parsedPrices[index] ? '$' + parsedPrices[index] : '-' }}
          </span>
        </div>
      </div>
    </div>

    <!-- 统计数据 -->
    <div class="stats-grid">
      <div v-if="market.volume" class="stat-card">
        <div class="stat-icon">💰</div>
        <div class="stat-content">
          <div class="stat-label">交易量</div>
          <div class="stat-value">${{ formatNumber(market.volume) }}</div>
        </div>
      </div>
      <div v-if="market.liquidity" class="stat-card">
        <div class="stat-icon">💧</div>
        <div class="stat-content">
          <div class="stat-label">流动性</div>
          <div class="stat-value">${{ formatNumber(market.liquidity) }}</div>
        </div>
      </div>
      <div v-if="market.events && market.events.length > 0" class="stat-card">
        <div class="stat-icon">🎯</div>
        <div class="stat-content">
          <div class="stat-label">关联事件</div>
          <div class="stat-value">{{ market.events.length }} 个</div>
        </div>
      </div>
    </div>

    <!-- 市场详细信息 -->
    <div class="market-details">
      <div class="detail-item">
        <span class="detail-label">市场ID</span>
        <span class="detail-value">{{ market.id }}</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">Slug</span>
        <span class="detail-value">{{ market.slug }}</span>
      </div>
      <div v-if="market.closedTime" class="detail-item">
        <span class="detail-label">关闭时间</span>
        <span class="detail-value">{{ formatDate(market.closedTime) }}</span>
      </div>
    </div>

    <!-- 标签 -->
    <div v-if="market.tags && market.tags.length > 0" class="market-tags">
      <div class="section-title">
        <span class="title-icon">🏷️</span>
        <span>标签</span>
      </div>
      <div class="tags-list">
        <span v-for="tag in market.tags" :key="tag.id" class="tag">
          {{ tag.label }}
        </span>
      </div>
    </div>

    <!-- 自定义标记 -->
    <div v-if="market.marks && market.marks.length > 0" class="market-marks">
      <div class="section-title">
        <span class="title-icon">⭐</span>
        <span>标记</span>
      </div>
      <div class="marks-list">
        <span v-for="mark in market.marks" :key="mark" class="mark">
          {{ mark }}
        </span>
      </div>
    </div>

    <!-- CLOB Token IDs -->
    <div v-if="market.clobTokenIds && market.clobTokenIds.length > 0" class="market-tokens">
      <div class="section-title">
        <span class="title-icon">🔑</span>
        <span>CLOB Token IDs</span>
      </div>
      <div class="tokens-list">
        <span v-for="tokenId in market.clobTokenIds" :key="tokenId" class="token-id">
          {{ tokenId }}
        </span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MarketCard',
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
      if (!this.market.outcome_prices) return null
      try {
        if (typeof this.market.outcome_prices === 'string') {
          return JSON.parse(this.market.outcome_prices)
        }
        return this.market.outcome_prices
      } catch (e) {
        return null
      }
    }
  },
  methods: {
    // 格式化日期
    formatDate(dateString) {
      if (!dateString) return '-'
      try {
        const date = new Date(dateString)
        return date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        })
      } catch (e) {
        return dateString
      }
    },
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
.market-card {
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.2s ease;
}

.market-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f5f5f5;
}

.header-left {
  flex: 1;
  margin-right: 15px;
}

.market-question {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px 0;
  line-height: 1.4;
}

.market-meta {
  display: flex;
  gap: 12px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #666;
}

.meta-icon {
  font-size: 14px;
}

.market-badges {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.badge {
  padding: 5px 12px;
  border-radius: 4px;
  font-size: 12px;
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

.badge-warning {
  background-color: #fff3e0;
  color: #e65100;
  border: 1px solid #ffe0b2;
}

/* 通用区块标题 */
.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #424242;
  margin-bottom: 12px;
}

.title-icon {
  font-size: 16px;
}

/* 选项和价格 */
.market-outcomes {
  margin-bottom: 20px;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.outcomes-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.outcome-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background-color: #fff;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.outcome-item:hover {
  border-color: #dee2e6;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.outcome-name {
  flex: 1;
  color: #495057;
  font-size: 14px;
  font-weight: 500;
}

.outcome-price {
  color: #20a53a;
  font-weight: 700;
  font-size: 16px;
}

/* 统计数据卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.stat-card:hover {
  background-color: #e9ecef;
  border-color: #dee2e6;
}

.stat-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 12px;
  color: #6c757d;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #212529;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 市场详细信息 */
.market-details {
  margin-bottom: 20px;
  padding: 16px;
  background-color: #fafafa;
  border-radius: 6px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-label {
  font-size: 13px;
  color: #757575;
  font-weight: 500;
}

.detail-value {
  font-size: 13px;
  color: #424242;
  text-align: right;
  word-break: break-all;
  max-width: 60%;
}

/* 标签、标记、Token IDs */
.market-tags,
.market-marks,
.market-tokens {
  margin-bottom: 20px;
}

.tags-list,
.marks-list,
.tokens-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  padding: 6px 12px;
  background-color: #e3f2fd;
  color: #1565c0;
  border: 1px solid #bbdefb;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.tag:hover {
  background-color: #bbdefb;
}

.mark {
  padding: 6px 12px;
  background-color: #f3e5f5;
  color: #6a1b9a;
  border: 1px solid #e1bee7;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.mark:hover {
  background-color: #e1bee7;
}

.token-id {
  padding: 6px 12px;
  background-color: #fff3e0;
  color: #e65100;
  border: 1px solid #ffe0b2;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  font-family: monospace;
  transition: all 0.2s ease;
}

.token-id:hover {
  background-color: #ffe0b2;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .market-card {
    padding: 16px;
  }

  .card-header {
    flex-direction: column;
    gap: 12px;
  }

  .header-left {
    margin-right: 0;
  }

  .market-question {
    font-size: 18px;
  }

  .market-badges {
    align-self: flex-start;
  }

  .market-outcomes {
    padding: 14px;
  }

  .outcome-item {
    padding: 8px 12px;
  }

  .outcome-name {
    font-size: 13px;
  }

  .outcome-price {
    font-size: 15px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .stat-card {
    padding: 12px 14px;
  }

  .stat-icon {
    font-size: 20px;
  }

  .stat-value {
    font-size: 15px;
  }

  .detail-value {
    max-width: 50%;
  }
}

@media (max-width: 480px) {
  .market-card {
    padding: 14px;
  }

  .market-question {
    font-size: 16px;
  }

  .outcome-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .stat-label {
    font-size: 11px;
  }

  .stat-value {
    font-size: 14px;
  }

  .detail-label,
  .detail-value {
    font-size: 12px;
  }
}
</style>

