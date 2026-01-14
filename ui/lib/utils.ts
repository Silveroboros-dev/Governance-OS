import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Format date helper
export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Format relative time
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return formatDate(dateString)
}

// Severity badge colors (no ranking - just categorical colors)
export function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'bg-red-500 text-white hover:bg-red-600'
    case 'high':
      return 'bg-orange-500 text-white hover:bg-orange-600'
    case 'medium':
      return 'bg-yellow-500 text-black hover:bg-yellow-600'
    case 'low':
      return 'bg-blue-500 text-white hover:bg-blue-600'
    default:
      return 'bg-gray-500 text-white hover:bg-gray-600'
  }
}

// Status badge colors
export function getStatusColor(status: string): string {
  switch (status) {
    case 'open':
      return 'bg-green-500 text-white hover:bg-green-600'
    case 'resolved':
      return 'bg-gray-500 text-white hover:bg-gray-600'
    case 'dismissed':
      return 'bg-gray-400 text-white hover:bg-gray-500'
    default:
      return 'bg-gray-500 text-white hover:bg-gray-600'
  }
}
