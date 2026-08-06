<script setup lang="ts">
import { watchDebounced } from '@vueuse/core'
import { SearchIcon } from 'lucide-vue-next'
import { computed, ref, watchEffect } from 'vue'
import { __ } from '../translation'
import useUserStore, { User } from '../users/users'

const props = defineProps<{
	placeholder?: string
	hideUsers?: string[]
	// only for pickers whose server side rejects an address that belongs to
	// nobody - otherwise a typo becomes a silent grant
	allowCustomEmail?: boolean
}>()
const selectedUserEmail = defineModel<string>()

const userStore = useUserStore()
const searchTxt = ref('')
watchEffect(() => {
	searchTxt.value = selectedUserEmail.value || ''
})

const matches = ref<User[]>([])
watchDebounced(
	searchTxt,
	() => {
		const term = searchTxt.value
		userStore.searchUsers(term).then((res) => {
			// a slow answer for an earlier term must not replace a later one
			if (term === searchTxt.value) matches.value = res
		})
	},
	{ debounce: 300, immediate: true },
)

const isEmail = (value: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim())

const options = computed(() => {
	const hidden = new Set(props.hideUsers || [])
	const found = matches.value
		.filter((user) => user.enabled && !hidden.has(user.email))
		.map((user) => ({
			...user,
			label: user.full_name,
			value: user.email,
			description: user.email,
		}))

	const address = searchTxt.value.trim()
	if (!props.allowCustomEmail || found.length || !isEmail(address) || hidden.has(address)) {
		return found
	}

	// nobody to browse here, so let the address stand on its own - the server
	// decides whether it belongs to an Insights user
	return [{ label: address, value: address, description: __('Share with this address') }]
})
</script>

<template>
	<Autocomplete
		:hide-search="true"
		:autofocus="false"
		:modelValue="selectedUserEmail"
		@update:modelValue="selectedUserEmail = $event?.value"
		:options="options"
	>
		<template #target="{ open }">
			<FormControl
				class="w-full"
				type="text"
				:placeholder="props.placeholder || 'Search user...'"
				autocomplete="off"
				v-model="searchTxt"
				@update:modelValue="open"
				@focus="open"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" stroke-width="1.5" />
				</template>
			</FormControl>
		</template>

		<template #item-prefix="{ option }">
			<Avatar size="sm" :label="option.label" :image="option.user_image" />
		</template>
	</Autocomplete>
</template>
