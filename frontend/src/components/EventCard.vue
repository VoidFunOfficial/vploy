<template>
  <el-card class="event-card mb-4" shadow="hover">
    <!-- 卡片头部 -->
    <template #header>
      <div class="card-header-content">
        <div class="header-left">
          <h3 class="event-title">{{ event.title }}</h3>
          <div class="event-meta mt-2">
            <el-tag v-if="event.end_date" type="info" effect="plain" size="small">
              <el-icon class="mr-1"><Timer /></el-icon>
              {{ formatDate(event.end_date) }}
            </el-tag>
          </div>
        </div>
        <div class="event-badges">
          <el-tag :type="event.active ? 'success' : 'info'" effect="dark" class="mr-1">
            {{ event.active ? '活跃' : '已关闭' }}
          </el-tag>
          <el-tag v-if="event.negRisk" type="warning" effect="dark">
            负风险
          </el-tag>
        </div>
      </div>
    </template>

    <!-- 事件描述 -->
    <div v-if="event.description" class="event-description mb-4">
      <el-alert :closable="false" type="info" show-icon>
        <template #title>
          <span class="description-text" style="white-space: pre-wrap;">{{ event.description }}</span>
        </template>
      </el-alert>
    </div>

    <!-- 统计数据卡片 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :xs="24" :sm="8" v-if="event.volume !== null && event.volume !== undefined">
        <el-card shadow="never" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon-wrapper"><el-icon><Money /></el-icon></div>
            <div>
              <div class="stat-label">交易量</div>
              <div class="stat-value">${{ formatNumber(event.volume) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8" v-if="event.liquidity !== null && event.liquidity !== undefined">
        <el-card shadow="never" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon-wrapper"><el-icon><Coin /></el-icon></div>
            <div>
              <div class="stat-label">流动性</div>
              <div class="stat-value">${{ formatNumber(event.liquidity) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8" v-if="event.markets && event.markets.length > 0">
        <el-card shadow="never" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon-wrapper"><el-icon><DataLine /></el-icon></div>
            <div>
              <div class="stat-label">关联市场</div>
              <div class="stat-value">{{ event.markets.length }} 个</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 事件详细信息 -->
    <el-descriptions border :column="1" class="mb-4">
      <el-descriptions-item label="事件ID">
        <span class="font-monospace">{{ event.id }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="Slug">
        <span class="font-monospace">{{ event.slug }}</span>
      </el-descriptions-item>
      <el-descriptions-item v-if="event.start_date" label="开始时间">
        {{ formatDate(event.start_date) }}
      </el-descriptions-item>
    </el-descriptions>

    <!-- 标签 -->
    <div v-if="event.tags && event.tags.length > 0" class="mb-4">
      <div class="section-title mb-2">
        <el-icon class="mr-1"><PriceTag /></el-icon>
        <span>标签</span>
      </div>
      <div class="tags-list">
        <el-tag v-for="tag in event.tags" :key="tag.id" size="small" class="mr-2 mb-2">
          {{ tag.label }}
        </el-tag>
      </div>
    </div>

    <!-- 自定义标记 -->
    <div v-if="event.marks && event.marks.length > 0" class="mb-4">
      <div class="section-title mb-2">
        <el-icon class="mr-1"><Star /></el-icon>
        <span>标记</span>
      </div>
      <div class="marks-list">
        <el-tag v-for="mark in event.marks" :key="mark" type="warning" size="small" class="mr-2 mb-2">
          {{ mark }}
        </el-tag>
      </div>
    </div>

    <!-- 关联市场列表 -->
    <div v-if="event.markets && event.markets.length > 0" class="related-markets">
      <el-collapse v-model="activeNames">
        <el-collapse-item name="1">
          <template #title>
            <div class="section-title" style="margin-bottom: 0;">
              <el-icon class="mr-1"><TrendCharts /></el-icon>
              <span>关联市场 ({{ event.markets.length }})</span>
            </div>
          </template>
          <div class="markets-list pt-2">
            <div
              v-for="(market, index) in event.markets"
              :key="market.id || index"
              class="mb-3"
            >
              <MarketMiniCard :market="market" />
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </el-card>
</template>

<script>
import { ref } from 'vue'
import MarketMiniCard from './MarketMiniCard.vue'
import {
  Timer,
  Money,
  Coin,
  DataLine,
  PriceTag,
  Star,
  TrendCharts
} from '@element-plus/icons-vue'

export default {
  name: 'EventCard',
  components: {
    MarketMiniCard,
    Timer,
    Money,
    Coin,
    DataLine,
    PriceTag,
    Star,
    TrendCharts
  },
  props: {
    event: {
      type: Object,
      required: true
    }
  },
  setup() {
    // 控制关联市场的展开/收起状态
    const activeNames = ref([])

    return {
      activeNames
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
  border-radius: 8px;
  transition: box-shadow 0.2s ease;
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

.event-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
  line-height: 1.4;
}

.event-badges {
  display: flex;
  flex-shrink: 0;
}

.stat-card {
  height: 100%;
  background-color: var(--el-fill-color-light);
  border: none;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-size: 20px;
}

.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 2px;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-regular);
}

.tags-list,
.marks-list {
  display: flex;
  flex-wrap: wrap;
}

.font-monospace {
  font-family: var(--font-family-monospace, monospace);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .card-header-content {
    flex-direction: column;
    gap: 10px;
  }

  .header-left {
    margin-right: 0;
  }

  .event-badges {
    align-self: flex-start;
  }
}
</style>

