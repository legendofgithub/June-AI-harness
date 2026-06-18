import { useState, useRef, useCallback } from 'react';
import { Send, Paperclip, Image } from 'lucide-react';
import useJuneStore from '../../stores/useJuneStore';

export default function InputBar() {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const sendMessage = useJuneStore(s => s.sendMessage);
  const isStreaming = useJuneStore(s => s.isStreaming);
  const uploadFile = useJuneStore(s => s.uploadFile);
  const enterScreenshotMode = useJuneStore(s => s.enterScreenshotMode);
  const isScreenshotMode = useJuneStore(s => s.isScreenshotMode);

  const handleSend = useCallback(() => {
    if (!input.trim() || isStreaming) return;
    sendMessage(input);
    setInput('');
    // 重置 textarea 高度
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [input, isStreaming, sendMessage]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadFile(file);
    }
    e.target.value = '';
  }, [uploadFile]);

  const handleInput = useCallback(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    }
  }, []);

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2 bg-gray-50 rounded-2xl border border-gray-200 px-4 py-2 focus-within:border-blue-300 focus-within:ring-2 focus-within:ring-blue-100 transition-all">
          {/* 文件上传按钮 */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title="上传文件"
          >
            <Paperclip size={18} />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileUpload}
            className="hidden"
            accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md,.png,.jpg,.jpeg,.webp,.gif"
          />

          {/* 截图追问按钮 */}
          <button
            onClick={enterScreenshotMode}
            className={`p-2 rounded-lg transition-colors ${
              isScreenshotMode
                ? 'text-blue-500 bg-blue-50'
                : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
            }`}
            title="截图追问"
          >
            <Image size={18} />
          </button>

          {/* 输入框 */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="输入问题，或选中任意文本右键追问..."
            rows={1}
            className="flex-1 bg-transparent resize-none outline-none text-sm py-1.5 max-h-[200px] placeholder:text-gray-400"
            disabled={isStreaming}
          />

          {/* 发送按钮 */}
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className={`p-2 rounded-lg transition-all ${
              input.trim() && !isStreaming
                ? 'bg-blue-500 text-white hover:bg-blue-600 shadow-sm'
                : 'text-gray-300 cursor-not-allowed'
            }`}
          >
            <Send size={18} />
          </button>
        </div>

        {isScreenshotMode && (
          <div className="mt-2 text-xs text-blue-500 bg-blue-50 rounded-lg px-3 py-1.5 text-center">
            📸 截图模式已开启 — 点击并拖拽框选追问区域，按 ESC 取消
          </div>
        )}
      </div>
    </div>
  );
}
