import type { ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'
import Modal from './Modal'
import Button from './Button'

interface ConfirmDialogProps {
  open: boolean
  title: string
  message: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  tone?: 'danger' | 'primary'
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

/** Yes/no confirmation for destructive or significant actions. */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  tone = 'primary',
  loading,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      onClose={loading ? () => {} : onCancel}
      size="sm"
      disableBackdropClose={loading}
      icon={tone === 'danger' ? <AlertTriangle className="h-5 w-5" /> : undefined}
      title={title}
      footer={
        <>
          <Button variant="outline" size="sm" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            variant={tone === 'danger' ? 'danger' : 'primary'}
            size="sm"
            onClick={onConfirm}
            loading={loading}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="text-sm leading-relaxed text-slate-600">{message}</div>
    </Modal>
  )
}
