<template>
	<Dialog v-model="show" :dismissable="true">
		<template #body>
			<div class="bg-white px-4 py-5 sm:p-6">
				<h3 class="mb-3 text-lg font-medium leading-6 text-gray-900">
					{{ title }}
				</h3>
				<div class="space-y-3 text-base">
					<div class="space-y-4">
						<div class="flex items-center space-x-4 rounded border px-4 py-2">
							<FeatherIcon name="globe" class="h-5 w-5 text-blue-500" />
							<div class="flex flex-1 flex-col">
								<div class="font-medium text-gray-800">Create Public Link</div>
								<div class="text-sm text-gray-700">
									Anyone with the link can view this
									{{ resourceType.replace('Insights ', '').toLowerCase() }}
								</div>
							</div>
							<Checkbox v-model="isPublic" />
						</div>
						<div class="flex overflow-hidden rounded bg-gray-100" v-if="publicLink">
							<div
								class="font-code form-input flex-1 overflow-hidden text-ellipsis whitespace-nowrap rounded-r-none text-sm text-gray-600"
							>
								{{ publicLink }}
							</div>
							<Tooltip text="Copy Link" :hoverDelay="0.1">
								<Button
									class="w-8 rounded-none bg-gray-200 hover:bg-gray-300"
									icon="link-2"
									@click="copyToClipboard(publicLink)"
								>
								</Button>
							</Tooltip>
							<Tooltip text="Copy iFrame" :hoverDelay="0.1">
								<Button
									class="w-8 rounded-l-none bg-gray-200 hover:bg-gray-300"
									icon="code"
									@click="copyToClipboard(iFrame)"
								>
								</Button>
							</Tooltip>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { copyToClipboard } from '@/utils'
import { createResource } from 'frappe-ui'
import { computed, watch } from 'vue'

const emit = defineEmits(['update:show', 'togglePublicAccess'])
const props = defineProps({
	show: {
		type: Boolean,
		required: true,
	},
	resourceType: {
		type: String,
		required: true,
	},
	resourceName: {
		type: String,
		required: true,
	},
	isPublic: {
		type: Boolean,
		default: false,
	},
})

const show = computed({
	get: () => props.show,
	set: (value) => {
		emit('update:show', value)
	},
})

const title = computed(() => {
	return `Share ${props.resourceType.replace('Insights ', '')}`
})

const isPublic = computed({
	get: () => props.isPublic,
	set: (value) => {
		emit('togglePublicAccess', value ? 1 : 0)
	},
})
const getPublicKey = createResource({
	url: 'insights.api.public.get_public_key',
	params: {
		resource_type: props.resourceType,
		resource_name: props.resourceName,
	},
})
watch(
	isPublic,
	(newVal, oldVal) => {
		if (newVal && !oldVal) {
			getPublicKey.fetch()
		}
	},
	{ immediate: true }
)

const resourceTypeTitle = props.resourceType.replace('Insights ', '').toLowerCase()
const publicLink = computed(() => {
	const publickKey = getPublicKey.data
	const base = `${window.location.origin}/insights/public/${resourceTypeTitle}/`
	return isPublic.value && publickKey ? base + publickKey : null
})
const iFrame = computed(() => {
	const publickKey = getPublicKey.data
	const base = `${window.location.origin}/insights/public/${resourceTypeTitle}/`
	const iframeAttrs = `width="800" height="600" frameborder="0" allowtransparency`
	return isPublic.value && publickKey
		? `<iframe src="${base + publickKey}" ${iframeAttrs}></iframe>`
		: null
})
</script>
