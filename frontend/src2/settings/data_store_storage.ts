import { __ } from '../translation'

export type ColumnReader = {
	doctype: string
	name: string
	title: string
	workbook: string | null
}

export type StoredColumn = {
	name: string
	bytes: number
	readers: ColumnReader[]
	skipped: boolean
	skippable: boolean
	in_use: boolean
}

export type StoredTable = {
	name: string
	data_source: string
	table: string
	label: string
	sync_mode: 'Full' | 'Incremental'
	bytes: number
	read_bytes: number
	unread_bytes: number
	rows: number
	measured_on: string
	last_read_on: string | null
	unread: boolean
	columns: StoredColumn[]
}

export type StorageGroupKey =
	| 'read'
	| 'unread_columns'
	| 'unread_tables'
	| 'cleanup'
	| 'other'
	| 'free'

export type DataStoreStorage = {
	measured_on: string | null
	measuring: boolean
	file_bytes: number
	free_bytes: number | null
	unread_days: number
	usage_known: boolean
	cleanup: { stopped: boolean; stopped_on: string | null; last_run: string | null }
	groups: Record<StorageGroupKey, number>
	tables: StoredTable[]
	cleanup_tables: CleanupTable[]
}

export type CleanupReason = 'not_stored' | 'leftover' | 'empty' | 'legacy'

export type CleanupTable = {
	schema: string
	table: string
	bytes: number
	reason: CleanupReason
}

export type BarSegment = {
	key: StorageGroupKey
	label: string
	value: number
	class: string
	tooltip: string
}

export type GiveBackItem =
	| { kind: 'table'; table: StoredTable; bytes: number }
	| { kind: 'column'; table: StoredTable; column: StoredColumn; bytes: number }

const KB = 1024
const MB = KB * 1024
const GB = MB * 1024

export function formatBytes(bytes: number): string {
	if (bytes >= GB) return `${(bytes / GB).toFixed(1)} GB`
	if (bytes >= MB) return `${(bytes / MB).toFixed(bytes < 10 * MB ? 1 : 0)} MB`
	if (bytes > 0) return `${Math.ceil(bytes / KB)} KB`
	return '0 MB'
}

const GROUP_CLASS: Record<StorageGroupKey, string> = {
	read: 'bg-surface-blue-6',
	unread_columns: 'bg-surface-amber-5',
	unread_tables: 'bg-surface-red-5',
	cleanup: 'bg-surface-violet-5',
	other: 'bg-surface-gray-5',
	free: 'bg-surface-gray-3',
}

function groupLabel(key: StorageGroupKey, unreadDays: number): string {
	return {
		read: __('Read by queries'),
		unread_columns: __('Columns no query reads'),
		unread_tables: __('Tables not read in {0} days', String(unreadDays)),
		cleanup: __('Cleanup removes'),
		other: __('Other'),
		free: __('Free'),
	}[key]
}

export function groupSegment(key: StorageGroupKey, bytes: number, unreadDays: number): BarSegment {
	const label = groupLabel(key, unreadDays)
	return {
		key,
		label,
		value: bytes,
		class: GROUP_CLASS[key],
		tooltip: `${label}: ${formatBytes(bytes)}`,
	}
}

export function storageSegments(storage: DataStoreStorage): BarSegment[] {
	return (Object.keys(GROUP_CLASS) as StorageGroupKey[])
		.map((key) => groupSegment(key, storage.groups[key] || 0, storage.unread_days))
		.filter((segment) => segment.value > 0)
}

export function tableSegments(storage: DataStoreStorage, table: StoredTable): BarSegment[] {
	const unreadKey = table.unread ? 'unread_tables' : 'unread_columns'
	return [
		groupSegment('read', table.read_bytes, storage.unread_days),
		groupSegment(unreadKey, table.unread_bytes, storage.unread_days),
	].filter((s) => s.value > 0)
}

export function columnClass(table: StoredTable, column: StoredColumn): string {
	if (table.unread) return GROUP_CLASS.unread_tables
	return column.in_use ? GROUP_CLASS.read : GROUP_CLASS.unread_columns
}

export function cleanupReason(reason: CleanupReason): string {
	return {
		not_stored: __('No longer stored'),
		leftover: __('Left by an interrupted import'),
		empty: __('Empty'),
		legacy: __('Copy from before the schema move'),
	}[reason]
}

export function giveBackItems(storage: DataStoreStorage): GiveBackItem[] {
	const items: GiveBackItem[] = []
	for (const table of storage.tables) {
		if (table.unread) {
			items.push({ kind: 'table', table, bytes: table.bytes })
			continue
		}
		for (const column of table.columns) {
			if (!column.in_use && column.skippable && !column.skipped && column.bytes) {
				items.push({ kind: 'column', table, column, bytes: column.bytes })
			}
		}
	}
	return items.sort((a, b) => b.bytes - a.bytes)
}

export function columnsBySize(table: StoredTable): StoredColumn[] {
	return [...table.columns].sort((a, b) => b.bytes - a.bytes)
}
