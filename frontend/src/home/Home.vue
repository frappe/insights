<script setup>
import auth from '@/utils/auth'
import HomeOnboarding from './HomeOnboarding.vue'
import HomeQuickActions from './HomeQuickActions.vue'
import HomePinnedItems from './HomePinnedItems.vue'
import HomeRecentRecords from './HomeRecentRecords.vue'
import { inject } from 'vue'

const $dayjs = inject('$dayjs')
const today = $dayjs().format('dddd, D MMMM')

document.title = 'Home | Frappe Insights'
</script>

<template>
	<div class="flex flex-1 flex-col space-y-8 overflow-hidden bg-white p-8">
		<div class="space-y-2">
			<div class="text-3xl font-bold text-gray-900">Hello, {{ auth.user.first_name }} 👋</div>
			<div class="text-lg text-gray-600">{{ today }}</div>
		</div>
		<HomeOnboarding></HomeOnboarding>
		<HomeQuickActions></HomeQuickActions>
		<HomePinnedItems></HomePinnedItems>
		<HomeRecentRecords></HomeRecentRecords>
	</div>
</template>
