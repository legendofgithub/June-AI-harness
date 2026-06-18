import { useRef, useCallback, useEffect } from 'react';

/**
 * SSE 自定义事件类型映射
 * EventSource 只原生支持 "open" / "message" / "error"，
 * 我们用 onmessage 接收 data-only 格式的事件，通过 type 字段分发。
 */
export interface SSEData {
  delta?: string;
  type?: string;
  thread_id?: string;
  error?: string;
  files?: any[];
  usage?: any;
}

export interface SSEReconnectConfig {
  /** 最大重试次数，默认 3 */
  maxRetries?: number;
  /** 基础延迟（毫秒），默认 1000 */
  baseDelayMs?: number;
  /** 最大延迟（毫秒），默认 30000 */
  maxDelayMs?: number;
  /** 重置计数窗口（毫秒），默认 120000。稳定运行超过此时间后重置重试计数 */
  resetWindowMs?: number;
}

const DEFAULT_CONFIG: Required<SSEReconnectConfig> = {
  maxRetries: 3,
  baseDelayMs: 1000,
  maxDelayMs: 30000,
  resetWindowMs: 120_000,
};

/**
 * useSSE —— SSE 连接管理 Hook
 *
 * 替项目中原有的裸 fetch+ReadableStream 方案，使用 EventSource API。
 * 内置：指数退避重连、心跳检测、错误降级。
 *
 * 用法:
 *   const { retry, retryCount } = useSSE(
 *     url,
 *     onMessage,
 *     onDone,
 *     onError,
 *     { maxRetries: 3 }
 *   );
 */
export function useSSE(
  url: string | null,
  onMessage: (data: SSEData) => void,
  onDone?: (threadId?: string) => void,
  onError?: (msg: string, retryable: boolean) => void,
  config?: SSEReconnectConfig,
) {
  const cfg = { ...DEFAULT_CONFIG, ...config };

  const retryCountRef = useRef(0);
  const lastSuccessRef = useRef(Date.now());
  const eventSourceRef = useRef<EventSource | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 用 ref 保存回调，避免 connect 在每次渲染时重建
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  const connect = useCallback(() => {
    if (!url) return;
    if (retryCountRef.current >= cfg.maxRetries) {
      onErrorRef.current?.('SSE 连接失败，已达最大重试次数。请刷新页面。', false);
      return;
    }

    // 关闭旧连接
    eventSourceRef.current?.close();
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }

    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onmessage = (event: MessageEvent) => {
      // 心跳：SSE 注释行以 ":" 开头，EventSource 不会触发 onmessage，
      // 但如果后端用 data: 格式发心跳，我们需要忽略
      if (!event.data || event.data.startsWith(': heartbeat')) {
        retryCountRef.current = 0;
        lastSuccessRef.current = Date.now();
        return;
      }

      retryCountRef.current = 0;
      lastSuccessRef.current = Date.now();

      try {
        const data = JSON.parse(event.data) as SSEData;
        onMessageRef.current(data);

        // 处理内嵌的 done/error
        if (data.type === 'done' || data.thread_id) {
          // done 信号由 SSE 流的 data 内容承载（event: done, data: {...}），
          // EventSource 不区分 event type，统一走 onmessage，需要手动检查
        }
      } catch {
        // 不是 JSON，可能是纯文本 delta
        onMessageRef.current({ delta: event.data, type: 'text' });
      }
    };

    es.addEventListener('done', () => {
      es.close();
      if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
      onDoneRef.current?.();
    });

    es.addEventListener('timeout', () => {
      es.close();
      if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
      onErrorRef.current?.('追问线程超时，已自动关闭。', false);
    });

    es.addEventListener('error', (event: Event) => {
      es.close();
      if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);

      // 稳定运行超过重置窗口且重试计数 > 0 → 重置计数
      const stableDuration = Date.now() - lastSuccessRef.current;
      if (stableDuration > cfg.resetWindowMs && retryCountRef.current > 0) {
        retryCountRef.current = 0;
      }

      const delay = Math.min(
        cfg.baseDelayMs * Math.pow(2, retryCountRef.current),
        cfg.maxDelayMs,
      );
      retryCountRef.current += 1;

      setTimeout(() => connect(), delay);
    });

    // 心跳检测：超过重置窗口无任何消息，视为连接僵死
    heartbeatTimerRef.current = setInterval(() => {
      if (Date.now() - lastSuccessRef.current > cfg.resetWindowMs) {
        es.close();
        if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
        setTimeout(() => connect(), cfg.baseDelayMs);
      }
    }, 30_000);

  }, [url, cfg.maxRetries, cfg.baseDelayMs, cfg.maxDelayMs, cfg.resetWindowMs]);

  useEffect(() => {
    if (url) {
      connect();
    }
    return () => {
      eventSourceRef.current?.close();
      if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
    };
  }, [connect, url]);

  return {
    /** 手动触发重连 */
    retry: connect,
    /** 当前重试次数 */
    retryCount: retryCountRef.current,
  };
}
