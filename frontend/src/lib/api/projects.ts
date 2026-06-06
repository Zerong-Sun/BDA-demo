import { apiRequest } from './client'
import type { Project } from '../schemas/candidate'

export function listProjects() {
  return apiRequest<Project[]>('/projects')
}

export interface CandidateFunnel {
  generated: number
  designed: number
  folded: number
  scored: number
  ordered: number
}

export interface ResultsSummary {
  hit_count: number
  ordered_count: number
  hit_rate_pct: number
  hit_rate_label: string
  best_kd: string
  best_kd_candidate: string | null
  main_failure: string
  main_failure_detail: string
  sec_failure_count: number
  decision: string
  decision_detail: string
  experiment_summary: string | null
}

export interface DeliveryPackageData {
  package_id: string
  project_id: string
  candidate_ids: string[]
  report_file: string | null
  fasta_file: string | null
  structure_bundle: string | null
  score_table: string | null
  experiment_summary: string | null
  redesign_constraints: Record<string, unknown>
}

export interface WorkflowRunSummary {
  workflow_run_id: string
  task_id: string
  status: string
  summary_metrics_json: Record<string, unknown>
}

export function getCandidateFunnel(projectId: string) {
  return apiRequest<CandidateFunnel>(`/projects/${projectId}/candidate-funnel`)
}

export function getResultsSummary(projectId: string) {
  return apiRequest<ResultsSummary>(`/projects/${projectId}/results-summary`)
}

export function getDeliveryPackage(projectId: string) {
  return apiRequest<DeliveryPackageData>(`/projects/${projectId}/delivery-package`)
}

export function getLatestWorkflowRun(projectId: string) {
  return apiRequest<WorkflowRunSummary>(`/projects/${projectId}/workflow-runs/latest`)
}
