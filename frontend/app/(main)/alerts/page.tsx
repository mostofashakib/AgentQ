// frontend/app/(main)/alerts/page.tsx
'use client'
import { useEffect, useState } from 'react'
import { api, type AlertRule, type AlertHistory } from '@/lib/api'

const EMPTY_FORM: Omit<AlertRule, 'id' | 'created_at'> = {
  name: '',
  conditions: {},
  channels: [],
  frequency_limit: 1,
  cooldown_minutes: 60,
  enabled: true,
}

export default function AlertsPage() {
  const [tab, setTab] = useState<'rules' | 'history'>('rules')

  // Rules state
  const [rules, setRules] = useState<AlertRule[]>([])
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formName, setFormName] = useState('')
  const [formConditions, setFormConditions] = useState('{}')
  const [formChannels, setFormChannels] = useState('[]')
  const [formFrequency, setFormFrequency] = useState(1)
  const [formCooldown, setFormCooldown] = useState(60)
  const [formEnabled, setFormEnabled] = useState(true)
  const [formError, setFormError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  // History state
  const [history, setHistory] = useState<AlertHistory[]>([])

  useEffect(() => {
    api.alerts.rules.list().then(setRules)
  }, [])

  useEffect(() => {
    if (tab === 'history') {
      api.alerts.history.list().then(setHistory)
    }
  }, [tab])

  function openNewForm() {
    setEditingId(null)
    setFormName(EMPTY_FORM.name)
    setFormConditions(JSON.stringify(EMPTY_FORM.conditions, null, 2))
    setFormChannels(JSON.stringify(EMPTY_FORM.channels, null, 2))
    setFormFrequency(EMPTY_FORM.frequency_limit)
    setFormCooldown(EMPTY_FORM.cooldown_minutes)
    setFormEnabled(EMPTY_FORM.enabled)
    setFormError(null)
    setShowForm(true)
  }

  function openEditForm(rule: AlertRule) {
    setEditingId(rule.id)
    setFormName(rule.name)
    setFormConditions(JSON.stringify(rule.conditions, null, 2))
    setFormChannels(JSON.stringify(rule.channels, null, 2))
    setFormFrequency(rule.frequency_limit)
    setFormCooldown(rule.cooldown_minutes)
    setFormEnabled(rule.enabled)
    setFormError(null)
    setShowForm(true)
  }

  function cancelForm() {
    setShowForm(false)
    setEditingId(null)
    setFormError(null)
  }

  async function saveForm() {
    setFormError(null)
    let parsedConditions: Record<string, string>
    let parsedChannels: Array<{ type: string; url?: string; [key: string]: unknown }>
    try {
      parsedConditions = JSON.parse(formConditions)
    } catch {
      setFormError('Conditions must be valid JSON object')
      return
    }
    try {
      parsedChannels = JSON.parse(formChannels)
    } catch {
      setFormError('Channels must be valid JSON array')
      return
    }
    const body: Omit<AlertRule, 'id' | 'created_at'> = {
      name: formName,
      conditions: parsedConditions,
      channels: parsedChannels,
      frequency_limit: formFrequency,
      cooldown_minutes: formCooldown,
      enabled: formEnabled,
    }
    setSaving(true)
    try {
      if (editingId) {
        const updated = await api.alerts.rules.update(editingId, body)
        setRules(prev => prev.map(r => (r.id === editingId ? updated : r)))
      } else {
        const created = await api.alerts.rules.create(body)
        setRules(prev => [...prev, created])
      }
      cancelForm()
    } catch {
      setFormError('Failed to save rule. Check API connectivity.')
    } finally {
      setSaving(false)
    }
  }

  async function deleteRule(id: string) {
    await api.alerts.rules.delete(id)
    setRules(prev => prev.filter(r => r.id !== id))
  }

  async function toggleEnabled(rule: AlertRule) {
    const updated = await api.alerts.rules.update(rule.id, {
      name: rule.name,
      conditions: rule.conditions,
      channels: rule.channels,
      frequency_limit: rule.frequency_limit,
      cooldown_minutes: rule.cooldown_minutes,
      enabled: !rule.enabled,
    })
    setRules(prev => prev.map(r => (r.id === rule.id ? updated : r)))
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-wide">Alerts</h1>
        <p className="text-sm text-muted mt-0.5">Configure alert rules and review firing history</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-border">
        {(['rules', 'history'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-mono capitalize transition-colors border-b-2 -mb-px ${
              tab === t
                ? 'border-cyan text-cyan'
                : 'border-transparent text-muted hover:text-text'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Rules Tab */}
      {tab === 'rules' && (
        <div>
          <div className="flex justify-end mb-4">
            <button
              onClick={openNewForm}
              className="text-xs font-mono px-3 py-1.5 rounded border border-cyan/40 text-cyan hover:bg-cyan/10 transition-colors"
            >
              + New Rule
            </button>
          </div>

          {/* Inline form */}
          {showForm && (
            <div className="mb-6 rounded border border-border bg-surface/30 p-4 space-y-3">
              <p className="text-xs font-mono text-muted font-semibold">
                {editingId ? 'EDIT RULE' : 'NEW RULE'}
              </p>

              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs text-muted mb-1">Name</label>
                  <input
                    type="text"
                    value={formName}
                    onChange={e => setFormName(e.target.value)}
                    className="w-full rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60"
                    placeholder="e.g. high-error-rate"
                  />
                </div>

                <div>
                  <label className="block text-xs text-muted mb-1">Conditions (JSON object)</label>
                  <textarea
                    value={formConditions}
                    onChange={e => setFormConditions(e.target.value)}
                    rows={4}
                    className="w-full rounded border border-border bg-surface text-xs font-mono px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60 resize-y"
                    placeholder={'{\n  "severity": "critical"\n}'}
                  />
                </div>

                <div>
                  <label className="block text-xs text-muted mb-1">Channels (JSON array)</label>
                  <textarea
                    value={formChannels}
                    onChange={e => setFormChannels(e.target.value)}
                    rows={4}
                    className="w-full rounded border border-border bg-surface text-xs font-mono px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60 resize-y"
                    placeholder={'[\n  {"type": "webhook", "url": "https://..."}\n]'}
                  />
                </div>

                <div>
                  <label className="block text-xs text-muted mb-1">Frequency Limit</label>
                  <input
                    type="number"
                    value={formFrequency}
                    min={1}
                    onChange={e => setFormFrequency(Number(e.target.value))}
                    className="w-full rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60"
                  />
                </div>

                <div>
                  <label className="block text-xs text-muted mb-1">Cooldown (minutes)</label>
                  <input
                    type="number"
                    value={formCooldown}
                    min={0}
                    onChange={e => setFormCooldown(Number(e.target.value))}
                    className="w-full rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60"
                  />
                </div>

                <div className="col-span-2 flex items-center gap-2">
                  <input
                    id="form-enabled"
                    type="checkbox"
                    checked={formEnabled}
                    onChange={e => setFormEnabled(e.target.checked)}
                    className="accent-cyan"
                  />
                  <label htmlFor="form-enabled" className="text-xs text-muted">Enabled</label>
                </div>
              </div>

              {formError && (
                <p className="text-xs text-red-400 font-mono">{formError}</p>
              )}

              <div className="flex gap-2">
                <button
                  onClick={saveForm}
                  disabled={saving}
                  className="text-xs font-mono px-3 py-1.5 rounded border border-cyan/40 text-cyan hover:bg-cyan/10 transition-colors disabled:opacity-50"
                >
                  {saving ? 'Saving…' : 'Save'}
                </button>
                <button
                  onClick={cancelForm}
                  className="text-xs font-mono px-3 py-1.5 rounded border border-border text-muted hover:text-text transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {rules.length === 0 ? (
            <div className="rounded border border-border p-12 text-center text-muted text-sm">
              No alert rules yet. Create one with &quot;New Rule&quot;.
            </div>
          ) : (
            <div className="rounded border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface/50">
                    <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">NAME</th>
                    <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">CONDITIONS</th>
                    <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">CHANNELS</th>
                    <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">FREQ LIMIT</th>
                    <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">COOLDOWN</th>
                    <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">ENABLED</th>
                    <th className="px-4 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {rules.map(rule => (
                    <tr key={rule.id} className="border-b border-border/50 hover:bg-surface/20">
                      <td className="px-4 py-2 text-xs font-mono text-cyan">{rule.name}</td>
                      <td className="px-4 py-2 text-xs font-mono text-muted max-w-xs truncate">
                        {JSON.stringify(rule.conditions)}
                      </td>
                      <td className="px-4 py-2 text-xs font-mono text-muted">
                        {rule.channels.length}
                      </td>
                      <td className="px-4 py-2 text-xs font-mono">{rule.frequency_limit}</td>
                      <td className="px-4 py-2 text-xs font-mono">{rule.cooldown_minutes}m</td>
                      <td className="px-4 py-2 text-xs">
                        <button
                          onClick={() => toggleEnabled(rule)}
                          className={`px-2 py-0.5 rounded text-xs font-mono border transition-colors ${
                            rule.enabled
                              ? 'border-cyan/30 bg-cyan/10 text-cyan hover:bg-cyan/20'
                              : 'border-border text-muted hover:border-cyan/30 hover:text-cyan'
                          }`}
                        >
                          {rule.enabled ? 'on' : 'off'}
                        </button>
                      </td>
                      <td className="px-4 py-2 text-xs">
                        <div className="flex gap-2 justify-end">
                          <button
                            onClick={() => openEditForm(rule)}
                            className="font-mono px-2 py-0.5 rounded border border-border text-muted hover:text-text hover:border-cyan/30 transition-colors"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => deleteRule(rule.id)}
                            className="font-mono px-2 py-0.5 rounded border border-border text-muted hover:text-red-400 hover:border-red-400/30 transition-colors"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {tab === 'history' && (
        <div>
          {history.length === 0 ? (
            <div className="rounded border border-border p-12 text-center text-muted text-sm">
              No alert history yet.
            </div>
          ) : (
            <div className="rounded border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface/50">
                    <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">RULE ID</th>
                    <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">TRACE ID</th>
                    <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">CHANNEL</th>
                    <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">FIRED AT</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map(entry => (
                    <tr key={entry.id} className="border-b border-border/50 hover:bg-surface/20">
                      <td className="px-4 py-2 text-xs font-mono text-cyan truncate max-w-xs">
                        {entry.rule_id}
                      </td>
                      <td className="px-4 py-2 text-xs font-mono text-muted">
                        {entry.trace_id.slice(0, 12)}&hellip;
                      </td>
                      <td className="px-4 py-2 text-xs font-mono text-muted">{entry.channel}</td>
                      <td className="px-4 py-2 text-xs font-mono text-muted">
                        {new Date(entry.fired_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
