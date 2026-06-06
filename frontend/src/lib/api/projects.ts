import { apiRequest } from './client'
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
import { z } from 'zod'

export function listProjects() {
  return apiRequest<Project[]>('/projects', {}, z.array(ProjectSchema))
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

export function getLatestWorkflowRun(projectId: string) {
  return apiRequest<WorkflowRun>(`/projects/${projectId}/workflow-runs/latest`, {}, WorkflowRunSchema)
}

export type { CandidateFunnel, DeliveryPackageData, ResultsSummary, Project, ProjectOverview }
