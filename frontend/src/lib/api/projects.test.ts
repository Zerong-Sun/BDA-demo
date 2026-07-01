import { describe, expect, it } from 'vitest'
import { deleteProject } from './projects'

describe('project api', () => {
  it('deletes a project by moving its workspace to trash', async () => {
    const result = await deleteProject('proj_delete_test')

    expect(result).toMatchObject({
      project_id: 'proj_delete_test',
      deleted: true,
      workspace: {
        status: 'trashed',
        root: 'projects/proj_delete_test',
        trash_root: 'project_trash/20260701T000000Z_proj_delete_test',
      },
    })
  })
})
