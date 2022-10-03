<template>
	<div class="text-base text-gray-800">
		<div class="flex flex-col items-center justify-center space-y-3">
			<div class="flex items-center">{{ progress }}%</div>
			<div class="mt-2 h-2 w-2/3 rounded-lg bg-gray-100">
				<div
					class="h-full rounded-lg transition-all"
					:class="[message.indexOf('Error') === -1 ? 'bg-green-500' : 'bg-red-600']"
					:style="`width: ${progress}%`"
				/>
			</div>
			<div class="flex items-center space-x-2">
				<span>{{ message }}</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, onMounted, ref, nextTick } from 'vue'
import { createResource } from 'frappe-ui'
import { useRouter } from 'vue-router'

const $socket = inject('$socket')
const $auth = inject('$auth')

const user = computed(() => $auth.user.user_id)
const message = ref('Starting...')
const progress = ref(0)

const router = useRouter()
const createDemoDb = createResource('insights.api.setup.setup_demo')
$socket.on('insights_demo_setup_progress', (data) => {
	console.log(data)
	if (!data.user == user.value) {
		return
	}
	if (data.progress < 0) {
		$socket.off('insights_demo_setup_progress')
		message.value = 'Error occurred. Please check console...'
		progress.value = 100
		return
	}
	progress.value = data.progress
	message.value = data.message
	if (data.progress === 100) {
		wrapUp()
	}
})
onMounted(() => {
	createDemoDb.submit().then(() => {
		wrapUp()
	})
})

function wrapUp() {
	$socket.off('insights_demo_setup_progress')
	localStorage.removeItem('setupComplete')
	localStorage.removeItem('onboardingComplete')
	nextTick(() => router.push('/'))
}
</script>
