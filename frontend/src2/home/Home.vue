<script setup lang="ts">
import { inject } from 'vue'
import session from '../session'
import HomeQuickActions from './HomeQuickActions.vue'
import HomeWorkbookList from './HomeWorkbookList.vue'

const $dayjs = inject('$dayjs')
// @ts-ignore
const today = $dayjs().format('dddd, D MMMM')
</script>

<template>
	<div class="flex flex-1 flex-col space-y-8 overflow-hidden bg-surface-base p-6">
		<div class="space-y-2">
			<div class="text-4xl-bold text-ink-gray-8">Hello, {{ session.user.first_name }} 👋</div>
			<div class="text-lg text-ink-gray-5">{{ today }}</div>
		</div>
		<HomeQuickActions></HomeQuickActions>
		<HomeWorkbookList></HomeWorkbookList>
	</div>
</template>
