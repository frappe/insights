<script setup lang="ts">
import { createResource } from 'frappe-ui'
import { NumberCard } from 'frappe-ui/charts'
import { Copy, LayoutDashboard, Scroll } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import VisibilitySelector from '../../components/VisibilitySelector.vue'
import OwnerAvatar from '../../components/OwnerAvatar.vue'
import RunAsOwnerField from '../../charts/components/RunAsOwnerField.vue'
import DrillActions from '../../charts/drill/DrillActions.vue'
import { columnIcon } from '../../query/column_icon'
import { __ } from '../../translation'
import OrganizationAccessRow from '../../workbook/OrganizationAccessRow.vue'
import type { PictureName } from '../upgrade_steps'
import ShareUserRow from '../../workbook/ShareUserRow.vue'
import ChartPicture from './ChartPicture.vue'
import DialogPicture from './DialogPicture.vue'
import MenuPicture from './MenuPicture.vue'

// Each picture is the screen where a reader meets a change, built from the
// components that screen uses, with fixed props. It cannot be clicked and a
// screen reader skips it: the sentences beside it carry the meaning.
const props = defineProps<{
	name: PictureName
	/** Who the share rows show. */
	person: { full_name: string; email: string }
	/** The doctype a Not Permitted card says the reader lacks. */
	doctype?: string
}>()

const BARS = [40, 62, 50, 84, 58, 70]

// The dashboards the first slide names, by the app that ships them, with the
// title and logo the workbook list shows that app by. The same rows for every
// reader, whether or not they may open them.
const SAMPLE_APP_DASHBOARDS = [
	{ title: 'Selling', app: 'erpnext' },
	{ title: 'Stock', app: 'erpnext' },
	{ title: 'Accounts', app: 'erpnext' },
	{ title: 'Payroll', app: 'hrms' },
	{ title: 'Expense Claims', app: 'hrms' },
]
const APP_TITLES: Record<string, string> = { erpnext: 'ERPNext', hrms: 'Frappe HR' }
const shippingApps = createResource({
	url: 'insights.api.upgrade.get_shipping_apps',
	cache: 'insights_shipping_apps',
	auto: props.name === 'appDashboards',
})
const appDashboards = computed(() =>
	SAMPLE_APP_DASHBOARDS.map((row) => {
		const app = (shippingApps.data ?? []).find((a: { app: string }) => a.app === row.app)
		return { title: row.title, app: app?.title ?? APP_TITLES[row.app], logo: app?.logo ?? null }
	}),
)

const inr = (value: number) => value.toLocaleString('en-IN')
const inrCompact = (value: number) =>
	value.toLocaleString('en-IN', { notation: 'compact', maximumFractionDigits: 1 })

const publicVisibility = ref<'Public'>('Public')
const rolesVisibility = ref<'Roles'>('Roles')
const noRoles = ref<string[]>([])
const dashboardRoles = ref(['Sales User', 'Accounts User'])
const chartRoles = ref(['Sales User'])
const runsAsOwner = ref(true)
</script>

