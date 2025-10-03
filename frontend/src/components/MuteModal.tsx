import React, { useState } from 'react';

interface MuteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (days: number, reason: string) => void;
  riskTitle?: string;
}

export function MuteModal({ isOpen, onClose, onConfirm, riskTitle }: MuteModalProps) {
  const [days, setDays] = useState(7);
  const [reason, setReason] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (days > 0) {
      onConfirm(days, reason);
      onClose();
      setReason('');
      setDays(7);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
          Mute Risk
        </h3>
        
        {riskTitle && (
          <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
            {riskTitle}
          </p>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
              Snooze for (days)
            </label>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-full p-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              required
            >
              <option value={1}>1 day</option>
              <option value={3}>3 days</option>
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
            </select>
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
              Reason (optional)
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g., Working on fix, low priority, false positive..."
              className="w-full p-2 border rounded-md h-20 resize-none dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
            />
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-gray-600 bg-gray-200 hover:bg-gray-300 rounded-md transition-colors dark:bg-gray-600 dark:text-gray-300 dark:hover:bg-gray-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
            >
              Mute Risk
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}