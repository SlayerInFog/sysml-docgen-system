import { http } from './http'

export interface User {
  id: number
  username: string
  email: string
  full_name?: string
  role: 'admin' | 'author' | 'reader'
  is_active: boolean
  created_at: string
}

export interface Project {
  id: number
  name: string
  code: string
  description?: string
  owner_id: number
  created_at: string
  updated_at: string
}

export interface ProjectMember {
  id: number
  project_id: number
  user_id: number
  username: string
  full_name?: string
  email: string
  role: 'owner' | 'manager' | 'editor' | 'viewer'
  created_at: string
}

export interface SysMLModel {
  id: number
  project_id: number
  name: string
  description?: string
  source_filename: string
  version: number
  status: string
  uploaded_by: number
  created_at: string
}

export interface ModelElement {
  id: number
  model_id: number
  element_uid: string
  name: string
  type: string
  documentation?: string
  parent_uid?: string
}

export interface ModelRelation {
  id: number
  model_id: number
  source_uid: string
  target_uid: string
  relation_type: string
  label?: string
}

export interface ModelCompareItem {
  uid: string
  name?: string
  type?: string
  change_fields: string[]
}

export interface RelationCompareItem {
  source_uid: string
  target_uid: string
  relation_type: string
  label?: string
}

export interface ModelCompare {
  base_model: SysMLModel
  target_model: SysMLModel
  added_elements: ModelCompareItem[]
  removed_elements: ModelCompareItem[]
  changed_elements: ModelCompareItem[]
  added_relations: RelationCompareItem[]
  removed_relations: RelationCompareItem[]
}

export interface Template {
  id: number
  project_id?: number
  name: string
  description?: string
  content: string
  version: number
  created_at: string
}

export interface TemplateVersion {
  id: number
  template_id: number
  version: number
  name: string
  description?: string
  content: string
  created_by?: number
  created_at: string
}

export interface GeneratedDocument {
  id: number
  project_id: number
  model_id: number
  template_id: number
  title: string
  status: string
  html_content: string
  file_path?: string
  created_by: number
  created_at: string
}

export const authApi = {
  register: (data: Record<string, unknown>) => http.post<User>('/auth/register', data).then((r) => r.data),
  login: (data: { username: string; password: string }) =>
    http.post<{ access_token: string; token_type: string; user: User }>('/auth/login', data).then((r) => r.data),
  me: () => http.get<User>('/auth/me').then((r) => r.data),
  users: () => http.get<User[]>('/auth/users').then((r) => r.data),
  userOptions: () => http.get<User[]>('/auth/users/options').then((r) => r.data),
  updateUser: (id: number, data: { role?: User['role']; is_active?: boolean }) =>
    http.patch<User>(`/auth/users/${id}`, data).then((r) => r.data),
}

export const projectApi = {
  list: () => http.get<Project[]>('/projects').then((r) => r.data),
  create: (data: { name: string; code: string; description?: string }) =>
    http.post<Project>('/projects', data).then((r) => r.data),
  update: (id: number, data: { name?: string; description?: string }) =>
    http.patch<Project>(`/projects/${id}`, data).then((r) => r.data),
  remove: (id: number) => http.delete(`/projects/${id}`).then((r) => r.data),
  members: (id: number) => http.get<ProjectMember[]>(`/projects/${id}/members`).then((r) => r.data),
  addMember: (id: number, data: { user_id: number; role: 'manager' | 'editor' | 'viewer' }) =>
    http.post<ProjectMember>(`/projects/${id}/members`, data).then((r) => r.data),
  updateMember: (projectId: number, memberId: number, data: { role: 'manager' | 'editor' | 'viewer' }) =>
    http.patch<ProjectMember>(`/projects/${projectId}/members/${memberId}`, data).then((r) => r.data),
  removeMember: (projectId: number, memberId: number) =>
    http.delete(`/projects/${projectId}/members/${memberId}`).then((r) => r.data),
}

export const modelApi = {
  list: (projectId?: number) =>
    http.get<SysMLModel[]>('/models', { params: projectId ? { project_id: projectId } : {} }).then((r) => r.data),
  upload: (form: FormData) => http.post<SysMLModel>('/models/upload', form).then((r) => r.data),
  elements: (modelId: number) => http.get<ModelElement[]>(`/models/${modelId}/elements`).then((r) => r.data),
  graph: (modelId: number) =>
    http.get<{ elements: ModelElement[]; relations: ModelRelation[] }>(`/models/${modelId}/graph`).then((r) => r.data),
  compare: (modelId: number, targetModelId: number) =>
    http
      .get<ModelCompare>('/models/compare', { params: { base_model_id: modelId, target_model_id: targetModelId } })
      .then((r) => r.data),
  updateElement: (id: number, data: { name?: string; documentation?: string }) =>
    http.patch<ModelElement>(`/models/elements/${id}`, data).then((r) => r.data),
}

export const documentApi = {
  templates: (projectId?: number) =>
    http.get<Template[]>('/documents/templates', { params: projectId ? { project_id: projectId } : {} }).then((r) => r.data),
  createDefaultTemplate: () => http.post<Template>('/documents/templates/default').then((r) => r.data),
  createTemplate: (data: { project_id?: number; name: string; description?: string; content: string }) =>
    http.post<Template>('/documents/templates', data).then((r) => r.data),
  updateTemplate: (id: number, data: { name?: string; description?: string; content?: string }) =>
    http.patch<Template>(`/documents/templates/${id}`, data, { timeout: 60000 }).then((r) => r.data),
  removeTemplate: (id: number) => http.delete(`/documents/templates/${id}`).then((r) => r.data),
  templateVersions: (id: number) =>
    http.get<TemplateVersion[]>(`/documents/templates/${id}/versions`).then((r) => r.data),
  rollbackTemplate: (templateId: number, versionId: number) =>
    http.post<Template>(`/documents/templates/${templateId}/rollback/${versionId}`).then((r) => r.data),
  previewTemplate: (data: { title?: string; content: string }) =>
    http.post<{ html: string }>('/documents/templates/preview', data).then((r) => r.data),
  generate: (data: { project_id: number; model_id: number; template_id: number; title: string }) =>
    http.post<GeneratedDocument>('/documents/generate', data).then((r) => r.data),
  list: (projectId?: number) =>
    http.get<GeneratedDocument[]>('/documents', { params: projectId ? { project_id: projectId } : {} }).then((r) => r.data),
  detail: (id: number) => http.get<GeneratedDocument>(`/documents/${id}`).then((r) => r.data),
  remove: (id: number) => http.delete(`/documents/${id}`).then((r) => r.data),
  export: (id: number, fmt: 'html' | 'docx' | 'pdf') =>
    http.get<Blob>(`/documents/${id}/export/${fmt}`, { responseType: 'blob' }).then((r) => r.data),
  exportUrl: (id: number, fmt: 'html' | 'docx' | 'pdf') => `/api/documents/${id}/export/${fmt}`,
}

export const auditApi = {
  logs: (params?: {
    action?: string
    target_type?: string
    user_id?: number
    keyword?: string
    start_time?: string
    end_time?: string
    limit?: number
  }) =>
    http.get('/audit/logs', { params }).then((r) => r.data),
}