<template>
	<div
		inert
		aria-hidden="true"
		class="flex items-center justify-center text-start"
		:class="props.name === 'shareNow' ? 'w-full min-w-0' : ''"
	>
		<div
			v-if="props.name === 'appDashboards'"
			class="flex w-[26rem] flex-col rounded-7 bg-surface-elevation-1 px-3 py-1.5 shadow-sm ring-1 ring-outline-gray-1"
		>
			<div
				v-for="row in appDashboards"
				:key="row.title"
				class="flex h-10 items-center gap-3 px-1 text-base"
			>
				<OwnerAvatar :shipped-by="row.app" :shipped-by-logo="row.logo" />
				<span class="flex-1 truncate text-ink-gray-8">{{ row.title }}</span>
				<span class="text-sm text-ink-gray-5">{{ row.app }}</span>
			</div>
		</div>

		<div v-else-if="props.name === 'showInDesk'" class="flex items-center gap-4">
			<div class="h-44 w-72">
				<ChartPicture :title="__('Sales by month')" :values="BARS" />
			</div>
			<MenuPicture
				class="w-44"
				:items="[
					{ label: __('View SQL'), icon: Scroll },
					{ label: __('Copy JSON'), icon: Copy },
					{ label: __('Show in Desk'), icon: LayoutDashboard, selected: true },
				]"
			/>
		</div>

		<div v-else-if="props.name === 'drill'" class="flex items-center gap-4">
			<div class="h-44 w-72">
				<ChartPicture
					:title="__('Sales by month')"
					:values="[40, 84, 50, 62, 58, 70]"
					:selected="1"
				/>
			</div>
			<MenuPicture class="w-48">
				<DrillActions can-rows can-break-down />
			</MenuPicture>
		</div>

		<div v-else-if="props.name === 'charts'" class="flex items-center gap-4">
			<div class="h-60 w-[26rem]">
				<ChartPicture
					type="Line"
					:title="__('Sales by month')"
					:values="[38, 52, 47, 66, 61, 78]"
				/>
			</div>
			<div class="flex w-60 flex-col gap-3">
				<NumberCard
					:title="__('Sales this quarter')"
					prefix="₹ "
					:value="1240000"
					:target="1500000"
					:format="inrCompact"
					:progress="{ value: (1240000 / 1500000) * 100 }"
				/>
				<NumberCard
					:title="__('New customers')"
					:value="86"
					:delta="12.4"
					delta-suffix="%"
					:delta-caption="__('vs last month')"
					:sparkline="{ data: [52, 61, 58, 70, 66, 86] }"
				/>
			</div>
		</div>

		<DialogPicture
			v-else-if="props.name === 'roles'"
			class="w-[28rem]"
			:title="__('Share Dashboard')"
		>
			<VisibilitySelector
				v-model:visibility="rolesVisibility"
				v-model:roles="dashboardRoles"
			/>
		</DialogPicture>

		<div v-else-if="props.name === 'notPermitted'" class="h-32 w-[28rem]">
			<ChartPicture
				:key="props.doctype"
				:title="__('Revenue by month')"
				:not-permitted="props.doctype || 'Sales Invoice'"
			/>
		</div>

		<DialogPicture
			v-else-if="props.name === 'shareBefore'"
			class="w-[22rem]"
			:title="__('Share Chart')"
		>
			<ShareUserRow
				:full-name="props.person.full_name"
				:email="props.person.email"
				access="edit"
			/>
		</DialogPicture>

		<div v-else-if="props.name === 'shareNow'" class="flex w-full items-start gap-3">
			<DialogPicture class="min-w-0 flex-1" :title="__('Manage Workbook Access')">
				<ShareUserRow
					:full-name="props.person.full_name"
					:email="props.person.email"
					access="edit"
				/>
			</DialogPicture>
			<DialogPicture class="min-w-0 flex-1" :title="__('Share Chart')">
				<VisibilitySelector
					v-model:visibility="rolesVisibility"
					v-model:roles="chartRoles"
				/>
			</DialogPicture>
		</div>

		<DialogPicture
			v-else-if="props.name === 'runAsOwner'"
			class="w-[28rem]"
			:title="__('Share Chart')"
		>
			<div class="flex flex-col gap-4">
				<VisibilitySelector v-model:visibility="publicVisibility" v-model:roles="noRoles">
					<template #actions>
						<Button icon="lucide-link-2" />
					</template>
				</VisibilitySelector>
				<RunAsOwnerField v-model="runsAsOwner" is-public />
			</div>
		</DialogPicture>

		<DialogPicture
			v-else-if="props.name === 'workbookAccess'"
			class="w-[34rem]"
			:title="__('Manage Workbook Access')"
		>
			<OrganizationAccessRow />
			<ShareUserRow
				:full-name="props.person.full_name"
				:email="props.person.email"
				access="edit"
			/>
		</DialogPicture>

		<div v-else-if="props.name === 'numberCards'" class="flex flex-col items-start gap-3">
			<Button variant="outline" class="text-sm">
				<template #prefix>
					<component :is="columnIcon('Date')" class="h-4 w-4" stroke-width="1.5" />
				</template>
				<span class="text-ink-gray-8">{{ __('Posting Date') }}</span>
			</Button>
			<div class="w-56">
				<NumberCard :title="__('Total Sales')" prefix="₹ " :value="1240000" :format="inr" />
			</div>
		</div>
	</div>
</template>
