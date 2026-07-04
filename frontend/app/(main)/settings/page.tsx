'use client'
import { useEffect, useState } from 'react'
import { api, type AppSettings } from '@/lib/api'

export default function SettingsPage() {
  const [thresholds, setThresholds] = useState<AppSettings | null>(null)
  const [channelType, setChannelType] = useState<'webhook' | 'slack' | 'email'>('webhook')
  const [channelUrl, setChannelUrl] = useState('')
  const [channelTo, setChannelTo] = useState('')
  const [saved, setSaved] = useState(false)
  const [llmProvider, setLlmProvider] = useState<'anthropic' | 'openai' | 'openrouter' | 'huggingface' | 'local'>('anthropic')
  const [llmModel, setLlmModel] = useState('')
  const [llmBaseUrl, setLlmBaseUrl] = useState('')
  const [llmApiKey, setLlmApiKey] = useState('')
  const [llmKeySet, setLlmKeySet] = useState(false)

  useEffect(() => {
    api.settings.get().then(s => {
      setThresholds(s)
      const c = s.default_alert_channel
      if (c) {
        setChannelType((c.type as 'webhook' | 'slack' | 'email') ?? 'webhook')
        setChannelUrl((c.url as string) ?? '')
        setChannelTo((c.to as string) ?? '')
      }
      setLlmProvider((s.llm_provider as typeof llmProvider) ?? 'anthropic')
      setLlmModel(s.llm_model ?? '')
      setLlmBaseUrl(s.llm_base_url ?? '')
      setLlmKeySet(s.llm_api_key_set ?? false)
    }).catch(() => {})
  }, [])

  async function saveThresholds() {
    if (!thresholds) return
    const updated = await api.settings.update({
      token_explosion_threshold: thresholds.token_explosion_threshold,
      excessive_tool_calls_threshold: thresholds.excessive_tool_calls_threshold,
      infinite_loop_repeat_threshold: thresholds.infinite_loop_repeat_threshold,
      behavior_similarity_threshold: thresholds.behavior_similarity_threshold,
    })
    setThresholds(updated)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  async function saveDefaultChannel() {
    const channel = channelType === 'email' ? { type: 'email', to: channelTo } : { type: channelType, url: channelUrl }
    const updated = await api.settings.update({ default_alert_channel: channel })
    setThresholds(updated)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  async function saveLlmProvider() {
    const body: Partial<AppSettings> & { llm_api_key?: string } = {
      llm_provider: llmProvider,
      llm_model: llmModel,
      llm_base_url: llmProvider === 'local' ? llmBaseUrl : null,
    }
    if (llmApiKey) body.llm_api_key = llmApiKey
    const updated = await api.settings.update(body)
    setThresholds(updated)
    setLlmKeySet(updated.llm_api_key_set)
    setLlmApiKey('')
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (!thresholds) return <div className="p-6 text-sm text-muted">Loading…</div>

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-lg font-semibold">Settings</h1>
      </div>

      <div className="mb-8">
        <p className="text-xs text-muted font-mono mb-3">GUARDRAIL THRESHOLDS</p>
        <div className="rounded border border-border p-4 space-y-3">
          <div>
            <label className="block text-xs text-muted mb-1">Token explosion (total tokens per span)</label>
            <input type="number" value={thresholds.token_explosion_threshold}
              onChange={e => setThresholds({ ...thresholds, token_explosion_threshold: Number(e.target.value) })}
              className="w-full rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60" />
          </div>
          <div>
            <label className="block text-xs text-muted mb-1">Excessive tool calls (per trace)</label>
            <input type="number" value={thresholds.excessive_tool_calls_threshold}
              onChange={e => setThresholds({ ...thresholds, excessive_tool_calls_threshold: Number(e.target.value) })}
              className="w-full rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60" />
          </div>
          <div>
            <label className="block text-xs text-muted mb-1">Infinite loop repeat count</label>
            <input type="number" value={thresholds.infinite_loop_repeat_threshold}
              onChange={e => setThresholds({ ...thresholds, infinite_loop_repeat_threshold: Number(e.target.value) })}
              className="w-full rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60" />
          </div>
          <div>
            <label className="block text-xs text-muted mb-1">Behavior similarity threshold (0–1)</label>
            <input type="number" step="0.01" min="0" max="1" value={thresholds.behavior_similarity_threshold}
              onChange={e => setThresholds({ ...thresholds, behavior_similarity_threshold: Number(e.target.value) })}
              className="w-full rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60" />
          </div>
          <button onClick={saveThresholds}
            className="text-xs font-mono px-3 py-1.5 rounded border border-cyan/40 text-cyan hover:bg-cyan/10 transition-colors">
            Save thresholds
          </button>
          <p className="text-xs text-muted">Changes take effect within 60 seconds (cached).</p>
        </div>
      </div>

      <div className="mb-8">
        <p className="text-xs text-muted font-mono mb-3">DEFAULT ALERT CHANNEL</p>
        <div className="rounded border border-border p-4 space-y-3">
          <div className="flex gap-2">
            <select value={channelType} onChange={e => setChannelType(e.target.value as 'webhook' | 'slack' | 'email')}
              className="rounded border border-border bg-surface text-sm px-2 py-1.5 text-text focus:outline-none focus:border-cyan/60">
              <option value="webhook">Webhook</option>
              <option value="slack">Slack</option>
              <option value="email">Email</option>
            </select>
            {channelType === 'email' ? (
              <input type="email" value={channelTo} onChange={e => setChannelTo(e.target.value)} placeholder="you@example.com"
                className="flex-1 rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60" />
            ) : (
              <input type="text" value={channelUrl} onChange={e => setChannelUrl(e.target.value)} placeholder="https://..."
                className="flex-1 rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60" />
            )}
          </div>
          <button onClick={saveDefaultChannel}
            className="text-xs font-mono px-3 py-1.5 rounded border border-cyan/40 text-cyan hover:bg-cyan/10 transition-colors">
            Save default channel
          </button>
          <p className="text-xs text-muted">Pre-fills new alert rules on the Alerts page.</p>
        </div>
      </div>

      <div className="mb-8">
        <p className="text-xs text-muted font-mono mb-3">LLM PROVIDER (BEHAVIOR RUBRIC GENERATION)</p>
        <div className="rounded border border-border p-4 space-y-3">
          <div className="flex gap-2">
            <select value={llmProvider} onChange={e => setLlmProvider(e.target.value as typeof llmProvider)}
              className="rounded border border-border bg-surface text-sm px-2 py-1.5 text-text focus:outline-none focus:border-cyan/60">
              <option value="anthropic">Anthropic</option>
              <option value="openai">OpenAI</option>
              <option value="openrouter">OpenRouter</option>
              <option value="huggingface">Hugging Face</option>
              <option value="local">Local / OpenAI-compatible</option>
            </select>
            <input type="text" value={llmModel} onChange={e => setLlmModel(e.target.value)}
              placeholder="e.g. claude-sonnet-4-6 or gpt-4o-mini"
              className="flex-1 rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60" />
          </div>
          {llmProvider === 'local' && (
            <input type="url" value={llmBaseUrl} onChange={e => setLlmBaseUrl(e.target.value)}
              placeholder="http://localhost:11434/v1"
              className="w-full rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60" />
          )}
          <div>
            <input type="password" value={llmApiKey} onChange={e => setLlmApiKey(e.target.value)}
              placeholder={llmKeySet ? '•••• (already set — enter a new value to replace it)' : 'API key'}
              className="w-full rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60" />
          </div>
          <button onClick={saveLlmProvider}
            className="text-xs font-mono px-3 py-1.5 rounded border border-cyan/40 text-cyan hover:bg-cyan/10 transition-colors">
            Save LLM provider
          </button>
          <p className="text-xs text-muted">Used only to name behavior clusters. AgentQ has no bundled API key.</p>
        </div>
      </div>

      {saved && <p className="text-xs text-green font-mono mt-4">Saved.</p>}
    </div>
  )
}
