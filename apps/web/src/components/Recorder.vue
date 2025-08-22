<template>
  <div>
    <h3>Speak</h3>
    <div>
      <button @click="start" :disabled="recording">Start</button>
      <button @click="stop" :disabled="!recording">Stop</button>
    </div>
    <p v-if="status">{{ status }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({ userId: { type: String, required: true } })
const emit = defineEmits(['transcribed'])

let mediaRecorder
let chunks = []
const recording = ref(false)
const status = ref('')

async function start() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  mediaRecorder = new MediaRecorder(stream)
  chunks = []
  mediaRecorder.ondataavailable = e => chunks.push(e.data)
  mediaRecorder.onstop = onStop
  mediaRecorder.start()
  recording.value = true
  status.value = 'Recording...'
}

async function stop() {
  if (mediaRecorder && recording.value) {
    mediaRecorder.stop()
  }
}

async function onStop() {
  recording.value = false
  status.value = 'Processing...'
  const blob = new Blob(chunks, { type: 'audio/webm' })
  const file = new File([blob], 'speech.webm', { type: 'audio/webm' })
  const form = new FormData()
  form.append('user_id', props.userId)
  form.append('audio', file)

  const res = await fetch('http://localhost:8000/stt', { method: 'POST', body: form })
  const data = await res.json()
  if (data.ok) {
    emit('transcribed', data.text)
    status.value = 'Transcribed: ' + data.text
  } else {
    status.value = 'Error: ' + (data.error || 'unknown')
  }
}
</script>
