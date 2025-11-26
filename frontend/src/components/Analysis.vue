<template>
  <div class="analysis-container">
    <div class="analysis-header">
      <h2>分析界面</h2>
      <p class="header-desc">添加事件或市场进行分析</p>
    </div>

    <!-- 添加控制面板 -->
    <div class="add-panel">
      <div class="panel-tabs">
        <button
          :class="['tab-btn', { active: activeTab === 'event' }]"
          @click="activeTab = 'event'"
        >
          添加事件
        </button>
        <button
          :class="['tab-btn', { active: activeTab === 'market' }]"
          @click="activeTab = 'market'"
        >
          添加市场
        </button>
      </div>

      <div class="panel-content">
        <!-- 事件添加表单 -->
        <div v-if="activeTab === 'event'" class="add-form">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">添加方式</label>
              <select v-model="eventAddType" class="form-select">
                <option value="slug">通过 Slug</option>
                <option value="id">通过 ID</option>
              </select>
            </div>
            <div class="form-group flex-grow">
              <label class="form-label">
                {{ eventAddType === 'slug' ? '事件 Slug' : '事件 ID' }}
              </label>
              <input
                v-model="eventInput"
                type="text"
                class="form-input"
                :placeholder="eventAddType === 'slug' ? '请输入事件 slug' : '请输入事件 ID'"
                @keyup.enter="addEvent"
              />
            </div>
            <div class="form-group">
              <label class="form-label">&nbsp;</label>
              <button
                class="btn btn-primary"
                @click="addEvent"
                :disabled="loading || !eventInput.trim()"
              >
                {{ loading ? '加载中...' : '添加事件' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 市场添加表单 -->
        <div v-if="activeTab === 'market'" class="add-form">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">添加方式</label>
              <select v-model="marketAddType" class="form-select">
                <option value="slug">通过 Slug</option>
                <option value="id">通过 ID</option>
              </select>
            </div>
            <div class="form-group flex-grow">
              <label class="form-label">
                {{ marketAddType === 'slug' ? '市场 Slug' : '市场 ID' }}
              </label>
              <input
                v-model="marketInput"
                type="text"
                class="form-input"
                :placeholder="marketAddType === 'slug' ? '请输入市场 slug' : '请输入市场 ID'"
                @keyup.enter="addMarket"
              />
            </div>
            <div class="form-group">
              <label class="form-label">&nbsp;</label>
              <button
                class="btn btn-primary"
                @click="addMarket"
                :disabled="loading || !marketInput.trim()"
              >
                {{ loading ? '加载中...' : '添加市场' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- 卡片展示区域 -->
    <div class="cards-container">
      <!-- 事件卡片列表 -->
      <div v-if="events.length > 0" class="cards-section">
        <div class="section-header">
          <h3>事件列表</h3>
          <span class="count-badge">{{ events.length }}</span>
        </div>
        <div class="cards-list">
          <div v-for="(event, index) in events" :key="'event-' + index" class="card-wrapper">
            <button class="remove-btn" @click="removeEvent(index)" title="移除">×</button>
            <EventCard :event="event" />
          </div>
        </div>
      </div>

      <!-- 市场卡片列表 -->
      <div v-if="markets.length > 0" class="cards-section">
        <div class="section-header">
          <h3>市场列表</h3>
          <span class="count-badge">{{ markets.length }}</span>
        </div>
        <div class="cards-list">
          <div v-for="(market, index) in markets" :key="'market-' + index" class="card-wrapper">
            <button class="remove-btn" @click="removeMarket(index)" title="移除">×</button>
            <MarketCard :market="market" />
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="events.length === 0 && markets.length === 0" class="empty-state">
        <div class="empty-icon">📊</div>
        <p>暂无数据</p>
        <p class="empty-hint">请使用上方表单添加事件或市场</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import EventCard from './EventCard.vue'
import MarketCard from './MarketCard.vue'
import { getEventBySlug, getEventById, getMarketBySlug, getMarketById } from '@/api/polymarket'

export default {
  name: 'Analysis',
  components: {
    EventCard,
    MarketCard
  },
  setup() {
    // 状态管理
    const activeTab = ref('event')
    const loading = ref(false)
    const error = ref('')

    // 事件相关
    const eventAddType = ref('slug')
    const eventInput = ref('')
    const events = ref([])

    // 市场相关
    const marketAddType = ref('slug')
    const marketInput = ref('')
    const markets = ref([])

    // 添加事件
    const addEvent = async () => {
      const input = eventInput.value.trim()
      if (!input) return

      loading.value = true
      error.value = ''

      try {
        let response
        if (eventAddType.value === 'slug') {
          response = await getEventBySlug(input)
        } else {
          response = await getEventById(input)
        }

        if (response && response.success) {
          events.value.push(response.data)
          eventInput.value = ''
        } else {
          error.value = response?.message || '获取事件失败'
        }
      } catch (err) {
        error.value = err.response?.data?.message || '获取事件失败，请检查输入是否正确'
      } finally {
        loading.value = false
      }
    }

    // 添加市场
    const addMarket = async () => {
      const input = marketInput.value.trim()
      if (!input) return

      loading.value = true
      error.value = ''

      try {
        let response
        if (marketAddType.value === 'slug') {
          response = await getMarketBySlug(input)
        } else {
          response = await getMarketById(input)
        }

        if (response && response.success) {
          markets.value.push(response.data)
          marketInput.value = ''
        } else {
          error.value = response?.message || '获取市场失败'
        }
      } catch (err) {
        error.value = err.response?.data?.message || '获取市场失败，请检查输入是否正确'
      } finally {
        loading.value = false
      }
    }

    // 移除事件
    const removeEvent = (index) => {
      events.value.splice(index, 1)
    }

    // 移除市场
    const removeMarket = (index) => {
      markets.value.splice(index, 1)
    }

    return {
      activeTab,
      loading,
      error,
      eventAddType,
      eventInput,
      events,
      marketAddType,
      marketInput,
      markets,
      addEvent,
      addMarket,
      removeEvent,
      removeMarket
    }
  }
}
</script>

<style scoped>
.analysis-container {
  padding: 20px;
}

/* 头部 */
.analysis-header {
  margin-bottom: 20px;
}

.analysis-header h2 {
  font-size: 20px;
  color: #333;
  margin-bottom: 5px;
}

.header-desc {
  color: #666;
  font-size: 13px;
}

/* 添加面板 */
.add-panel {
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-bottom: 20px;
  overflow: hidden;
}

.panel-tabs {
  display: flex;
  border-bottom: 1px solid #ddd;
  background-color: #f9f9f9;
}

.tab-btn {
  flex: 1;
  padding: 12px 20px;
  border: none;
  background-color: transparent;
  color: #666;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  background-color: #f0f0f0;
}

.tab-btn.active {
  background-color: #fff;
  color: #20a53a;
  font-weight: 600;
  border-bottom: 2px solid #20a53a;
}

.panel-content {
  padding: 20px;
}

/* 表单 */
.add-form {
  width: 100%;
}

.form-row {
  display: flex;
  gap: 15px;
  align-items: flex-end;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group.flex-grow {
  flex: 1;
}

.form-label {
  margin-bottom: 8px;
  color: #333;
  font-size: 13px;
  font-weight: 500;
}

.form-select,
.form-input {
  height: 40px;
  padding: 0 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}

.form-select {
  min-width: 120px;
  cursor: pointer;
}

.form-input {
  width: 100%;
}

.form-select:focus,
.form-input:focus {
  border-color: #20a53a;
  box-shadow: 0 0 0 3px rgba(32, 165, 58, 0.1);
}

.btn-primary {
  height: 40px;
  padding: 0 20px;
  background-color: #20a53a;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background-color: #1a8c31;
}

.btn-primary:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

/* 错误提示 */
.error-message {
  padding: 12px 15px;
  background-color: #ffebee;
  border: 1px solid #ef5350;
  border-radius: 6px;
  color: #c62828;
  font-size: 13px;
  margin-bottom: 20px;
}

/* 卡片容器 */
.cards-container {
  margin-top: 20px;
}

.cards-section {
  margin-bottom: 30px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.section-header h3 {
  font-size: 16px;
  color: #333;
  font-weight: 600;
}

.count-badge {
  padding: 2px 8px;
  background-color: #20a53a;
  color: #fff;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.cards-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.card-wrapper {
  position: relative;
}

.remove-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 30px;
  height: 30px;
  border: none;
  background-color: #ff5722;
  color: #fff;
  border-radius: 50%;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  z-index: 10;
  transition: all 0.2s;
}

.remove-btn:hover {
  background-color: #e64a19;
  transform: scale(1.1);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 15px;
}

.empty-state p {
  color: #666;
  font-size: 14px;
  margin: 5px 0;
}

.empty-hint {
  color: #999;
  font-size: 13px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .analysis-container {
    padding: 10px;
  }

  .form-row {
    flex-direction: column;
    gap: 10px;
  }

  .form-group {
    width: 100%;
  }

  .remove-btn {
    width: 26px;
    height: 26px;
    font-size: 18px;
  }
}
</style>

