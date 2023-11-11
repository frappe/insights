<script setup>
import PublicShareDialog from '@/components/PublicShareDialog.vue'
import useDashboards from '@/dashboard/useDashboards'
import { computed, inject, ref, watch } from 'vue'

const query = inject('query')

const showShareDialog = ref(false)
const showDashboardDialog = ref(false)
const dashboards = useDashboards()
dashboards.reload()
const toDashboard = ref(null)
const addingToDashboard = ref(false)
const dashboardOptions = computed(() => {
	return dashboards.list.map((d) => {
		return { label: d.title, value: d.name }
	})
})
const $notify = inject('$notify')
const addChartToDashboard = async () => {
	if (!toDashboard.value) return
	await query.chart.addToDashboard(toDashboard.value.value)
	showDashboardDialog.value = false
	$notify({
		variant: 'success',
		title: 'Success',
		message: 'Chart added to dashboard',
	})
}

const dashboardInput = ref(null)
watch(
	() => showDashboardDialog.value,
	(val) => {
		if (val) {
			setTimeout(() => {
				dashboardInput.value.input?.$el?.blur()
				dashboardInput.value.input?.$el?.focus()
			}, 500)
		}
	},
	{ immediate: true }
)
</script>

<template>
	<div class="flex gap-2">
		<Button variant="outline" @click="showDashboardDialog = true"> Add to Dashboard </Button>
		<Button variant="outline" @click="showShareDialog = true"> Share </Button>
	</div>

	<PublicShareDialog
		v-if="query.chart.doc?.doctype && query.chart.doc?.name"
		v-model:show="showShareDialog"
		:resource-type="query.chart.doc.doctype"
		:resource-name="query.chart.doc.name"
		:allow-public-access="true"
		:isPublic="Boolean(query.chart.doc.is_public)"
		@togglePublicAccess="query.chart.togglePublicAccess"
	/>

	<Dialog :options="{ title: 'Add to Dashboard' }" v-model="showDashboardDialog">
		<template #body-content>
			<div class="text-base">
				<span class="mb-2 block text-sm leading-4 text-gray-700">Dashboard</span>
				<Autocomplete
					ref="dashboardInput"
					:options="dashboardOptions"
					v-model="toDashboard"
				/>
			</div>
		</template>
		<template #actions>
			<Button variant="solid" @click="addChartToDashboard" :loading="addingToDashboard">
				Add
			</Button>
		</template>
	</Dialog>
</template>
