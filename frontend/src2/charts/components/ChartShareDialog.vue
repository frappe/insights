<script setup lang="ts">
import { computed, ref } from 'vue'
import VisibilitySelector from '../../components/VisibilitySelector.vue'
import { copyToClipboard } from '../../helpers'
import { confirmDialog } from '../../helpers/confirm_dialog'
import { __ } from '../../translation'
import { DataAuthority, Visibility } from '../../types/workbook.types'
import { Chart } from '../chart'

const props = defineProps<{ chart: Chart }>()
const show = defineModel()

const chart = props.chart

const visibility = ref<Visibility>(chart.doc.visibility || 'Private')
const visibleToRoles = ref((chart.doc.visible_to_roles || []).map((r) => r.role))
const dataAuthority = ref<DataAuthority>(chart.doc.data_authority || 'Viewer')

const shareLink = computed(() => chart.getShareLink())
const iFrameLink = computed(() => {
	return `<iframe src="${shareLink.value}" width="100%" height="300" frameborder="0"></iframe>`
})

const hasChanged = computed(() => {
	const prev = {
		visibility: visibility.value,
		visible_to_roles: visibleToRoles.value,
		data_authority: dataAuthority.value,
	}
	const next = {
		visibility: chart.doc.visibility || 'Private',
		visible_to_roles: (chart.doc.visible_to_roles || []).map((r) => r.role),
		data_authority: chart.doc.data_authority || 'Viewer',
	}
	return JSON.stringify(prev) !== JSON.stringify(next)
})

const authorityOptions = computed(() => [
	{
		label: __("Each viewer's own data access"),
		value: 'Viewer',
	},
	{
		label: __('My data access'),
		value: 'Author',
	},
])

const wideAudience = computed(
	() => visibility.value === 'Public' || visibility.value === 'Everyone',
)
const exposesAuthorRows = computed(() => wideAudience.value && dataAuthority.value === 'Author')

function saveChanges() {
	if (exposesAuthorRows.value) {
		confirmDialog({
			title: __('Show everyone the rows you can see?'),
			message: __(
				'This chart runs with your data access, so every viewer sees the rows you can see, including rows their own permissions would hide. Use it only for numbers you would publish.',
			),
			theme: 'red',
			primaryActionLabel: __('Yes, use my data access'),
			onSuccess: applyChanges,
		})
		return
	}
	applyChanges()
}

function applyChanges() {
	chart.doc.visibility = visibility.value
	chart.doc.visible_to_roles = visibleToRoles.value.map((role) => ({ role }))
	chart.doc.data_authority = dataAuthority.value
	// mirrors the top rung until is_public retires with the template migration
	chart.doc.is_public = visibility.value === 'Public'
	show.value = false
}
</script>

<template>
	<Dialog
		v-model:open="show"
		:title="__('Share Chart')"
		:actions="[
			{
				label: __('Done'),
				variant: 'solid',
				disabled: !hasChanged,
				onClick: saveChanges,
			},
		]"
	>
		<template #default>
			<div class="flex flex-col gap-4 text-base">
				<VisibilitySelector v-model:visibility="visibility" v-model:roles="visibleToRoles">
					<template #actions>
						<Tooltip text="Copy Link" :hoverDelay="0.1">
							<Button icon="lucide-link-2" @click="copyToClipboard(shareLink)">
							</Button>
						</Tooltip>
						<Tooltip text="Copy iFrame" :hoverDelay="0.1">
							<Button icon="lucide-code" @click="copyToClipboard(iFrameLink)">
							</Button>
						</Tooltip>
					</template>
				</VisibilitySelector>

				<div class="flex flex-col gap-2">
					<span class="text-sm text-ink-gray-5">{{ __('Whose data access') }}</span>
					<Combobox
						v-model="dataAuthority"
						:options="authorityOptions"
						:placeholder="__('Select an option')"
					/>
					<p v-if="exposesAuthorRows" class="text-sm text-ink-red-6">
						{{
							__(
								'Viewers will see the rows you can see, including rows their own permissions would hide.',
							)
						}}
					</p>
				</div>
			</div>
		</template>
	</Dialog>
</template>
