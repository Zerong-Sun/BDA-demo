import { ApiError, apiRequest } from './client'
import { fetchPaginatedList } from './pagination'
import {
  CandidateFunnelSchema,
  DeliveryPackageSchema,
  ResultsSummarySchema,
  type CandidateFunnel,
  type DeliveryPackageData,
  type ResultsSummary,
} from '../schemas/delivery'
import { ProjectOverviewSchema, ProjectSchema, type Project, type ProjectOverview } from '../schemas/project'
import { WorkflowRunSchema, type WorkflowRun } from '../schemas/workflow'

export function listProjects(): Promise<Project[]> {
  return fetchPaginatedList('/projects', ProjectSchema)
}

export interface CreateProjectPayload {
  project_name: string
  project_type: string
  summary?: string
}

export function createProject(payload: CreateProjectPayload): Promise<Project> {
  return apiRequest<Project>(
    '/projects',
    { method: 'POST', body: JSON.stringify(payload) },
    ProjectSchema,
  )
}

export interface DeleteProjectResult {
  project_id: string
  deleted: boolean
  workspace: {
    status: string
    backend: string
    root: string
    trash_root?: string | null
    deleted_at?: string
  }
}

export function deleteProject(projectId: string): Promise<DeleteProjectResult> {
  return apiRequest<DeleteProjectResult>(`/projects/${projectId}`, { method: 'DELETE' })
}

export function getProjectOverview(projectId: string) {
  return apiRequest<ProjectOverview>(`/projects/${projectId}/overview`, {}, ProjectOverviewSchema)
}

export function getCandidateFunnel(projectId: string) {
  return apiRequest<CandidateFunnel>(
    `/projects/${projectId}/candidate-funnel`,
    {},
    CandidateFunnelSchema,
  )
}

export function getResultsSummary(projectId: string) {
  return apiRequest<ResultsSummary>(
    `/projects/${projectId}/results-summary`,
    {},
    ResultsSummarySchema,
  )
}

export function getDeliveryPackage(projectId: string) {
  return apiRequest<DeliveryPackageData>(
    `/projects/${projectId}/delivery-package`,
    {},
    DeliveryPackageSchema,
  )
}

export async function getDeliveryPackageOrNull(projectId: string): Promise<DeliveryPackageData | null> {
  try {
    return await getDeliveryPackage(projectId)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}

export function getLatestWorkflowRun(projectId: string) {
  return apiRequest<WorkflowRun>(`/projects/${projectId}/workflow-runs/latest`, {}, WorkflowRunSchema)
}

export function listProjectWorkflowRuns(projectId: string) {
  return apiRequest<{ items: WorkflowRun[] }>(
    `/projects/${projectId}/workflow-runs`,
  ).then((payload) => payload.items.map((item) => WorkflowRunSchema.parse(item)))
}

export interface ProjectResearchSummary {
  brief: Record<string, unknown> | null
  questions: Record<string, unknown>[]
  findings: Record<string, unknown>[]
  runs: Record<string, unknown>[]
  workflow_plans: Record<string, unknown>[]
}

export function getProjectResearchSummary(projectId: string) {
  return apiRequest<ProjectResearchSummary>(`/projects/${projectId}/research-summary`)
}

export async function getLatestWorkflowRunOrNull(projectId: string): Promise<WorkflowRun | null> {
  try {
    return await getLatestWorkflowRun(projectId)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}

export type { CandidateFunnel, DeliveryPackageData, ResultsSummary, Project, ProjectOverview }
