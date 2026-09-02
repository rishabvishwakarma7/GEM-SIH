/**
 * Tiny classname combiner — joins truthy class fragments with a space.
 * Keeps component call sites readable without pulling in an extra dependency.
 */
export type ClassValue = string | number | false | null | undefined

export function cn(...values: ClassValue[]): string {
  return values.filter(Boolean).join(' ')
}
