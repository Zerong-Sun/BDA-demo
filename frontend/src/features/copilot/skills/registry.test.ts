import { describe, expect, it } from 'vitest'
import { copilotSkills, matchSkill } from './registry'

describe('copilot skill registry', () => {
  it('registers all planned skills', () => {
    expect(copilotSkills.map((skill) => skill.name)).toEqual([
      'programmable-biomaterials-expert',
      'paper-reader',
      'query-candidates',
      'workflow-adjust',
      'result-interpret',
      'structure-explain',
    ])
  })

  it('matches candidate ranking prompts', () => {
    expect(matchSkill('Which candidate should we rank first?')?.name).toBe('query-candidates')
  })

  it('matches programmable biomaterials prompts', () => {
    expect(matchSkill('How should RFdiffusion and ProteinMPNN connect for a protein hydrogel?')?.name).toBe(
      'programmable-biomaterials-expert',
    )
  })

  it('matches workflow prompts in Chinese', () => {
    expect(matchSkill('调整工作流阈值')?.name).toBe('workflow-adjust')
  })

  it('returns undefined for unrelated prompts', () => {
    expect(matchSkill('hello world')).toBeUndefined()
  })
})
