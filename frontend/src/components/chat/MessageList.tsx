import { useEffect, useRef, useCallback } from 'react';
import useJuneStore from '../../stores/useJuneStore';
import MessageBubble from './MessageBubble';

export default function MessageList() {
  const messages = useJuneStore(s => s.mainMessages);
  const showContextMenu = useJuneStore(s => s.showContextMenu);
  const bottomRef = useRef<HTMLDivElement>(null);

  // 自动滚动到最新消息
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleTextSelect = useCallback((selectedText: string, sourceMessageId: string) => {
    const rect = window.getSelection()?.getRangeAt(0)?.getBoundingClientRect();
    const position = {
      x: rect ? rect.right + 10 : window.innerWidth / 2 - 200,
      y: rect ? rect.top : window.innerHeight / 2 - 200,
    };

    showContextMenu({
      x: position.x,
      y: position.y,
      items: [
        {
          label: '复制',
          icon: '📋',
          action: () => {
            navigator.clipboard.writeText(selectedText);
          },
          shortcut: 'Ctrl+C',
        },
        {
          label: '文本追问',
          icon: '💬',
          action: () => {
            const store = useJuneStore.getState();
            const existingFloats = store.floatWindows.filter(
              w => w.source.sourceMessageId === sourceMessageId
            );
            const level = existingFloats.length + 1;

            store.openTextFollowUp({
              selectedText,
              sourceMessageId,
              parentThreadId: 'main',
              level,
              position: {
                x: Math.min(position.x, window.innerWidth - 440),
                y: Math.min(position.y, window.innerHeight - 380),
              },
            });
          },
        },
      ],
    });
  }, [showContextMenu]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-gray-400">
          <div className="text-5xl mb-4">🔵</div>
          <h2 className="text-xl font-semibold text-gray-500 mb-2">June AI 伴学</h2>
          <p className="text-sm">选中任何文本右键追问，让学习不停顿</p>
          <div className="mt-6 flex gap-2 justify-center text-xs text-gray-400">
            <div className="px-3 py-1.5 bg-gray-50 rounded-lg border border-gray-100">
              💬 选中文本 → 右键追问
            </div>
            <div className="px-3 py-1.5 bg-gray-50 rounded-lg border border-gray-100">
              📸 任意位置 → 截图追问
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-3xl mx-auto">
        {messages.map(msg => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onTextSelect={handleTextSelect}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
