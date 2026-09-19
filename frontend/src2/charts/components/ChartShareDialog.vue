<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Toggle from '../../components/Toggle.vue'
import VisibilitySelector from '../../components/VisibilitySelector.vue'
import { copyToClipboard } from '../../helpers'
import { confirmDialog } from '../../helpers/confirm_dialog'
import { __ } from '../../translation'
import { Visibility } from '../../types/workbook.types'
import { Chart } from '../chart'

const props = defineProps<{ chart: Chart }>()
const show = defineModel()

const chart = props.chart

const visibility = ref<Visibility>(chart.doc.visibility || 'Private')
const visibleToRoles = ref((chart.doc.visible_to_roles || []).map((r) => r.role))
// the field is a check, so it arrives as 0 or 1, and a chart saved before it
// existed carries neither
const savedUserPermissions = () => Boolean(chart.doc.apply_user_permissions ?? true)

const applyUserPermissions = ref(chart.doc.visibility === 'Public' ? false : savedUserPermissions())

const shareLink = computed(() => chart.getShareLink())
const iFrameLink = computed(() => {
	return `<iframe src="${shareLink.value}" width="100%" height="300" frameborder="0"></iframe>`
})

const hasChanged = computed(() => {
	const prev = {
		visibility: visibility.value,
		visible_to_roles: visibleToRoles.value,
		apply_user_permissions: applyUserPermissions.value,
	}
	const next = {
		visibility: chart.doc.visibility || 'Private',
		visible_to_roles: (chart.doc.visible_to_roles || []).map((r) => r.role),
		apply_user_permissions: savedUserPermissions(),
	}
	return JSON.stringify(prev) !== JSON.stringify(next)
})

const isPublic = computed(() => visibility.value === 'Public')

// a guest has no permissions of their own, so the Public level runs as the owner
watch(isPublic, (published) => {
	if (published) applyUserPermissions.value = false
})

const wideVisibility = computed(
	() => visibility.value === 'Public' || visibility.value === 'Everyone',
)
const exposesOwnerRows = computed(() => wideVisibility.value && !applyUserPermissions.value)

function saveChanges() {
	if (exposesOwnerRows.value) {
		confirmDialog({
			title: __('Show everyone the rows you can see?'),
			message: __(
				'This chart runs with your permissions, so everyone sees the rows you can see, including rows their own permissions would hide. Use it only for numbers you would publish.',
			),
			theme: 'red',
			primaryActionLabel: __('Yes, use my permissions'),
			onSuccess: applyChanges,
		})
		return
	}
	applyChanges()
}

function applyChanges() {
	chart.doc.visibility = visibility.value
	chart.doc.visible_to_roles = visibleToRoles.value.map((role) => ({ role }))
	chart.doc.apply_user_permissions = applyUserPermissions.value
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
					<div class="flex items-center justify-between gap-2">
						<span class="text-sm text-ink-gray-5">
							{{ __('Apply User Permissions') }}
						</span>
						<Toggle v-model="applyUserPermissions" :disabled="isPublic" />
					</div>
					<p v-if="isPublic" class="text-sm text-ink-gray-5">
						{{
							__(
								'Guests have no permissions of their own, so a public link shows what you can see.',
							)
						}}
					</p>
					<p v-else-if="exposesOwnerRows" class="text-sm text-ink-red-5">
						{{
							__(
								'Everyone will see the rows you can see, including rows their own permissions would hide.',
							)
						}}
					</p>
				</div>
			</div>
		</template>
	</Dialog>
</template>
