<template>
  <div class="event-card">
    <!-- 卡片头部 -->
    <div class="card-header">
      <div class="header-left">
        <h3 class="event-title">{{ event.title }}</h3>
        <div class="event-meta">
          <span v-if="event.end_date" class="meta-item">
            <span class="meta-icon">⏰</span>
            {{ formatDate(event.end_date) }}
          </span>
        </div>
      </div>
      <div class="event-badges">
        <span v-if="event.active" class="badge badge-success">活跃</span>
        <span v-else class="badge badge-gray">已关闭</span>
        <span v-if="event.negRisk" class="badge badge-warning">负风险</span>
      </div>
    </div>

    <!-- 事件描述 -->
    <div v-if="event.description" class="event-description">
      <div class="description-icon">📋</div>
      <div class="description-text">{{ event.description }}</div>
    </div>

    <!-- 统计数据卡片 -->
    <div class="stats-grid">
      <div v-if="event.volume !== null && event.volume !== undefined" class="stat-card">
        <div class="stat-icon">💰</div>
        <div class="stat-content">
          <div class="stat-label">交易量</div>
          <div class="stat-value">${{ formatNumber(event.volume) }}</div>
        </div>
      </div>
      <div v-if="event.liquidity !== null && event.liquidity !== undefined" class="stat-card">
        <div class="stat-icon">💧</div>
        <div class="stat-content">
          <div class="stat-label">流动性</div>
          <div class="stat-value">${{ formatNumber(event.liquidity) }}</div>
        </div>
      </div>
      <div v-if="event.markets && event.markets.length > 0" class="stat-card">
        <div class="stat-icon">📊</div>
        <div class="stat-content">
          <div class="stat-label">关联市场</div>
          <div class="stat-value">{{ event.markets.length }} 个</div>
        </div>
      </div>
    </div>

    <!-- 事件详细信息 -->
    <div class="event-details">
      <div class="detail-item">
        <span class="detail-label">事件ID</span>
        <span class="detail-value">{{ event.id }}</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">Slug</span>
        <span class="detail-value">{{ event.slug }}</span>
      </div>
      <div v-if="event.start_date" class="detail-item">
        <span class="detail-label">开始时间</span>
        <span class="detail-value">{{ formatDate(event.start_date) }}</span>
      </div>
    </div>

    <!-- 标签 -->
    <div v-if="event.tags && event.tags.length > 0" class="event-tags">
      <div class="section-title">
        <span class="title-icon">🏷️</span>
        <span>标签</span>
      </div>
      <div class="tags-list">
        <span v-for="tag in event.tags" :key="tag.id" class="tag">
          {{ tag.label }}
        </span>
      </div>
    </div>

    <!-- 自定义标记 -->
    <div v-if="event.marks && event.marks.length > 0" class="event-marks">
      <div class="section-title">
        <span class="title-icon">⭐</span>
        <span>标记</span>
      </div>
      <div class="marks-list">
        <span v-for="mark in event.marks" :key="mark" class="mark">
          {{ mark }}
        </span>
      </div>
    </div>

    <!-- 关联市场列表 -->
    <div v-if="event.markets && event.markets.length > 0" class="related-markets">
      <div class="markets-header" @click="toggleMarkets">
        <div class="section-title">
          <span class="title-icon">📈</span>
          <span>关联市场 ({{ event.markets.length }})</span>
        </div>
        <button class="toggle-btn">
          {{ marketsExpanded ? '收起' : '展开' }}
          <span class="arrow">{{ marketsExpanded ? '▲' : '▼' }}</span>
        </button>
      </div>

      <div v-show="marketsExpanded" class="markets-list">
        <div
          v-for="(market, index) in event.markets"
          :key="market.id || index"
          class="market-item"
        >
          <MarketMiniCard :market="market" />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import MarketMiniCard from './MarketMiniCard.vue'

export default {
  name: 'EventCard',
  components: {
    MarketMiniCard
  },
  props: {
    event: {
      type: Object,
      required: true
    }
  },
  setup() {
    // 控制关联市场的展开/收起状态
    const marketsExpanded = ref(false)

    const toggleMarkets = () => {
      marketsExpanded.value = !marketsExpanded.value
    }

    return {
      marketsExpanded,
      toggleMarkets
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
.event-card {
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.2s ease;
}

.event-card:hover {
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

.event-title {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px 0;
  line-height: 1.4;
}

.event-meta {
  display: flex;
  gap: 12px;
  margin-top: 6px;
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

.event-badges {
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

/* 事件描述 */
.event-description {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px;
  background-color: #f8f9fa;
  border-left: 4px solid #20a53a;
  border-radius: 4px;
}

.description-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.description-text {
  flex: 1;
  color: #424242;
  font-size: 14px;
  line-height: 1.6;
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

/* 事件详细信息 */
.event-details {
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

/* 标签 */
.event-tags,
.event-marks {
  margin-bottom: 20px;
}

.tags-list,
.marks-list {
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

/* 关联市场 */
.related-markets {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 2px solid #f5f5f5;
}

.markets-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  padding: 12px 16px;
  background-color: #f8f9fa;
  border-radius: 6px;
  transition: background-color 0.2s ease;
}

.markets-header:hover {
  background-color: #e9ecef;
}

.toggle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background-color: #fff;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  color: #495057;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-btn:hover {
  background-color: #f8f9fa;
  border-color: #adb5bd;
}

.arrow {
  font-size: 10px;
  transition: transform 0.2s ease;
}

.markets-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.market-item {
  padding-left: 16px;
  border-left: 3px solid #e9ecef;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .event-card {
    padding: 16px;
  }

  .card-header {
    flex-direction: column;
    gap: 12px;
  }

  .header-left {
    margin-right: 0;
  }

  .event-title {
    font-size: 18px;
  }

  .event-badges {
    align-self: flex-start;
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

  .markets-header {
    padding: 10px 12px;
  }

  .toggle-btn {
    padding: 5px 10px;
    font-size: 12px;
  }
}

@media (max-width: 480px) {
  .event-card {
    padding: 14px;
  }

  .event-title {
    font-size: 16px;
  }

  .description-text {
    font-size: 13px;
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

