<template>
  <div class="analysis-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>分析界面</h2>
        </div>
      </template>

      <!-- 添加控制面板 -->
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="添加事件" name="event">
          <div class="add-form">
            <el-form :inline="true" @submit.prevent>
              <el-form-item label="添加方式">
                <el-select v-model="eventAddType" placeholder="选择方式" style="width: 120px">
                  <el-option label="通过 Slug" value="slug" />
                  <el-option label="通过 ID" value="id" />
                </el-select>
              </el-form-item>
              <el-form-item label="内容" style="flex-grow: 1; min-width: 300px;">
                <el-input
                  v-model="eventInput"
                  :placeholder="eventAddType === 'slug' ? '请输入事件 slug' : '请输入事件 ID'"
                  @keyup.enter="addEvent"
                  clearable
                  style="width: 100%"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="loading" :disabled="!eventInput.trim()" @click="addEvent">
                  {{ loading ? '加载中...' : '添加事件' }}
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <el-tab-pane label="添加市场" name="market">
          <div class="add-form">
            <el-form :inline="true" @submit.prevent>
              <el-form-item label="添加方式">
                <el-select v-model="marketAddType" placeholder="选择方式" style="width: 120px">
                  <el-option label="通过 Slug" value="slug" />
                  <el-option label="通过 ID" value="id" />
                </el-select>
              </el-form-item>
              <el-form-item label="内容" style="flex-grow: 1; min-width: 300px;">
                <el-input
                  v-model="marketInput"
                  :placeholder="marketAddType === 'slug' ? '请输入市场 slug' : '请输入市场 ID'"
                  @keyup.enter="addMarket"
                  clearable
                  style="width: 100%"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="loading" :disabled="!marketInput.trim()" @click="addMarket">
                  {{ loading ? '加载中...' : '添加市场' }}
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 卡片展示区域 -->
      <div class="cards-container">
        <!-- 事件卡片列表 -->
        <div v-if="events.length > 0" class="cards-section">
          <el-divider content-position="left">
            <h3>事件列表 <el-tag type="success" effect="dark" round size="small">{{ events.length }}</el-tag></h3>
          </el-divider>
          <div class="cards-list">
            <div v-for="(event, index) in events" :key="'event-' + index" class="card-wrapper">
              <el-button 
                class="remove-btn" 
                type="danger" 
                circle 
                :icon="Close" 
                size="small"
                @click="removeEvent(index)" 
                title="移除" 
              />
              <EventCard :event="event" />
            </div>
          </div>
        </div>

        <!-- 市场卡片列表 -->
        <div v-if="markets.length > 0" class="cards-section">
          <el-divider content-position="left">
            <h3>市场列表 <el-tag type="success" effect="dark" round size="small">{{ markets.length }}</el-tag></h3>
          </el-divider>
          <div class="cards-list">
            <div v-for="(market, index) in markets" :key="'market-' + index" class="card-wrapper">
              <el-button 
                class="remove-btn" 
                type="danger" 
                circle 
                :icon="Close" 
                size="small"
                @click="removeMarket(index)" 
                title="移除" 
              />
              <MarketCard :market="market" />
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <el-empty v-if="events.length === 0 && markets.length === 0" description="暂无数据">
           <template #extra>
              <p class="empty-hint">请使用上方表单添加事件或市场</p>
           </template>
        </el-empty>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Close } from '@element-plus/icons-vue'
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
          ElMessage.success('添加事件成功')
        } else {
          ElMessage.error(response?.message || '获取事件失败')
        }
      } catch (err) {
        ElMessage.error(err.response?.data?.message || '获取事件失败，请检查输入是否正确')
      } finally {
        loading.value = false
      }
    }

    // 添加市场
    const addMarket = async () => {
      const input = marketInput.value.trim()
      if (!input) return

      loading.value = true

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
          ElMessage.success('添加市场成功')
        } else {
          ElMessage.error(response?.message || '获取市场失败')
        }
      } catch (err) {
        ElMessage.error(err.response?.data?.message || '获取市场失败，请检查输入是否正确')
      } finally {
        loading.value = false
      }
    }

    // 移除事件
    const removeEvent = (index) => {
      events.value.splice(index, 1)
      ElMessage.info('已移除事件')
    }

    // 移除市场
    const removeMarket = (index) => {
      markets.value.splice(index, 1)
      ElMessage.info('已移除市场')
    }

    return {
      activeTab,
      loading,
      eventAddType,
      eventInput,
      events,
      marketAddType,
      marketInput,
      markets,
      addEvent,
      addMarket,
      removeEvent,
      removeMarket,
      Close
    }
  }
}
</script>

<style scoped>
/* Removed .analysis-container since we use .page-container */

.card-header h2 {
  margin: 0;
  font-size: 18px;
  color: var(--el-text-color-primary);
}

.add-form {
  padding: 10px 0;
  display: flex;
  justify-content: flex-start;
}

.cards-container {
  margin-top: 20px;
}

.cards-section {
  margin-bottom: 30px;
}

.section-header h3 {
  font-size: 16px;
  color: var(--el-text-color-primary);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
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
  z-index: 10;
}

.empty-hint {
  color: var(--text-color-secondary);
  font-size: 14px;
}

@media (max-width: 768px) {
  .add-form .el-form-item {
    margin-right: 0;
    margin-bottom: 15px;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }
  
  .add-form .el-form-item__content {
    width: 100%;
  }
}
</style>

