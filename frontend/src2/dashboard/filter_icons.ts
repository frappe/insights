// The icons a dashboard filter can wear.
//
// Lucide ships more than 1500 glyphs, and frappe-ui only serves the whole pack
// through a 468 kB sprite that a plugin injects into `document.body` — which a
// desk island's shadow root cannot reach. A filter names a column, so a few
// dozen glyphs cover what an author ever reaches for.
//
// Every name is spelled out here in full. Tailwind's JIT emits a `lucide-*`
// class only where it reads that literal in source, so a name built at runtime
// draws an empty box.

export type FilterIconGroup = {
	label: string
	icons: string[]
}

export const FILTER_ICON_GROUPS: FilterIconGroup[] = [
	{
		label: 'Data',
		icons: [
			'lucide-type',
			'lucide-hash',
			'lucide-percent',
			'lucide-calculator',
			'lucide-binary',
			'lucide-list',
			'lucide-list-checks',
			'lucide-table',
			'lucide-columns-3',
			'lucide-database',
			'lucide-filter',
			'lucide-sliders-horizontal',
		],
	},
	{
		label: 'Time',
		icons: [
			'lucide-calendar',
			'lucide-calendar-days',
			'lucide-calendar-range',
			'lucide-clock',
			'lucide-history',
			'lucide-hourglass',
			'lucide-timer',
			'lucide-sun',
			'lucide-moon',
		],
	},
	{
		label: 'People',
		icons: [
			'lucide-user',
			'lucide-users',
			'lucide-user-check',
			'lucide-contact',
			'lucide-id-card',
			'lucide-briefcase',
			'lucide-building',
			'lucide-building-2',
			'lucide-handshake',
			'lucide-graduation-cap',
		],
	},
	{
		label: 'Place',
		icons: [
			'lucide-map-pin',
			'lucide-map',
			'lucide-globe',
			'lucide-flag',
			'lucide-compass',
			'lucide-navigation',
			'lucide-route',
			'lucide-house',
			'lucide-truck',
			'lucide-plane',
			'lucide-car',
		],
	},
	{
		label: 'Money',
		icons: [
			'lucide-dollar-sign',
			'lucide-banknote',
			'lucide-credit-card',
			'lucide-wallet',
			'lucide-receipt',
			'lucide-coins',
			'lucide-piggy-bank',
			'lucide-trending-up',
			'lucide-trending-down',
			'lucide-chart-line',
			'lucide-chart-bar',
			'lucide-chart-pie',
		],
	},
	{
		label: 'Commerce',
		icons: [
			'lucide-shopping-cart',
			'lucide-shopping-bag',
			'lucide-package',
			'lucide-boxes',
			'lucide-warehouse',
			'lucide-factory',
			'lucide-store',
			'lucide-barcode',
			'lucide-qr-code',
			'lucide-ticket',
		],
	},
	{
		label: 'Status',
		icons: [
			'lucide-circle-check',
			'lucide-circle-x',
			'lucide-circle-alert',
			'lucide-circle-help',
			'lucide-check',
			'lucide-x',
			'lucide-star',
			'lucide-heart',
			'lucide-flame',
			'lucide-zap',
			'lucide-activity',
			'lucide-gauge',
			'lucide-target',
			'lucide-award',
		],
	},
	{
		label: 'Objects',
		icons: [
			'lucide-tag',
			'lucide-tags',
			'lucide-bookmark',
			'lucide-folder',
			'lucide-file',
			'lucide-file-text',
			'lucide-layers',
			'lucide-book',
			'lucide-key',
			'lucide-lock',
			'lucide-shield',
			'lucide-eye',
			'lucide-link',
			'lucide-image',
			'lucide-palette',
			'lucide-wrench',
			'lucide-settings',
			'lucide-search',
		],
	},
	{
		label: 'Systems',
		icons: [
			'lucide-server',
			'lucide-cpu',
			'lucide-git-branch',
			'lucide-workflow',
			'lucide-mail',
			'lucide-phone',
			'lucide-message-square',
			'lucide-bell',
			'lucide-send',
			'lucide-thermometer',
			'lucide-droplet',
			'lucide-leaf',
			'lucide-stethoscope',
		],
	},
]

const KNOWN_ICONS = new Set(FILTER_ICON_GROUPS.flatMap((group) => group.icons))

/**
 * The class that draws `icon`, or nothing when this build cannot draw it.
 *
 * A stored icon is a class name. Filters authored against the sprite hold a
 * bare lucide name instead, so those are read as one. Either way a name the
 * curated list drops has no CSS behind it, and the caller draws its fallback
 * rather than an empty box.
 */
export function filterIconClass(icon?: string): string | undefined {
	if (!icon) return undefined
	const className = icon.startsWith('lucide-') ? icon : `lucide-${icon}`
	return KNOWN_ICONS.has(className) ? className : undefined
}

export function filterIconLabel(className: string): string {
	return className
		.slice('lucide-'.length)
		.replace(/-/g, ' ')
		.replace(/\b\w/g, (c) => c.toUpperCase())
}
