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

export async function getLatestWorkflowRunOrNull(projectId: string): Promise<WorkflowRun | null> {
  try {
    return await getLatestWorkflowRun(projectId)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}

export type { CandidateFunnel, DeliveryPackageData, ResultsSummary, Project, ProjectOverview }
