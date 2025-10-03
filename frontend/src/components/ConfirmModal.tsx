import React from 'react';

export default function ConfirmModal({
  open, title, body, confirmText = 'Continue', cancelText = 'Cancel',
  onConfirm, onCancel, confirmDisabled = false,
}: {
  open: boolean; title: string; body?: React.ReactNode;
  confirmText?: string; cancelText?: string;
  onConfirm: () => void; onCancel: () => void;
  confirmDisabled?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[9998] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onCancel} />
      <div className="relative bg-white rounded-xl shadow-xl p-4 w-full max-w-md">
        <div className="text-lg font-semibold text-neutral-900">{title}</div>
        {body && <div className="mt-2 text-sm text-neutral-700">{body}</div>}
        <div className="mt-4 flex justify-end gap-2">
          <button className="px-3 py-1 rounded border" onClick={onCancel}>{cancelText}</button>
          <button
            className={`px-3 py-1 rounded ${confirmDisabled ? 'bg-gray-300 text-gray-600 cursor-not-allowed' : 'bg-black text-white'}`}
            onClick={onConfirm}
            disabled={confirmDisabled}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
