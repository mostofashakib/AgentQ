// frontend/app/(main)/alerts/page.tsx
'use client'
import { useEffect, useState } from 'react'
import { api, type AlertRule, type AlertHistory } from '@/lib/api'

const THREATS = ['injection', 'scope', 'exfiltration', 'behavioral', 'integrity']
const SEVERITIES = ['low', 'medium', 'high', 'critical']
type ConditionType = 'none' | 'severity' | 'threat_class' | 'unsupported'
type ChannelType = 'webhook' | 'slack' | 'email'

const EMPTY_FORM: Omit<AlertRule, 'id' | 'created_at'> = {
  name: '',
  conditions: {},
  channels: [],
  frequency_limit: 1,
  cooldown_minutes: 60,
  enabled: true,
}

function conditionsToForm(conditions: Record<string, string>): { type: ConditionType; value: string; raw?: Record<string, string> } {
  const keys = Object.keys(conditions ?? {})
  if (keys.length === 0) return { type: 'none', value: '' }
  if (keys.length === 1 && keys[0] === 'severity') return { type: 'severity', value: conditions.severity }
  if (keys.length === 1 && keys[0] === 'threat_class') return { type: 'threat_class', value: conditions.threat_class }
  return { type: 'unsupported', value: '', raw: conditions }
}

function formToConditions(type: ConditionType, value: string, rawConditions: Record<string, string> | null): Record<string, string> {
  if (type === 'unsupported') return rawConditions ?? {}
  if (type === 'none' || !value) return {}
  return { [type]: value }
}

function channelToForm(channels: AlertRule['channels']): { type: ChannelType; url: string; to: string } {
  const c = channels[0]
  if (!c) return { type: 'webhook', url: '', to: '' }
  return {
    type: (c.type as ChannelType) ?? 'webhook',
    url: (c.url as string) ?? '',
    to: (c.to as string) ?? '',
  }
}

function formToChannels(type: ChannelType, url: string, to: string): AlertRule['channels'] {
  if (type === 'email') return to ? [{ type: 'email', to }] : []
  return url ? [{ type, url }] : []
}

