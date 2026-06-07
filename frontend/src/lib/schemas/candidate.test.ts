import { describe, expect, it } from 'vitest'
import { CandidateListSchema, CandidateSchema } from './candidate'

const validCandidate = {
  candidate_id: 'PD1Binder_c4361',
  project_id: 'proj_pd1_0423',
  family: 'scaffold_a',
  interface_score: 0.91,
  pred_kd: '0.6 nM',
  plddt: 88.2,
  status: 'validated',
  decision: 'Anchor',
}

describe('CandidateSchema', () => {
  it('accepts a valid candidate payload', () => {
    expect(CandidateSchema.parse(validCandidate).candidate_id).toBe('PD1Binder_c4361')
  })

  it('rejects missing required numeric fields', () => {
    expect(() => CandidateSchema.parse({ ...validCandidate, interface_score: 'bad' })).toThrow()
  })
})

describe('CandidateListSchema', () => {
  it('accepts paginated list envelopes', () => {
    const parsed = CandidateListSchema.parse({
      items: [validCandidate],
      total: 1,
      limit: 50,
      offset: 0,
    })
    expect(parsed.items).toHaveLength(1)
    expect(parsed.total).toBe(1)
  })
})
