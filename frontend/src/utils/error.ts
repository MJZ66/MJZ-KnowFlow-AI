/**
 * Unified API error parser.
 * Maps backend {code, message, message_en} responses to user-facing strings.
 */

import { getSavedLanguage } from '../i18n';

export interface ApiErrorBody {
  code?: string;
  message?: string;
  message_en?: string;
  detail?: string;
}

/**
 * Parse an API error into a language-appropriate message.
 *
 * Priority:
 * 1. Backend {message/message_en} based on current language
 * 2. Backend {detail} as fallback
 * 3. Generic fallback message
 */
export function parseApiError(err: unknown): string {
  const lang = getSavedLanguage();
  const isZh = lang === 'zh-CN';

  // If it's a plain Error with a message
  if (err instanceof Error) {
    const msg = err.message;

    // Try to parse as JSON — some errors might be stringified JSON
    try {
      const parsed = JSON.parse(msg) as ApiErrorBody;
      return _formatBody(parsed, isZh);
    } catch {
      // Not JSON — use known error pattern mapping
      return _mapKnownError(msg, isZh);
    }
  }

  // If it's already an object
  if (typeof err === 'object' && err !== null) {
    const body = err as ApiErrorBody;
    return _formatBody(body, isZh);
  }

  // Unknown type — generic fallback
  return isZh ? '操作失败，请稍后重试。' : 'Operation failed. Please try again later.';
}

function _formatBody(body: ApiErrorBody, isZh: boolean): string {
  // Prefer structured message
  if (isZh && body.message) return body.message;
  if (!isZh && body.message_en) return body.message_en;

  // Fallback to detail
  if (body.detail) {
    return _mapKnownError(body.detail, isZh);
  }

  // If we have one message but in wrong language, still use it
  if (body.message) return body.message;
  if (body.message_en) return body.message_en;

  return isZh ? '操作失败，请稍后重试。' : 'Operation failed. Please try again later.';
}

function _mapKnownError(msg: string, isZh: boolean): string {
  const lower = msg.toLowerCase();

  // Common error patterns → user-friendly messages
  const patterns: Array<[RegExp, string, string]> = [
    [/current password is incorrect/i,
      '当前密码不正确，请重试。',
      'Current password is incorrect. Please try again.'],
    [/new password must be different/i,
      '新密码不能与当前密码相同。',
      'New password must be different from the current password.'],
    [/invalid.*(email|password|credentials)/i,
      '邮箱或密码错误，请检查后重试。',
      'Invalid email or password. Please check and try again.'],
    [/not authenticated/i,
      '未登录或登录已过期，请重新登录。',
      'Not authenticated. Please sign in again.'],
    [/token.*(invalid|expired)/i,
      '登录凭证无效或已过期，请重新登录。',
      'Session expired. Please sign in again.'],
    [/email.*(exists|already|registered)/i,
      '该邮箱已被注册。',
      'This email is already registered.'],
    [/not found/i,
      '请求的资源不存在。',
      'The requested resource was not found.'],
    [/permission denied/i,
      '无权限执行此操作。',
      'Permission denied.'],
    [/file.*(large|size)/i,
      '文件大小超过限制。',
      'File size exceeds the limit.'],
    [/unsupported.*(file|type)/i,
      '不支持的文件类型。',
      'Unsupported file type.'],
    [/limit.*reach/i,
      '已达到数量上限。',
      'Limit reached.'],
    [/failed/i,
      '操作失败，请稍后重试。',
      'Operation failed. Please try again later.'],
    [/internal server error/i,
      '服务器内部错误，请稍后重试。',
      'Internal server error. Please try again later.'],
  ];

  for (const [regex, zh, en] of patterns) {
    if (regex.test(msg)) {
      return isZh ? zh : en;
    }
  }

  // No pattern match — return original message
  return msg;
}
