<script setup lang="ts">
import { Avatar } from 'frappe-ui'
import { computed } from 'vue'
import useUserStore from '../users/users'

// Who a listed document comes from: the app that ships it, as its square
// logo, or its owner. A reader without an Insights role cannot list users and
// gets `ownerName` in place of `owner`.
const props = defineProps<{
	owner?: string
	ownerName?: string
	shippedBy?: string | null
	shippedByLogo?: string | null
}>()

const userStore = props.owner ? useUserStore() : null
const name = computed(
	() => props.ownerName || (props.owner && userStore?.getName(props.owner)) || props.owner || '',
)
</script>

<template>
	<Tooltip v-if="shippedBy" :text="shippedBy">
		<div class="relative flex size-5 shrink-0 items-center justify-center">
			<Avatar
				size="xs"
				shape="square"
				:label="shippedBy"
				:image="shippedByLogo ?? undefined"
			/>
		</div>
	</Tooltip>
	<Tooltip v-else :text="name">
		<Avatar
			class="relative shrink-0"
			size="sm"
			:label="name"
			:image="owner ? userStore?.getImage(owner) : undefined"
		/>
	</Tooltip>
</template>
