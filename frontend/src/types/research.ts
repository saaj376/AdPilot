export interface ResearchInput {
  product_name: string
  product_description: string
  audience: string
  product_facts: string[]
  videos: { url: string; transcript: string }[]
  languages: string[]
}
export interface Finding {
  problem: string
  category: string
  evidence_ids: string[]
  product_fact_ids: number[]
  hypothesis: string
  keywords: string[]
  headline: string
  description: string
  landing_page_change: string
  experiment: string
  success_metric: string
}
export interface ResearchBrief {
  id: string
  status: 'pending' | 'collecting' | 'analyzing' | 'ready' | 'failed'
  input: ResearchInput
  sources: {
    url: string
    video_id: string
    status: string
    origin?: string
    truncated?: boolean
    error?: string
    evidence: { id: string; text: string; seconds: number; url: string }[]
  }[]
  analysis: { summary: string; findings: Finding[]; limitations: string[] } | null
  error: string | null
}
