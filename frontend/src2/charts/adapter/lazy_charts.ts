// The adapters import these lazily through this module instead of
// `import('frappe-ui/charts')`. Rolldown keeps a barrel that is also imported
// statically, with every chart it re-exports, in the eager chunk.
export { DonutChart, FunnelChart, HeatmapChart, SankeyChart, ScatterChart } from 'frappe-ui/charts'
