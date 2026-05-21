'use client'

import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued'

type Props = {
  oldPrompt: string
  newPrompt: string
  oldLabel?: string
  newLabel?: string
}

export function SkillDiff({ oldPrompt, newPrompt, oldLabel, newLabel }: Props) {
  if (oldPrompt === newPrompt) {
    return (
      <p data-testid="skill-diff-empty" className="p-card text-xs text-muted-foreground">
        兩版 prompt 內容相同
      </p>
    )
  }
  return (
    <div className="overflow-auto text-xs" data-testid="skill-diff">
      <ReactDiffViewer
        oldValue={oldPrompt}
        newValue={newPrompt}
        leftTitle={oldLabel ?? '舊版'}
        rightTitle={newLabel ?? '新版'}
        splitView
        compareMethod={DiffMethod.WORDS}
        useDarkTheme={false}
        styles={{
          variables: {
            light: {
              diffViewerBackground: '#fafafa',
              addedBackground: '#dcfce7',
              removedBackground: '#fee2e2',
            },
          },
        }}
      />
    </div>
  )
}
