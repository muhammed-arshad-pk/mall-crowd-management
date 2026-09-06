import { useState } from 'react'
import { LiveTab } from './components/LiveTab'
import { ReportsTab } from './components/ReportsTab'
import { Tabs, type TabId } from './components/Tabs'
import { TopBar } from './components/TopBar'
import { LiveDataProvider, useLiveData } from './hooks/useLiveData'

function Shell() {
  const [tab, setTab] = useState<TabId>('live')
  const { connected } = useLiveData()

  return (
    <>
      <TopBar connected={connected} />
      <Tabs active={tab} onChange={setTab} />
      <main className="mx-auto max-w-[1440px] px-8 py-6 pb-14">{tab === 'live' ? <LiveTab /> : <ReportsTab />}</main>
    </>
  )
}

export default function App() {
  return (
    <LiveDataProvider>
      <Shell />
    </LiveDataProvider>
  )
}
