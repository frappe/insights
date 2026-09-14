// The one writer of what a row dragged out of the workbook sidebar carries.
// `DashboardBuilder.onDrop` is its only reader.
export function setDraggedItem(dataTransfer: DataTransfer, type: string, item: any) {
	// A drop whose effect the drag did not allow never fires: dropping on a
	// dashboard copies the item, dragging inside the sidebar moves it, and
	// Sortable allows `move` alone.
	dataTransfer.effectAllowed = 'copyMove'
	dataTransfer.setData('text/plain', JSON.stringify({ type, item }))
}
