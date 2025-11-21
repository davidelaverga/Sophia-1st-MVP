import { copy } from "./en"

type StringLeaves<T> = {
  [K in keyof T & string]: T[K] extends string
    ? K
    : T[K] extends Array<any>
    ? never
    : T[K] extends object
    ? `${K}.${StringLeaves<T[K]>}`
    : never
}[keyof T & string]

export type CopyKey = StringLeaves<typeof copy>

export const t = (key: CopyKey): string => {
  const value = key.split(".").reduce<any>((acc, segment) => {
    if (acc && typeof acc === "object") {
      return acc[segment]
    }
    return undefined
  }, copy)

  if (typeof value === "string") {
    return value
  }

  if (process.env.NODE_ENV !== "production") {
    console.warn(`[copy] Missing string for key "${key}"`)
  }
  return key
}

export { copy }
