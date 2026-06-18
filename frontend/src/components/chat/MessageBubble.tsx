import { useRef, useCallback } from 'react';
import type { Message } from '../../types';
import FloatManager from '../../utils/floatManager';
import useJuneStore from '../../stores/useJuneStore';

interface MessageBubbleProps {
  message: Message;
  onTextSelect?: (text: string, messageId: string) => void;
}

export default function MessageBubble({ message, onTextSelect }: MessageBubbleProps) {
  const bubbleRef = useRef<HTMLDivElement>(null);
  const floatWindows = useJuneStore(s => s.floatWindows);
  const openTextFollowUp = useJuneStore(s => s.openTextFollowUp);

  const isUser = message.role === 'user';

  // 获取该消息的追问链
  const followUpChain = FloatManager.getFollowUpChain(message.id, floatWindows);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    const selection = window.getSelection();
    const selectedText = selection?.toString().trim();

    if (selectedText && bubbleRef.current?.contains(selection?.anchorNode)) {
      e.preventDefault();
      onTextSelect?.(selectedText, message.id);
    }
  }, [message.id, onTextSelect]);

  const handleFollowUpClick = (threadId: string) => {
    // 聚焦对应的悬浮窗
    useJuneStore.getState().bringToFront(threadId);
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className="max-w-[80%]">
        {!isUser && (
          <div className="flex items-center gap-2 mb-1 ml-1">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white text-xs font-bold">
              J
            </div>
            <span className="text-xs text-gray-500">June AI</span>
          </div>
        )}
        <div
          ref={bubbleRef}
          onContextMenu={handleContextMenu}
          className={`select-text rounded-xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? 'bg-blue-500 text-white rounded-br-md'
              : 'bg-white border border-gray-200 text-gray-800 rounded-bl-md shadow-sm'
          }`}
        >
          {message.content ? (
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            <div className="flex items-center gap-1 text-gray-400">
              <span className="animate-pulse">●</span>
              <span className="animate-pulse" style={{ animationDelay: '0.2s' }}>●</span>
              <span className="animate-pulse" style={{ animationDelay: '0.4s' }}>●</span>
            </div>
          )}

          {/* 资料库引用 */}
          {message.references && message.references.length > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-100">
              {message.references.map((ref, i) => (
                <div key={i} className="text-xs text-gray-400 flex items-center gap-1">
                  <span>📎</span>
                  <span>来自: {ref.fileName}{ref.page ? ` (第${ref.page}页)` : ''}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 追问链指示器 */}
        {followUpChain.length > 0 && (
          <div className="mt-1 ml-1 flex flex-col gap-0.5">
            {followUpChain.map(chain => (
              <button
                key={chain.threadId}
                onClick={() => handleFollowUpClick(chain.threadId)}
                className={`text-xs px-2 py-0.5 rounded-full inline-flex items-center gap-1 w-fit hover:opacity-80 transition-opacity ${
                  chain.level === 1 ? 'bg-blue-50 text-blue-600' :
                  chain.level === 2 ? 'bg-purple-50 text-purple-600' :
                  'bg-orange-50 text-orange-600'
                }`}
              >
                <span className="font-bold">L{chain.level}</span>
                <span>追问: {chain.summary}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
