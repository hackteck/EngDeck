<template>
  <main style="max-width: 760px; margin: 24px auto; padding: 16px">
    <h1>EngDeck 🇬🇧</h1>
    <p>Offline English learning on Steam Deck — STT, grammar feedback, personalized exercises.</p>
    <section style="margin-top: 24px">
      <Recorder :user-id="userId" @transcribed="onTranscribed" />
    </section>
    <section v-if="text" style="margin-top: 24px">
      <h3>Grammar feedback</h3>
      <button @click="checkGrammar" :disabled="loadingGrammar">Check</button>
      <div v-if="grammar">
        <p><strong>Corrected:</strong> {{ grammar.corrected }}</p>
        <ul>
          <li v-for="(i, idx) in grammar.issues" :key="idx">
            <strong>{{ i.category }}</strong>: <em>{{ i.span }}</em> — {{ i.message }}
            <span v-if="i.suggestion"> → {{ i.suggestion }}</span>
          </li>
        </ul>
      </div>
    </section>
    <section style="margin-top: 24px">
      <h3>Practice</h3>
      <button @click="loadExercises" :disabled="loadingExercises">Generate</button>
      <ol v-if="exercises.length">
        <li v-for="(ex, idx) in exercises" :key="idx">
          <div><strong>{{ ex.type }}</strong>: {{ ex.prompt }}</div>
          <details><summary>Answer</summary><div>{{ ex.answer }}</div></details>
        </li>
      </ol>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import Recorder from './components/Recorder.vue'

const userId = ref('user-local-001')
const text = ref('')
const grammar = ref(null)
const exercises = ref([])
const loadingGrammar = ref(false)
const loadingExercises = ref(false)

function onTranscribed(t) { text.value = t }

async function checkGrammar() {
  loadingGrammar.value = true
  try {
    const res = await fetch('http://localhost:8000/grammar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId.value, text: text.value })
    })
    const data = await res.json()
    grammar.value = data
  } finally {
    loadingGrammar.value = false
  }
}

async function loadExercises() {
  loadingExercises.value = true
  try {
    const res = await fetch('http://localhost:8000/exercise', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId.value, limit: 5 })
    })
    const data = await res.json()
    exercises.value = data.exercises || []
  } finally {
    loadingExercises.value = false
  }
}
</script>
