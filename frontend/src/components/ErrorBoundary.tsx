import React, { Component, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** 边界标识，用于日志定位 */
  name: string;
  /** 自定义降级 UI，不提供则使用默认 */
  fallback?: ReactNode;
  /** 错误回调 */
  onError?: (error: Error, name: string) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * ErrorBoundary —— React 错误边界
 *
 * 每个 FloatWindow、ChatPanel、FilePanel 独立包裹。
 * 一个窗口/面板崩溃不会导致整个应用白屏。
 *
 * 用法:
 *   <ErrorBoundary name="float-window-L1">
 *     <FloatWindow ... />
 *   </ErrorBoundary>
 */
export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    this.props.onError?.(error, this.props.name);
    console.error(`[ErrorBoundary:${this.props.name}]`, error);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // 默认降级 UI
      return (
        <div
          style={{
            padding: '16px',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            background: '#fef2f2',
            fontSize: '14px',
          }}
        >
          <p style={{ margin: '0 0 8px 0', color: '#991b1b' }}>
            ⚠️ 该窗口出现异常，已自动隔离。
          </p>
          <p style={{ margin: '0 0 12px 0', color: '#6b7280', fontSize: '12px' }}>
            {this.state.error?.message || '未知错误'}
          </p>
          <button
            onClick={this.handleRetry}
            style={{
              padding: '4px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              background: '#fff',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            尝试恢复
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
