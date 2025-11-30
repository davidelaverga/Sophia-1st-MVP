"use client"

import { useState } from "react"
import { exportPrivacyData, deleteAccountData } from "../../lib/api/privacy"

export function PrivacyPanel() {
  const [status, setStatus] = useState<"idle" | "exporting" | "deleting">("idle")
  const [message, setMessage] = useState<string>()
  const [confirmDelete, setConfirmDelete] = useState(false)

  const handleExport = async () => {
    setStatus("exporting")
    setMessage(undefined)
    try {
      const blob = await exportPrivacyData()
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement("a")
      anchor.href = url
      anchor.download = `sophia-export-${Date.now()}.json`
      anchor.click()
      URL.revokeObjectURL(url)
      setMessage("Your data export is downloading.")
    } catch (err) {
      const message = (err as Error).message || "We couldn’t export your data right now."
      setMessage(message.includes("404") ? "Export endpoint isn’t available yet. Please check with backend." : message)
    } finally {
      setStatus("idle")
    }
  }

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true)
      setMessage("Click delete again to confirm. This cannot be undone.")
      return
    }
    setStatus("deleting")
    setMessage(undefined)
    try {
      await deleteAccountData()
      setMessage("Your account data was deleted. We’ll reload shortly.")
      setTimeout(() => window.location.reload(), 2000)
    } catch (err) {
      const message = (err as Error).message || "We couldn’t delete your data right now."
      setMessage(message.includes("404") ? "Delete endpoint isn’t available yet. Please check with backend." : message)
    } finally {
      setStatus("idle")
      setConfirmDelete(false)
    }
  }

  return (
    <section aria-labelledby="privacy-panel-title" className="rounded-3xl border border-sophia-text/10 bg-sophia-bubble p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p id="privacy-panel-title" className="text-base font-semibold text-sophia-text">
            Privacy
          </p>
          <p className="text-sm text-sophia-text2">You can export or delete your conversations anytime.</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={handleExport}
          disabled={status !== "idle"}
          className="rounded-2xl border border-sophia-text/20 bg-sophia-button px-4 py-3 text-sm font-medium text-sophia-text transition hover:border-sophia-purple/40 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {status === "exporting" ? "Preparing export…" : "Export my data"}
        </button>
        <button
          type="button"
          onClick={handleDelete}
          disabled={status !== "idle"}
          className="rounded-2xl border border-sophia-error/30 bg-sophia-error/15 px-4 py-3 text-sm font-semibold text-sophia-text transition hover:border-sophia-error/50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {status === "deleting" ? "Deleting…" : confirmDelete ? "Confirm delete" : "Delete my account"}
        </button>
      </div>

      {message && <p className="mt-3 text-sm text-sophia-text2">{message}</p>}
    </section>
  )
}



