<script setup>
import PublicShareDialog from '@/components/PublicShareDialog.vue'
import useDashboards from '@/dashboard/useDashboards'
import { Maximize } from 'lucide-vue-next'
import { computed, inject, ref, watch } from 'vue'

const emit = defineEmits(['fullscreen'])
const query = inject('query')

const showShareDialog = ref(false)
const showDashboardDialog = ref(false)
const dashboards = useDashboards()
const toDashboard = ref(null)
const addingToDashboard = ref(false)
const dashboardOptions = computed(() => {
	return dashboards.list.map((d) => {
		return { label: d.title, value: d.name }
	})
})

const $notify = inject('$notify')
function onAddToDashboard() {
	showDashboardDialog.value = true
}
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

watch(showDashboardDialog, (val) => val && dashboards.reload(), { immediate: true })

const showNewDashboardDialog = ref(false)
function onCreateDashboard() {
	showNewDashboardDialog.value = true
	showDashboardDialog.value = false
}
const newDashboardTitle = ref('')
const creatingDashboard = ref(false)
async function createNewDashboard() {
	if (!newDashboardTitle.value) return
	creatingDashboard.value = true
	await dashboards.create(newDashboardTitle.value)
	creatingDashboard.value = false
	showNewDashboardDialog.value = false
	showDashboardDialog.value = true
}
</script>

<template>
	<div class="flex gap-2">
		<Button variant="outline" @click="emit('fullscreen')">
			<template #icon> <Maximize class="h-4 w-4" /> </template>
		</Button>
		<Button variant="outline" @click="onAddToDashboard()"> Add to Dashboard </Button>
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

	<Dialog
		:options="{
			title: 'Add to Dashboard',
			actions: [
				{
					label: 'Add',
					variant: 'solid',
					disabled: !toDashboard,
					onClick: addChartToDashboard,
					loading: addingToDashboard,
				},
			],
		}"
		v-model="showDashboardDialog"
	>
		<template #body-content>
			<div class="text-base">
				<span class="mb-2 block text-sm leading-4 text-gray-700">Dashboard</span>
				<Autocomplete :options="dashboardOptions" v-model="toDashboard">
					<template #footer="{ togglePopover }">
						<Button
							class="w-full"
							variant="ghost"
							iconLeft="plus"
							@click="onCreateDashboard() || togglePopover()"
						>
							Create New
						</Button>
					</template>
				</Autocomplete>
			</div>
		</template>
	</Dialog>
	<Dialog
		:options="{
			title: 'Create New Dashboard',
			actions: [
				{
					label: 'Create',
					variant: 'solid',
					onClick: createNewDashboard,
					loading: creatingDashboard,
				},
			],
		}"
		v-model="showNewDashboardDialog"
	>
		<template #body-content>
			<div class="text-base">
				<span class="mb-2 block text-sm leading-4 text-gray-700">Dashboard Title</span>
				<FormControl
					v-model="newDashboardTitle"
					placeholder="Enter title"
					class="w-full"
					autocomplete="off"
				/>
			</div>
		</template>
	</Dialog>
</template>
