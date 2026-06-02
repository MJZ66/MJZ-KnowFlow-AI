// ============================================
// Auth
// ============================================
export interface User {
  id: number;
  email: string;
  username: string;
  role: 'user' | 'admin' | 'super_admin';
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ============================================
// Knowledge Base
// ============================================
export interface KnowledgeBase {
  id: number;
  user_id: number;
  name: string;
  description: string;
  visibility: 'private' | 'team' | 'public';
  created_at: string;
  updated_at: string;
}

export interface KBMember {
  id: number;
  knowledge_base_id: number;
  user_id: number;
  role: 'owner' | 'editor' | 'viewer';
  created_at: string;
}

// ============================================
// Document
// ============================================
export type DocumentStatus =
  | 'uploaded'
  | 'parsing'
  | 'chunking'
  | 'embedding'
  | 'completed'
  | 'failed';

export interface Document {
  id: number;
  knowledge_base_id: number;
  user_id: number | null;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentStatusInfo {
  id: number;
  status: string;
  progress: number;
  error_message: string | null;
}

// ============================================
// Chat
// ============================================
export interface ChatSession {
  id: number;
  knowledge_base_id: number;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  session_id: number;
  user_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
}

export interface RagReference {
  id: number;
  source_filename: string | null;
  page_number: number | null;
  section_title: string | null;
  content_preview: string | null;
  score: number | null;
}

// ============================================
// Task
// ============================================
export interface BackgroundTask {
  id: number;
  task_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  related_document_id: number | null;
  progress: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// ============================================
// SSE Events
// ============================================
export type SSEEventType =
  | 'retrieval_start'
  | 'retrieval_done'
  | 'token'
  | 'references'
  | 'done'
  | 'error';

export interface RetrievalStats {
  mode?: string;
  raw_count?: number;
  valid_count?: number;
  reranked_count?: number;
  count?: number;
  cached?: boolean;
}

export interface SSEReference {
  source_filename: string | null;
  document_id: number | null;
  chunk_id?: number | null;
  chunk_index?: number | null;
  page_number: number | null;
  section_title: string | null;
  content_preview: string | null;
  score: number | null;
}

export interface SSEDoneData {
  content?: string;
  references?: SSEReference[];
}