export default function AlertsPage() {
  const [tab, setTab] = useState<'rules' | 'history'>('rules')

  // Rules state
  const [rules, setRules] = useState<AlertRule[]>([])
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formName, setFormName] = useState('')
  const [formConditionType, setFormConditionType] = useState<ConditionType>('none')
  const [formConditionValue, setFormConditionValue] = useState('')
  const [formRawConditions, setFormRawConditions] = useState<Record<string, string> | null>(null)
  const [formChannelType, setFormChannelType] = useState<ChannelType>('webhook')
  const [formChannelUrl, setFormChannelUrl] = useState('')
  const [formChannelTo, setFormChannelTo] = useState('')
  const [formFrequency, setFormFrequency] = useState(1)
  const [formCooldown, setFormCooldown] = useState(60)
  const [formEnabled, setFormEnabled] = useState(true)
  const [formError, setFormError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  // History state
  const [history, setHistory] = useState<AlertHistory[]>([])

  useEffect(() => {
    api.alerts.rules.list().then(setRules).catch(() => {})
  }, [])

  useEffect(() => {
    if (tab === 'history') api.alerts.history.list().then(setHistory).catch(() => {})
  }, [tab])

  function openNewForm() {
    setEditingId(null)
    setFormName(EMPTY_FORM.name)
    setFormConditionType('none')
    setFormConditionValue('')
    setFormRawConditions(null)
    setFormChannelType('webhook')
    setFormChannelUrl('')
    setFormChannelTo('')
    setFormFrequency(EMPTY_FORM.frequency_limit)
    setFormCooldown(EMPTY_FORM.cooldown_minutes)
    setFormEnabled(EMPTY_FORM.enabled)
    setFormError(null)
    setShowForm(true)
  }

  function openEditForm(rule: AlertRule) {
    setEditingId(rule.id)
    setFormName(rule.name)
    const cond = conditionsToForm(rule.conditions)
    setFormConditionType(cond.type)
    setFormConditionValue(cond.value)
    setFormRawConditions(cond.type === 'unsupported' ? cond.raw ?? rule.conditions : null)
    const chan = channelToForm(rule.channels)
    setFormChannelType(chan.type)
    setFormChannelUrl(chan.url)
    setFormChannelTo(chan.to)
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
    const body: Omit<AlertRule, 'id' | 'created_at'> = {
      name: formName,
      conditions: formToConditions(formConditionType, formConditionValue, formRawConditions),
      channels: formToChannels(formChannelType, formChannelUrl, formChannelTo),
      frequency_limit: formFrequency,
      cooldown_minutes: formCooldown,
      enabled: formEnabled,
    }
    if (body.channels.length === 0) {
      setFormError('Provide a URL (webhook/Slack) or address (email) for the channel')
      return
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
    try {
      await api.alerts.rules.delete(id)
      setRules(prev => prev.filter(r => r.id !== id))
    } catch {
      // no-op: keep UI state unchanged if delete fails
    }
  }

  async function toggleEnabled(rule: AlertRule) {
    try {
      const updated = await api.alerts.rules.update(rule.id, {
        name: rule.name,
        conditions: rule.conditions,
        channels: rule.channels,
        frequency_limit: rule.frequency_limit,
        cooldown_minutes: rule.cooldown_minutes,
        enabled: !rule.enabled,
      })
      setRules(prev => prev.map(r => (r.id === rule.id ? updated : r)))
    } catch {
      // no-op: keep UI state unchanged if toggle fails
    }
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
                  <label className="block text-xs text-muted mb-1">Condition</label>
                  <div className="flex gap-2">
                    <select
                      value={formConditionType}
                      onChange={e => {
                        setFormConditionType(e.target.value as ConditionType)
                        setFormConditionValue('')
                        setFormRawConditions(null)
                      }}
                      className="rounded border border-border bg-surface text-sm px-2 py-1.5 text-text focus:outline-none focus:border-cyan/60"
                    >
                      <option value="none">Any (wildcard)</option>
                      <option value="severity">Severity</option>
                      <option value="threat_class">Threat class</option>
                      {formConditionType === 'unsupported' && (
                        <option value="unsupported" disabled>Advanced (preserved as-is)</option>
                      )}
                    </select>
                    {formConditionType === 'unsupported' ? (
                      <div className="flex-1 rounded border border-border bg-surface/50 text-xs px-2 py-1.5 text-muted italic">
                        Advanced condition (not editable here) — switch to Severity/Threat class/Any to replace it
                      </div>
                    ) : formConditionType !== 'none' && (
                      <select
                        value={formConditionValue}
                        onChange={e => setFormConditionValue(e.target.value)}
                        className="flex-1 rounded border border-border bg-surface text-sm px-2 py-1.5 text-text focus:outline-none focus:border-cyan/60"
                      >
                        <option value="">Select…</option>
                        {(formConditionType === 'severity' ? SEVERITIES : THREATS).map(v => (
                          <option key={v} value={v}>{v}</option>
                        ))}
                      </select>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-xs text-muted mb-1">Channel</label>
                  <div className="flex gap-2">
                    <select
                      value={formChannelType}
                      onChange={e => setFormChannelType(e.target.value as ChannelType)}
                      className="rounded border border-border bg-surface text-sm px-2 py-1.5 text-text focus:outline-none focus:border-cyan/60"
                    >
                      <option value="webhook">Webhook</option>
                      <option value="slack">Slack</option>
                      <option value="email">Email</option>
                    </select>
                    {formChannelType === 'email' ? (
                      <input
                        type="email"
                        value={formChannelTo}
                        onChange={e => setFormChannelTo(e.target.value)}
                        placeholder="you@example.com"
                        className="flex-1 rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60"
                      />
                    ) : (
                      <input
                        type="text"
                        value={formChannelUrl}
                        onChange={e => setFormChannelUrl(e.target.value)}
                        placeholder="https://..."
                        className="flex-1 rounded border border-border bg-surface text-sm px-3 py-1.5 text-text focus:outline-none focus:border-cyan/60"
                      />
                    )}
                  </div>
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
