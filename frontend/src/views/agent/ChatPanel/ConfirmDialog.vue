<template>
  <div class="confirm-overlay">
    <div class="confirm-box">
      <template v-if="isAskUser">
        <div class="confirm-icon">💬</div>
        <div class="confirm-title">Agent 提问</div>
        <div class="confirm-msg">{{ message }}</div>
        <div class="confirm-input-row">
          <input
            :value="replyText"
            @input="$emit('update:replyText', $event.target.value)"
            class="confirm-input"
            placeholder="请输入回复..."
            @keydown.enter.prevent="$emit('submit-reply')"
          />
          <button class="confirm-approve" @click="$emit('submit-reply')">发送回复</button>
        </div>
      </template>
      <template v-else>
        <div class="confirm-icon">🔐</div>
        <div class="confirm-title">工具执行确认</div>
        <div class="confirm-msg">{{ message }}</div>
        <div class="confirm-tool">工具: {{ toolName }}</div>
        <div class="confirm-btns">
          <button class="confirm-reject" @click="$emit('reject')">拒绝</button>
          <button class="confirm-approve" @click="$emit('approve')">允许执行</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
defineProps({
  isAskUser: { type: Boolean, default: false },
  message: { type: String, default: '' },
  toolName: { type: String, default: '' },
  replyText: { type: String, default: '' },
})
defineEmits(['approve', 'reject', 'submit-reply', 'update:replyText'])
</script>

<style scoped>
.confirm-overlay {
  position: absolute; inset: 0;
  background: rgba(0,0,0,.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 30; border-radius: 14px;
}
.confirm-box {
  background: #fff; border-radius: 16px; padding: 28px 32px;
  max-width: 420px; width: 90%; text-align: center;
  box-shadow: 0 20px 60px rgba(0,0,0,.2);
}
.confirm-icon { font-size: 36px; margin-bottom: 12px; }
.confirm-title { font-size: 17px; font-weight: 700; color: #333; margin-bottom: 10px; }
.confirm-msg { font-size: 14px; color: #555; line-height: 1.6; margin-bottom: 8px; }
.confirm-tool { font-size: 13px; color: #8c8680; margin-bottom: 18px; }
.confirm-btns { display: flex; gap: 10px; justify-content: center; }
.confirm-input-row { display: flex; gap: 8px; margin-top: 8px; }
.confirm-input {
  flex: 1; padding: 8px 12px; border: 1px solid #e7e0d5; border-radius: 8px;
  font-size: 14px; font-family: inherit; outline: none;
}
.confirm-input:focus { border-color: #7f9b7a; }
.confirm-reject {
  padding: 8px 24px; border-radius: 10px; border: 1px solid #e7e0d5;
  background: #fff; color: #8c8680; font-size: 14px; cursor: pointer; font-family: inherit;
}
.confirm-reject:hover { background: #fdf2ef; border-color: #e0b8ad; color: #9b3d2f; }
.confirm-approve {
  padding: 8px 24px; border-radius: 10px; border: none;
  background: #7f9b7a; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.confirm-approve:hover { background: #3d6b3a; }
</style>
