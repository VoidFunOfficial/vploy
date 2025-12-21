<template>
  <el-card class="market-card mb-4" shadow="hover">
    <!-- 卡片头部 -->
    <template #header>
      <div class="card-header-content">
        <div class="header-left">
          <h3 class="market-question">{{ market.question }}</h3>
          <div class="market-meta mt-2">
            <el-tag v-if="market.category" type="info" effect="plain" size="small" class="mr-2">
              <el-icon class="mr-1"><Folder /></el-icon>
              {{ market.category }}
            </el-tag>
            <el-tag v-if="market.end_date" type="info" effect="plain" size="small">
              <el-icon class="mr-1"><Timer /></el-icon>
              {{ formatDate(market.end_date) }}
            </el-tag>
          </div>
        </div>
        <div class="market-badges">
          <el-tag :type="market.active ? 'success' : 'info'" effect="dark" class="mr-1">
            {{ market.active ? '活跃' : '已关闭' }}
          </el-tag>
          <el-tag v-if="market.negRisk" type="warning" effect="dark">
            负风险
          </el-tag>
        </div>
      </div>
    </template>

    <!-- 选项和价格 -->
    <div v-if="parsedOutcomes && parsedOutcomes.length > 0" class="market-outcomes mb-4">
      <div class="section-title mb-2">
        <el-icon class="mr-1"><DataLine /></el-icon>
        <span>选项和价格</span>
      </div>
      <div class="outcomes-list">
        <el-row :gutter="10">
          <el-col :xs="24" :sm="12" :md="8" v-for="(outcome, index) in parsedOutcomes" :key="index" class="mb-2">
            <div class="outcome-item">
              <span class="outcome-name text-truncate">{{ outcome }}</span>
              <span class="outcome-price">
                {{ parsedPrices && parsedPrices[index] ? '$' + parsedPrices[index] : '-' }}
              </span>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- 统计数据 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :xs="24" :sm="8" v-if="market.volume">
        <el-card shadow="never" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon-wrapper"><el-icon><Money /></el-icon></div>
            <div>
              <div class="stat-label">交易量</div>
              <div class="stat-value">${{ formatNumber(market.volume) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8" v-if="market.liquidity">
        <el-card shadow="never" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon-wrapper"><el-icon><Coin /></el-icon></div>
            <div>
              <div class="stat-label">流动性</div>
              <div class="stat-value">${{ formatNumber(market.liquidity) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8" v-if="market.events && market.events.length > 0">
        <el-card shadow="never" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon-wrapper"><el-icon><Aim /></el-icon></div>
            <div>
              <div class="stat-label">关联事件</div>
              <div class="stat-value">{{ market.events.length }} 个</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 市场详细信息 -->
    <el-descriptions border :column="1" class="mb-4">
      <el-descriptions-item label="市场ID">
        <span class="font-monospace">{{ market.id }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="Slug">
        <span class="font-monospace">{{ market.slug }}</span>
      </el-descriptions-item>
      <el-descriptions-item v-if="market.closedTime" label="关闭时间">
        {{ formatDate(market.closedTime) }}
      </el-descriptions-item>
    </el-descriptions>

    <!-- 标签 -->
    <div v-if="market.tags && market.tags.length > 0" class="mb-4">
      <div class="section-title mb-2">
        <el-icon class="mr-1"><PriceTag /></el-icon>
        <span>标签</span>
      </div>
      <div class="tags-list">
        <el-tag v-for="tag in market.tags" :key="tag.id" size="small" class="mr-2 mb-2">
          {{ tag.label }}
        </el-tag>
      </div>
    </div>

    <!-- 自定义标记 -->
    <div v-if="market.marks && market.marks.length > 0" class="mb-4">
      <div class="section-title mb-2">
        <el-icon class="mr-1"><Star /></el-icon>
        <span>标记</span>
      </div>
      <div class="marks-list">
        <el-tag v-for="mark in market.marks" :key="mark" type="warning" size="small" class="mr-2 mb-2">
          {{ mark }}
        </el-tag>
      </div>
    </div>

    <!-- CLOB Token IDs -->
    <div v-if="market.clobTokenIds && market.clobTokenIds.length > 0">
      <div class="section-title mb-2">
        <el-icon class="mr-1"><Key /></el-icon>
        <span>CLOB Token IDs</span>
      </div>
      <div class="tokens-list">
        <el-tag v-for="tokenId in market.clobTokenIds" :key="tokenId" type="info" size="small" class="mr-2 mb-2 font-monospace">
          {{ tokenId }}
        </el-tag>
      </div>
    </div>
  </el-card>
</template>

<script>
import { 
  Folder, Timer, DataLine, Money, Coin, Aim, PriceTag, Star, Key 
} from '@element-plus/icons-vue'

export default {
  name: 'MarketCard',
  components: {
    Folder, Timer, DataLine, Money, Coin, Aim, PriceTag, Star, Key
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
  border-radius: 8px;
}

.card-header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-left {
  flex: 1;
  margin-right: 15px;
}

.market-question {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
  line-height: 1.4;
}

.market-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-regular);
}

.outcome-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background-color: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  transition: all 0.2s ease;
}

.outcome-item:hover {
  border-color: var(--el-border-color);
  background-color: var(--el-fill-color);
}

.outcome-name {
  flex: 1;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 500;
  margin-right: 10px;
}

.outcome-price {
  color: var(--el-color-success);
  font-weight: 700;
  font-size: 16px;
}

.stat-card {
  height: 100%;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stat-icon-wrapper {
  font-size: 24px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  padding: 10px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

/* Utility classes removed - using global.css */
.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.font-monospace {
  font-family: monospace;
}
</style>

