'use client';

import { useCallback, useState } from 'react';
import { clsx } from 'clsx';

interface Props {
  onFile: (file: File) => void;
  disabled?: boolean;
}

export function AudioDropzone({ onFile, disabled = false }: Props) {
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleFile = useCallback(
    (file: File) => {
      setFileName(file.name);
      onFile(file);
    },
    [onFile],
  );

  return (
    <label
      className={clsx(
        'flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-8 py-14 text-center transition-colors',
        dragging
          ? 'border-violet-400 bg-violet-50'
          : 'border-slate-300 bg-slate-50 hover:border-slate-400',
        disabled && 'cursor-not-allowed opacity-50',
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const f = e.dataTransfer.files[0];
        if (f) handleFile(f);
      }}
    >
      <input
        type="file"
        accept="audio/*"
        className="sr-only"
        disabled={disabled}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
      />
      <p className="text-2xl">🎙</p>
      {fileName ? (
        <p className="mt-2 text-sm text-slate-700">{fileName}</p>
      ) : (
        <>
          <p className="mt-2 text-sm font-medium text-slate-700">Drop audio here or click to browse</p>
          <p className="mt-1 text-xs text-slate-400">MP3, M4A, WAV — max 25 MB</p>
        </>
      )}
    </label>
  );
}
