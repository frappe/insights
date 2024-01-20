<script setup>
import { computed, ref, inject } from 'vue'
import { TextEditor, call } from 'frappe-ui'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])
const show = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
const content = ref('')
const isCritical = ref(false)

const dialogOptions = { title: 'Contact the Team', size: '2xl' }
const selectedTabIndex = ref(0)
const tabs = [
	{
		label: 'Question',
		description: 'How do I...',
		iconName: 'help-circle',
		placeholder: 'I am not sure how to...',
	},
	{
		label: 'Feedback',
		description: 'What if there was...',
		iconName: 'rss',
		placeholder: 'I think it would be great if...',
	},
	{
		label: 'Bug Report',
		description: 'When I try to...',
		iconName: 'alert-triangle',
		placeholder: 'I found a bug, when I try to...',
	},
]

function close() {
	show.value = false
	selectedTabIndex.value = 0
	content.value = ''
	isCritical.value = false
}
const $notify = inject('$notify')
const sending = ref(false)
async function submit() {
	sending.value = true
	await call('insights.api.contact_team', {
		message_type: tabs[selectedTabIndex.value].label,
		message_content: content.value,
		is_critical: isCritical.value,
	})
	sending.value = false
	close()
	$notify({
		title: 'Message Sent',
		message: 'Your message has been sent to the team.',
		variant: 'success',
	})
}
</script>

<template>
	<Dialog :options="dialogOptions" v-model="show" :dismissable="true" @onClose="close">
		<template #body-content>
			<div class="flex w-full flex-col space-y-4 text-base">
				<div
					class="flex w-full cursor-pointer items-center space-x-2 rounded bg-gray-100 p-1.5"
				>
					<div
						v-for="(tab, index) in tabs"
						class="flex h-full flex-1 items-center justify-between bg-transparent px-3 py-1.5 transition-all"
						:class="[selectedTabIndex === index ? 'rounded bg-white shadow' : '']"
						@click="selectedTabIndex = index"
					>
						<div class="flex flex-col">
							<p>{{ tab.label }}</p>
							<p class="text-xs text-gray-600">{{ tab.description }}</p>
						</div>
						<FeatherIcon :name="tab.iconName" class="h-5 w-5 text-gray-500" />
					</div>
				</div>

				<div class="flex h-[20rem] flex-col rounded border px-4 py-2 shadow">
					<TextEditor
						:key="selectedTabIndex"
						editor-class="flex flex-1 prose-sm flex flex-col justify-end"
						:placeholder="tabs[selectedTabIndex].placeholder"
						:content="content"
						:editable="true"
						@change="content = $event"
					/>
				</div>
				<span class="!mt-2 text-sm text-gray-600">
					You can use markdown syntax to format your message. You can also drag and drop
					images to upload them.
				</span>
				<div class="mt-2 flex items-center justify-between">
					<Input
						v-show="selectedTabIndex == 2"
						label="I am not able to use the app because of this bug"
						type="checkbox"
						v-model="isCritical"
					/>
					<Button
						variant="solid"
						:loading="sending"
						:label="selectedTabIndex === 2 ? 'Report Bug' : 'Send'"
						@click="submit"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>
