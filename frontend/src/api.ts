import type { CareerRole, DashboardData, LearningResource, Profile, Roadmap, User } from './types';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}
function cookie(name: string) {
  const part = document.cookie.split('; ').find((item) => item.startsWith(`${name}=`));
  return part ? decodeURIComponent(part.slice(name.length + 1)) : '';
}
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const method = (init.method || 'GET').toUpperCase();
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const token = cookie('csrf_token');
    if (token) headers.set('X-CSRF-Token', token);
  }
  const response = await fetch(`/api${path}`, { ...init, headers, credentials: 'same-origin' });
  if (!response.ok) {
    let message = 'Something went wrong. Please try again.';
    try { message = (await response.json()).detail || message; } catch { /* keep safe default */ }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export const api = {
  me: () => request<{ user: User | null }>('/auth/me'),
  register: (payload: { name: string; email: string; password: string; education: string; degree: string; branch: string; graduation_year: number | null }) => request<{ user: User }>('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (email: string, password: string, remember: boolean) => request<{ user: User }>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password, remember }) }),
  logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST', body: '{}' }),
  forgotPassword: (email: string) => request<{ message: string }>('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (token: string, password: string) => request<{ message: string }>('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, password }) }),
  dashboard: () => request<DashboardData>('/dashboard'),
  saveProfile: (payload: Partial<Profile>) => request<Profile>('/profile', { method: 'PUT', body: JSON.stringify(payload) }),
  analyze: () => request<{ recommendations: DashboardData['recommendations'] }>('/career/analyze', { method: 'POST', body: '{}' }),
  catalog: () => request<{ careers: CareerRole[] }>('/career/catalog'),
  roadmap: (careerId: number) => request<Roadmap>('/roadmap/generate', { method: 'POST', body: JSON.stringify({ career_id: careerId }) }),
  updateRoadmap: (itemId: number, status: Roadmap['items'][number]['status']) => request<{ ok: boolean }>('/roadmap/progress', { method: 'PUT', body: JSON.stringify({ item_id: itemId, status }) }),
  explain: (careerId: number) => request<{ explanation: string; ai_generated: boolean }>(`/career/${careerId}/explanation`),
  chat: (message: string) => request<{ reply: string; ai_generated: boolean; resources: LearningResource[] }>('/ai/chat', { method: 'POST', body: JSON.stringify({ message }) }),
  chatHistory: () => request<{ messages: { id: number; role: 'user' | 'assistant'; content: string; ai_generated: boolean; resources: LearningResource[]; created_at: string }[] }>('/ai/history'),
  clearChatHistory: () => request<{ ok: boolean; deleted: number }>('/ai/history', { method: 'DELETE', body: '{}' }),
  research: () => request<{ authorized: boolean; runs: { id: number; name: string; method: string; dataset_name: string; sample_count: number; metrics: Record<string, number>; created_at: string }[]; message?: string }>('/research/evaluations'),
  evaluate: (dataset_name: string, cases: unknown[]) => request<{ authorized: boolean; runs: { id: number; name: string; method: string; dataset_name: string; sample_count: number; metrics: Record<string, number>; created_at: string }[] }>('/research/evaluations', { method: 'POST', body: JSON.stringify({ dataset_name, cases }) }),
  sample: () => request<{ profile: Profile; sample_profile: boolean }>('/profile/sample', { method: 'POST', body: '{}' }),
  interests: () => request<{ available: string[]; selected: Profile['interests'] }>('/interests'),
  saveInterests: (interests: string[]) => request<{ available: string[]; selected: Profile['interests'] }>('/interests', { method: 'POST', body: JSON.stringify({ interests }) }),
  settings: () => request<{ email: string; role: string; scoring_weights: Record<string, number>; weights_note: string }>('/settings'),
  updateWeights: (weights: Record<string, number>) => request<{ weights: Record<string, number>; version: number; note: string }>('/settings/scoring', { method: 'PUT', body: JSON.stringify({ weights }) }),
  uploadResume: (file: File) => { const data = new FormData(); data.append('file', file); return request<{ draft_id: string; extracted: Record<string, unknown> }>('/resume/upload', { method: 'POST', body: data }); },
  acceptResume: (draft_id: string, extracted: Record<string, unknown>) => request<{ ok: boolean; message: string }>('/resume/accept', { method: 'POST', body: JSON.stringify({ draft_id, extracted }) }),
  skillCatalog: () => request<{ skills: { name: string; category: string; description: string; previous?: { score: number; level: string; created_at: string } | null }[]; assessment_supported: string[] }>('/skill-assessment/catalog'),
  skillAssessmentHistory: () => request<{ attempts: { id: number; skill: string; score: number; level: string; attempted: number; total: number; created_at: string }[] }>('/skill-assessment/history'),
  startSkillAssessment: (skill: string, level: 'beginner' | 'intermediate' | 'advanced' = 'beginner') => request<{ attempt_id: number; skill: string; questions: { id: string; type: string; difficulty: string; prompt: string; options: string[] }[]; total: number; mode: string; note: string }>('/skill-assessment/start', { method: 'POST', body: JSON.stringify({ skill, level }) }),
  submitSkillAssessment: (attempt_id: number, answers: Record<string, number>) => request<{ attempt_id: number; skill: string; score: number; level: string; attempted: number; total: number; correct: number; feedback: { id: string; prompt: string; correct: boolean; explanation: string; correct_option: number }[]; recommendation: string }>(`/skill-assessment/${attempt_id}/submit`, { method: 'POST', body: JSON.stringify({ answers }) }),
  analyzeGithub: (url: string) => request<{ analysis_id: number; repository_url: string; name: string; description: string | null; stars: number; forks: number; languages: Record<string, number>; file_count: number; skills: { skill: string; evidence: string; confidence: string; limitation: string }[]; quality_observations: { readme_present: boolean; tests_present: boolean; ci_present: boolean; dependency_files: string[] }; readme_excerpt: string; latest_commit_at: string | null; limitations: string[] }>('/github/analyze', { method: 'POST', body: JSON.stringify({ url }) }),
  githubHistory: () => request<{ analyses: { id: number; repository_url: string; repository_name: string; summary: any; created_at: string }[] }>('/github/history'),
};
