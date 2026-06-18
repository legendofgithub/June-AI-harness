import { useState, useCallback, useRef } from 'react';
import useJuneStore from '../stores/useJuneStore';

export default function ScreenshotOverlay() {
  const [isSelecting, setIsSelecting] = useState(false);
  const [selection, setSelection] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const startRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const overlayRef = useRef<HTMLDivElement>(null);

  const exitScreenshotMode = useJuneStore(s => s.exitScreenshotMode);
  const openScreenshotFollowUp = useJuneStore(s => s.openScreenshotFollowUp);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (e.target === overlayRef.current) {
      setIsSelecting(true);
      startRef.current = { x: e.clientX, y: e.clientY };
      setSelection({ x: e.clientX, y: e.clientY, w: 0, h: 0 });
    }
  }, []);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!isSelecting) return;
    const x = Math.min(startRef.current.x, e.clientX);
    const y = Math.min(startRef.current.y, e.clientY);
    const w = Math.abs(e.clientX - startRef.current.x);
    const h = Math.abs(e.clientY - startRef.current.y);
    setSelection({ x, y, w, h });
  }, [isSelecting]);

  const handlePointerUp = useCallback(async () => {
    if (!isSelecting || !selection || selection.w < 20 || selection.h < 20) {
      setIsSelecting(false);
      return;
    }

    setIsSelecting(false);

    try {
      // 使用 html2canvas 方式截图（简化版：直接用 canvas 从 body）
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // 使用简单的截图方式：暂时截取整个 viewport
      // 在生产环境中应使用 html2canvas 库
      const scale = window.devicePixelRatio || 1;
      canvas.width = selection.w * scale;
      canvas.height = selection.h * scale;
      ctx.scale(scale, scale);

      // 创建临时浮层提示
      const base64 = canvas.toDataURL('image/png');

      openScreenshotFollowUp({
        screenshotBase64: base64,
        sourceMessageId: 'screenshot_' + Date.now(),
        parentThreadId: 'main',
        level: 1,
        position: {
          x: Math.min(selection.x + selection.w + 10, window.innerWidth - 440),
          y: Math.min(selection.y, window.innerHeight - 420),
        },
      });
    } catch (err) {
      console.error('Screenshot failed:', err);
    }

    exitScreenshotMode();
  }, [isSelecting, selection, exitScreenshotMode, openScreenshotFollowUp]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      exitScreenshotMode();
    }
  }, [exitScreenshotMode]);

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-[9998]"
      style={{ cursor: 'crosshair' }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      autoFocus
    >
      {/* 背景遮罩 */}
      <div className="absolute inset-0 bg-black/30" />

      {/* 选中区域 */}
      {selection && selection.w > 0 && selection.h > 0 && (
        <div
          className="absolute bg-white/10 border-2 border-blue-400 rounded-sm"
          style={{
            left: selection.x,
            top: selection.y,
            width: selection.w,
            height: selection.h,
          }}
        >
          <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-blue-500 text-white text-xs px-2 py-0.5 rounded whitespace-nowrap">
            {selection.w} × {selection.h}
          </div>
        </div>
      )}

      {/* 提示 */}
      {!isSelecting && !selection && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white text-center">
          <div className="text-4xl mb-3">📸</div>
          <div className="text-lg font-medium">拖拽框选要追问的区域</div>
          <div className="text-sm text-white/70 mt-1">按 ESC 取消</div>
        </div>
      )}
    </div>
  );
}
