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
	<div class="flex flex-1 flex-col space-y-8 overflow-hidden bg-white p-6">
		<div class="space-y-2">
			<div class="text-3xl font-bold text-gray-900">
				Hello, {{ session.user.first_name }} 👋
			</div>
			<div class="text-lg text-gray-600">{{ today }}</div>
		</div>
		<HomeQuickActions></HomeQuickActions>
		<HomeWorkbookList></HomeWorkbookList>
	</div>
</template>
