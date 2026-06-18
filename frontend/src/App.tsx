import { useEffect, useCallback } from 'react';
import useJuneStore from './stores/useJuneStore';
import Header from './components/layout/Header';
import MessageList from './components/chat/MessageList';
import InputBar from './components/chat/InputBar';
import FloatWindowLayer from './components/float/FloatWindowLayer';
import ContextMenu from './components/menu/ContextMenu';
import ScreenshotOverlay from './components/ScreenshotOverlay';
import ErrorBoundary from './components/ErrorBoundary';

export default function App() {
  const createSession = useJuneStore(s => s.createSession);
  const currentSessionId = useJuneStore(s => s.currentSessionId);
  const sessions = useJuneStore(s => s.sessions);
  const hideContextMenu = useJuneStore(s => s.hideContextMenu);
  const isScreenshotMode = useJuneStore(s => s.isScreenshotMode);

  // 自动创建默认会话
  useEffect(() => {
    if (sessions.length === 0) {
      createSession();
    }
  }, [sessions.length, createSession]);

  // 全局点击关闭右键菜单
  const handleGlobalClick = useCallback(() => {
    hideContextMenu();
  }, [hideContextMenu]);

  // 全局右键菜单（未选中文本时的截图追问入口）
  const handleGlobalContextMenu = useCallback((e: MouseEvent) => {
    const selection = window.getSelection();
    const selectedText = selection?.toString().trim();

    // 如果有选中文本，让 MessageBubble 处理
    if (selectedText) return;

    // 检查是否在输入框或悬浮窗内
    const target = e.target as HTMLElement;
    if (
      target.closest('input, textarea, [contenteditable]') ||
      target.closest('[data-float-window]')
    ) return;

    e.preventDefault();
    const store = useJuneStore.getState();
    store.showContextMenu({
      x: e.clientX,
      y: e.clientY,
      items: [
        {
          label: '截图追问',
          icon: '📸',
          action: () => {
            store.enterScreenshotMode();
          },
        },
      ],
    });
  }, []);

  useEffect(() => {
    document.addEventListener('contextmenu', handleGlobalContextMenu);
    return () => document.removeEventListener('contextmenu', handleGlobalContextMenu);
  }, [handleGlobalContextMenu]);

  return (
    <ErrorBoundary name="app-root">
      <div
        className="h-screen flex flex-col bg-gray-50"
        onClick={handleGlobalClick}
      >
        <Header />

        {/* 主内容区 */}
        <ErrorBoundary name="main-chat-panel">
          <div className="flex-1 flex overflow-hidden">
            {/* 聊天区 */}
            <div className="flex-1 flex flex-col overflow-hidden">
              <MessageList />
              <InputBar />
            </div>
          </div>
        </ErrorBoundary>

        {/* 悬浮窗层（每个 FloatWindow 内部独立包裹 ErrorBoundary） */}
        <FloatWindowLayer />

        {/* 右键菜单 */}
        <ContextMenu />

        {/* 截图覆盖层 */}
        {isScreenshotMode && <ScreenshotOverlay />}
      </div>
    </ErrorBoundary>
  );
}
