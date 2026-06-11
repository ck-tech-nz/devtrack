import { describe, it, expect } from 'vitest'
import { buildIssueQueryParams, type IssueFilterState } from '../app/utils/issueQuery'

function base(over: Partial<IssueFilterState> = {}): IssueFilterState {
  return {
    page: 1,
    pageSize: 20,
    showCompleted: false,
    filterStatus: '',
    filterAssignee: '',
    filterHandlerId: null,
    filterPriority: '',
    filterPriorityTagValue: null,
    filterReporter: null,
    search: '',
    ...over,
  }
}

describe('buildIssueQueryParams', () => {
  it('always sets page and page_size', () => {
    const p = buildIssueQueryParams(base({ page: 3, pageSize: 50 }))
    expect(p.get('page')).toBe('3')
    expect(p.get('page_size')).toBe('50')
  })

  it('excludes completed statuses by default (no showCompleted, no status)', () => {
    const p = buildIssueQueryParams(base())
    expect(p.get('exclude_statuses')).toBe('已关闭,未计划')
  })

  it('drops the exclude_statuses default when showCompleted is on', () => {
    const p = buildIssueQueryParams(base({ showCompleted: true }))
    expect(p.has('exclude_statuses')).toBe(false)
  })

  it('drops the exclude_statuses default when an explicit status is chosen', () => {
    const p = buildIssueQueryParams(base({ filterStatus: '处理中' }))
    expect(p.has('exclude_statuses')).toBe(false)
    expect(p.get('status')).toBe('处理中')
  })

  it('inline handler badge takes precedence over the assignee dropdown', () => {
    const p = buildIssueQueryParams(base({ filterHandlerId: '7', filterAssignee: '99' }))
    expect(p.get('assignee')).toBe('7')
  })

  it('falls back to the assignee dropdown when no handler badge', () => {
    const p = buildIssueQueryParams(base({ filterAssignee: '99' }))
    expect(p.get('assignee')).toBe('99')
  })

  it('inline priority badge takes precedence over the priority slider', () => {
    const p = buildIssueQueryParams(base({ filterPriorityTagValue: 'P0', filterPriority: 'P3' }))
    expect(p.get('priority')).toBe('P0')
  })

  it('falls back to the priority slider when no priority badge', () => {
    const p = buildIssueQueryParams(base({ filterPriority: 'P2' }))
    expect(p.get('priority')).toBe('P2')
  })

  it('maps reporter filter to its own param key (reporter vs created_by)', () => {
    const asReporter = buildIssueQueryParams(base({ filterReporter: { type: 'reporter', value: 'alice' } }))
    expect(asReporter.get('reporter')).toBe('alice')
    expect(asReporter.has('created_by')).toBe(false)

    const asCreatedBy = buildIssueQueryParams(base({ filterReporter: { type: 'created_by', value: '42' } }))
    expect(asCreatedBy.get('created_by')).toBe('42')
    expect(asCreatedBy.has('reporter')).toBe(false)
  })

  it('trims search and omits it when blank', () => {
    expect(buildIssueQueryParams(base({ search: '  bug  ' })).get('search')).toBe('bug')
    expect(buildIssueQueryParams(base({ search: '   ' })).has('search')).toBe(false)
  })

  it('omits optional params entirely when nothing is filtered', () => {
    const p = buildIssueQueryParams(base())
    expect(p.has('assignee')).toBe(false)
    expect(p.has('priority')).toBe(false)
    expect(p.has('status')).toBe(false)
    expect(p.has('search')).toBe(false)
  })
})
