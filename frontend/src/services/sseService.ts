import type { FollowUpRequest } from '../types';

const API_BASE = 'http://localhost:8000/api';

export interface SSEServiceConfig {
  /** SSE 请求超时时间（毫秒），默认 600000（10 分钟） */
  timeoutMs: number;
  /** 重试次数，默认 3 */
  maxRetries: number;
  /** 基础重试延迟（毫秒），默认 1000 */
  retryBaseDelayMs: number;
  /** 最大重试延迟（毫秒），默认 30000 */
  retryMaxDelayMs: number;
}

const DEFAULT_CONFIG: SSEServiceConfig = {
  timeoutMs: 600_000,
  maxRetries: 3,
  retryBaseDelayMs: 1000,
  retryMaxDelayMs: 30_000,
};

/** 从 localStorage 获取 API Token */
function getToken(): string {
  return localStorage.getItem('june_api_token') || '';
}

/** 设置 API Token */
export function setApiToken(token: string): void {
  localStorage.setItem('june_api_token', token);
}

class SSEService {
  private apiBase: string;
  private config: SSEServiceConfig;

  constructor(baseUrl?: string, config?: Partial<SSEServiceConfig>) {
    this.apiBase = baseUrl ?? API_BASE;
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  setBaseUrl(url: string) {
    this.apiBase = url;
  }

  async sendChatMessage(
    sessionId: string,
    message: string,
    onDelta: (delta: string) => void,
    onReferences?: (files: any[]) => void,
  ): Promise<void> {
    return this.streamRequestWithRetry(
      `${this.apiBase}/sessions/${sessionId}/chat`,
      { message },
      onDelta,
      onReferences,
    );
  }

  async sendFollowUp(
    request: FollowUpRequest,
    onDelta: (delta: string) => void,
    onReferences?: (files: any[]) => void,
  ): Promise<void> {
    return this.streamRequestWithRetry(
      `${this.apiBase}/sessions/${request.session_id}/follow-up`,
      request,
      onDelta,
      onReferences,
    );
  }

  /**
   * 验证 Token 是否有效
   */
  async verifyToken(token: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.apiBase}/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * 带重试的 SSE 流式请求。
   */
  private async streamRequestWithRetry(
    url: string,
    body: any,
    onDelta: (delta: string) => void,
    onReferences?: (files: any[]) => void,
  ): Promise<void> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.config.maxRetries; attempt++) {
      try {
        await this.streamRequest(url, body, onDelta, onReferences);
        return;
      } catch (e: any) {
        lastError = e;
        if (e.name === 'AbortError') return;

        if (attempt < this.config.maxRetries) {
          const delay = Math.min(
            this.config.retryBaseDelayMs * Math.pow(2, attempt),
            this.config.retryMaxDelayMs,
          );
          console.warn(`[SSEService] 请求失败，${delay}ms 后重试 (${attempt + 1}/${this.config.maxRetries}):`, e.message);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError || new Error('SSE 请求失败，已达最大重试次数');
  }

  private async streamRequest(
    url: string,
    body: any,
    onDelta: (delta: string) => void,
    onReferences?: (files: any[]) => void,
  ): Promise<void> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeoutMs);

    const token = getToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (response.status === 401) {
        throw new Error('认证失败，请检查 API Token 是否正确');
      }

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (line === 'data: : heartbeat' || line.trim() === ': heartbeat') continue;

          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.delta) {
                onDelta(data.delta);
              }
              if (data.error) {
                console.error('[SSE] Server error:', data.error);
                onDelta(`\n\n[错误] ${data.error}`);
              }
              if (data.files && onReferences) {
                onReferences(data.files);
              }
            } catch {
              // 跳过格式错误的行
            }
          }
        }
      }
    } finally {
      clearTimeout(timeoutId);
    }
  }
}

export const sseService = new SSEService();
export default sseService;
