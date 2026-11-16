import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { TopNav } from '../components/layout/TopNav'
import { request, isApiError } from '../services/api'
import type { ResearchBrief, ResearchInput } from '../types/research'

const emptyInput: ResearchInput = {
  product_name: '', product_description: '', audience: '', product_facts: [''],
  videos: [{ url: '', transcript: '' }], languages: ['en', 'hi'],
}

function errorText(error: unknown): string {
  if (isApiError(error)) {
    const detail = (error.body as { detail?: unknown })?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((item) => item.msg).join('. ')
  }
  return 'Could not reach the research service. Check the connection and retry.'
}

export function ResearchPage() {
  const { briefId } = useParams()
  const navigate = useNavigate()
  const [input, setInput] = useState<ResearchInput>(emptyInput)
  const [facts, setFacts] = useState('')
  const [brief, setBrief] = useState<ResearchBrief | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!briefId) return
    let cancelled = false
    let timer: number | undefined
    async function poll() {
      try {
        const result = await request<ResearchBrief>(`/research/${briefId}`)
        if (cancelled) return
        setBrief(result)
        setError('')
        if (!['ready', 'failed'].includes(result.status)) timer = window.setTimeout(poll, 2000)
      } catch (err) {
        if (!cancelled) {
          setError(errorText(err))
          timer = window.setTimeout(poll, 5000)
        }
      }
    }
    void poll()
    return () => { cancelled = true; window.clearTimeout(timer) }
  }, [briefId])

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await request<ResearchBrief>('/research', {
        method: 'POST', body: JSON.stringify({ ...input, product_facts: facts.split('\n').map(f => f.trim()).filter(Boolean) }),
      })
      setBrief(result)
      navigate(`/research/${result.id}`)
    } catch (err) { setError(errorText(err)) }
    finally { setBusy(false) }
  }

  function exportBrief() {
    if (!brief) return
    const url = URL.createObjectURL(new Blob([JSON.stringify(brief, null, 2)], { type: 'application/json' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'campaign-research.json'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const current = brief?.id === briefId ? brief : null
  const analysis = current?.analysis
  const evidence = new Map(current?.sources.flatMap(s => s.evidence).map(e => [e.id, e]) ?? [])

  return <div className="page-shell">
    <TopNav title="Turn customer problems into campaign experiments"
      subtitle="YouTube research for small ecommerce and home-appliance brands. Start with evidence before spending on ads."
      actions={briefId ? <Link className="ghost-btn" to="/">New research</Link> : undefined} />
    {error && <p role="alert" className="form-error">{error}</p>}
    {!briefId ? <>
      <section className="research-intro">
        <h2>What should your next ad actually say?</h2>
        <p>Add product reviews, comparisons, or tutorials. Get customer problems, buying objections, and testable ad angles with links to the moments that inspired them.</p>
        <p>For example: a pet-hair vacuum seller can investigate maintenance concerns, then test a message supported by their product’s actual features.</p>
      </section>
      <form className="campaign-form" onSubmit={submit}>
        <label className="field-label" htmlFor="product-name">Product name</label>
        <input id="product-name" className="field-input" required minLength={2} maxLength={120}
          placeholder="e.g. HomeSweep pet-hair vacuum" value={input.product_name}
          onChange={e => setInput({ ...input, product_name: e.target.value })} />
        <label className="field-label" htmlFor="product-description">What do you sell?</label>
        <textarea id="product-description" className="field-textarea" required minLength={20} maxLength={4000}
          placeholder="Describe the product and the problem it is designed to solve." value={input.product_description}
          onChange={e => setInput({ ...input, product_description: e.target.value })} />
        <label className="field-label" htmlFor="audience">Who are you trying to reach?</label>
        <input id="audience" className="field-input" required minLength={5} maxLength={1000}
          placeholder="e.g. Apartment households with pets in India" value={input.audience}
          onChange={e => setInput({ ...input, audience: e.target.value })} />
        <label className="field-label" htmlFor="product-facts">Product facts you can substantiate — one per line</label>
        <textarea id="product-facts" className="field-textarea" required maxLength={7500} value={facts}
          placeholder={'Washable filter\nReplacement brush costs ₹499\nTwo-year manufacturer warranty'} onChange={e => setFacts(e.target.value)} />
        <p className="field-hint">Only supplied facts can support product claims. Include up to 15 specific features, prices, or policies.</p>
        <h3>YouTube sources</h3>
        <p className="field-hint">Add up to five relevant videos. We analyze available English or Hindi captions, not images or comments.</p>
        {input.videos.map((video, index) => <fieldset className="research-source" key={index}>
          <legend>Video {index + 1}</legend>
          <label className="field-label" htmlFor={`video-${index}`}>YouTube video URL</label>
          <input id={`video-${index}`} className="field-input" type="url" required value={video.url}
            placeholder="https://www.youtube.com/watch?v=..." onChange={e => setInput({ ...input,
              videos: input.videos.map((v, i) => i === index ? { ...v, url: e.target.value } : v) })} />
          <details><summary>Paste transcript excerpts if captions are unavailable</summary>
            <p className="field-hint">One excerpt per line with its video timestamp, for example [02:15] The brush needs cleaning after every use.</p>
            <textarea aria-label={`Timestamped transcript for video ${index + 1}`} className="field-textarea" maxLength={30000}
              value={video.transcript} onChange={e => setInput({ ...input,
                videos: input.videos.map((v, i) => i === index ? { ...v, transcript: e.target.value } : v) })} />
          </details>
          {input.videos.length > 1 && <button type="button" className="ghost-btn" onClick={() => setInput({ ...input,
            videos: input.videos.filter((_, i) => i !== index) })}>Remove video</button>}
        </fieldset>)}
        {input.videos.length < 5 && <button className="ghost-btn" type="button" onClick={() => setInput({ ...input,
          videos: [...input.videos, { url: '', transcript: '' }] })}>Add another video</button>}
        <p className="field-hint">A brief generates research hypotheses and drafts for review. It does not publish ads or spend money.</p>
        <button className="primary-btn" type="submit" disabled={busy}>{busy ? 'Starting research…' : 'Build research brief'}</button>
      </form>
    </> : !current ? <p className="empty-state">Loading research brief…</p> : <>
      <section className="research-intro" aria-live="polite">
        <h2>{current.input.product_name}</h2>
        <p>Audience: {current.input.audience}</p>
        <strong>{({ pending: 'Research queued', collecting: 'Collecting transcript evidence…', analyzing: 'Building evidence-backed experiments…', ready: 'Brief ready for review', failed: 'Research could not finish' })[current.status]}</strong>
        {current.error && <p role="alert" className="form-error">{current.error}</p>}
        {current.status === 'failed' && <button className="ghost-btn" onClick={() => {
          setInput({ ...current.input, videos: current.input.videos.map(v => {
            const source = current.sources.find(s => s.url === v.url && s.origin === 'user_supplied')
            return { ...v, transcript: source?.evidence.map(e => {
              const stamp = new Date(e.seconds * 1000).toISOString().slice(11, 19)
              return `[${stamp}] ${e.text}`
            }).join('\n') ?? '' }
          }) })
          setFacts(current.input.product_facts.join('\n'))
          navigate('/')
        }}>Edit sources and retry</button>}
      </section>
      <section className="research-source-list">
        {current.sources.map(source => <article className="research-source" key={source.video_id}>
          <a href={source.url} target="_blank" rel="noreferrer">View video {source.video_id}</a>
          <p>{source.status === 'ready' ? `${source.evidence.length} excerpts · ${source.origin?.replaceAll('_', ' ')}` : source.error}</p>
          {source.truncated && <p className="field-hint">Analysis covers an initial excerpt of this video, not the full transcript.</p>}
        </article>)}
      </section>
      {analysis && <>
        <p className="research-summary">{analysis.summary}</p>
        <div className="research-actions"><button className="primary-btn" onClick={exportBrief}>Export brief JSON</button>
          <Link className="ghost-btn" to="/campaigns/new" state={{ researchBriefId: current.id,
            businessDescription: `${current.input.product_name}: ${current.input.product_description}. Audience: ${current.input.audience}. Product facts: ${current.input.product_facts.join('; ')}` }}>Prepare campaign plan</Link></div>
        <p className="field-hint">Review all drafts and product claims before use. Video opinions are hypotheses, not proven demand.</p>
        <section className="research-findings">{analysis.findings.map((finding, index) => <article className="report-card" key={index}>
          <p className="field-hint">{finding.category.replaceAll('_', ' ')} · Hypothesis {index + 1}</p>
          <h3>{finding.problem}</h3><p>{finding.hypothesis}</p>
          <h4>Transcript evidence</h4>
          {finding.evidence_ids.map(id => { const item = evidence.get(id); return item ? <blockquote key={id}>
            <p>“{item.text}”</p><a href={item.url} target="_blank" rel="noreferrer">Watch at {Math.floor(item.seconds / 60)}:{String(Math.floor(item.seconds % 60)).padStart(2, '0')}</a>
          </blockquote> : null })}
          <h4>Product fit</h4>
          {finding.product_fact_ids.length ? <ul>{finding.product_fact_ids.map(id => <li key={id}>{current.input.product_facts[id]}</li>)}</ul>
            : <p className="form-error">Research gap: no supplied product fact supports solving this problem. Do not use this as a product claim.</p>}
          <h4>Search keyword ideas</h4><p>{finding.keywords.join(' · ')}</p>
          <h4>Ad draft — requires review</h4><strong>{finding.headline}</strong><p>{finding.description}</p>
          <h4>Landing-page improvement</h4><p>{finding.landing_page_change}</p>
          <h4>Experiment</h4><p>{finding.experiment}</p><p><strong>Measure:</strong> {finding.success_metric}</p>
        </article>)}</section>
        <section className="research-intro"><h3>Limits of this research</h3><ul>{analysis.limitations.map((limit, i) => <li key={i}>{limit}</li>)}</ul></section>
      </>}
    </>}
  </div>
}
