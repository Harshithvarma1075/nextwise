import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api'
const algorithms = [
  { id: 'cf', name: 'Collaborative filtering', detail: 'Finds products from shared user behavior.' },
  { id: 'content', name: 'Content-based', detail: 'Matches catalog text and categories.' },
  { id: 'hybrid', name: 'Hybrid (selected)', detail: 'Validation selected the strongest CF-only blend.' },
]

async function api(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, { headers: { 'Content-Type': 'application/json', ...options.headers }, ...options })
  } catch {
    throw new Error('Cannot reach the API. Start Flask and check the API address.')
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new Error(body?.error?.message || 'The request could not be completed.')
  return body
}

function ProductCard({ product, index }) {
  return <article className="product-card">
    <span className="rank">{String(index + 1).padStart(2, '0')}</span>
    <div className="product-copy">
      <p className="eyebrow">{product.category_l1} · {product.category_l2}</p>
      <h3>{product.product_name}</h3>
      <p className="description">{product.product_description}</p>
      <div className="product-meta"><span>${product.price.toFixed(2)}</span><span>{product.gender}</span><span>{product.promoted_status === 'true' ? 'Promoted' : 'Standard'}</span></div>
    </div>
  </article>
}

function formatActivityTime(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Recorded time unavailable' : `${date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' })} UTC`
}

function ActivityPanel({ profile, activity, loading }) {
  if (!profile) return null
  return <aside className="activity-panel">
    <div className="activity-heading"><span>RECENT ACTIVITY</span><small>{profile.is_demo ? 'NEW USER' : 'RECORDED HISTORY'}</small></div>
    {profile.is_demo && <p className="activity-empty">No recorded activity yet. Recommendations use the popularity fallback.</p>}
    {loading && <p className="activity-empty">Loading recorded interactions…</p>}
    {!loading && !profile.is_demo && activity.length === 0 && <p className="activity-empty">No recent interactions were found.</p>}
    {!loading && !profile.is_demo && activity.map((event) => <div className="activity-row" key={`${event.item_id}-${event.event_timestamp}-${event.event_type}`}><span className={`event event-${event.event_type.toLowerCase()}`}>{event.event_type}</span><div><strong>{event.product_name}</strong><small>{event.category_l2} · {formatActivityTime(event.event_timestamp)}</small></div></div>)}
    {!profile.is_demo && <p className="activity-footnote">All listed events are used as recorded behavioral history; the CF model does not treat purchases as the only signal.</p>}
  </aside>
}

export default function App() {
  const [algorithm, setAlgorithm] = useState('hybrid')
  const [search, setSearch] = useState('')
  const [users, setUsers] = useState([])
  const [profile, setProfile] = useState(null)
  const [recommendation, setRecommendation] = useState(null)
  const [activity, setActivity] = useState([])
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [loadingRecommendations, setLoadingRecommendations] = useState(false)
  const [loadingActivity, setLoadingActivity] = useState(false)
  const [error, setError] = useState('')

  const findUsers = async (event) => {
    event?.preventDefault()
    setLoadingUsers(true); setError('')
    try {
      const query = search.trim() ? `&search=${encodeURIComponent(search.trim())}` : ''
      const data = await api(`/users?limit=12${query}`)
      setUsers(data.users)
    } catch (err) { setError(err.message) } finally { setLoadingUsers(false) }
  }

  useEffect(() => { findUsers() }, [])

  const chooseUser = async (user) => {
    setProfile({ ...user, is_demo: false })
    setRecommendation(null); setActivity([]); setError(''); setLoadingActivity(true)
    try {
      const data = await api(`/users/${user.user_id}/activity?limit=8`)
      setActivity(data.activity)
    } catch (err) { setError(err.message) } finally { setLoadingActivity(false) }
  }

  const createDemoUser = async () => {
    setError('')
    try {
      const data = await api('/demo-users', { method: 'POST', body: JSON.stringify({}) })
      setProfile(data.user); setRecommendation(null); setActivity([])
    } catch (err) { setError(err.message) }
  }

  const getRecommendations = async () => {
    if (!profile) { setError('Choose a dataset user or create a new demo user first.'); return }
    setLoadingRecommendations(true); setError('')
    try {
      const userParam = profile.is_demo ? '' : `&user_id=${profile.user_id}`
      const data = await api(`/recommendations?algorithm=${algorithm}&limit=10${userParam}`)
      setRecommendation(data)
    } catch (err) { setError(err.message) } finally { setLoadingRecommendations(false) }
  }

  const selectedAlgorithm = algorithms.find((item) => item.id === algorithm)
  return <main>
    <header className="hero">
      <div><p className="eyebrow accent">NXTWISE · RECOMMENDATION STUDIO</p><h1>Show the decision<br /><em>behind</em> every result.</h1></div>
      <aside className="hero-note"><span className="status-dot" />Live catalog + saved models<br /><small>Amazon Retail Demo Store synthetic data</small></aside>
    </header>

    <section className="workspace" aria-label="Recommendation controls">
      <aside className="control-panel">
        <div className="panel-heading"><span>01</span><h2>Choose a shopper</h2></div>
        <form className="search" onSubmit={findUsers}><input aria-label="Search dataset users by numeric ID" value={search} onChange={(event) => setSearch(event.target.value.replace(/\D/g, ''))} placeholder="Search user ID" inputMode="numeric" /><button disabled={loadingUsers}>{loadingUsers ? '…' : 'Find'}</button></form>
        <div className="user-list" aria-live="polite">{users.map((user) => <button className={`user-row ${profile?.user_id === user.user_id ? 'selected' : ''}`} key={user.user_id} onClick={() => chooseUser(user)}><strong>User {user.user_id}</strong><span>Age {user.age} · {user.gender}</span></button>)}</div>
        <button className="demo-button" onClick={createDemoUser}>＋ Create new demo user<span>Shows cold-start popularity fallback</span></button>
      </aside>

      <section className="results-panel">
        <div className="panel-heading"><span>02</span><h2>Select the method</h2></div>
        <div className="algorithm-grid">{algorithms.map((item) => <button key={item.id} className={`algorithm ${algorithm === item.id ? 'active' : ''}`} onClick={() => { setAlgorithm(item.id); setRecommendation(null) }}><strong>{item.name}</strong><span>{item.detail}</span></button>)}</div>
        <div className="profile-bar"><div>{profile ? <><span className="profile-label">ACTIVE SHOPPER</span><strong>{profile.is_demo ? 'New demo user' : `Dataset user ${profile.user_id}`}</strong><small>{profile.is_demo ? 'No history — popularity fallback will be used.' : `Age ${profile.age} · ${profile.gender}`}</small></> : <><span className="profile-label">NO SHOPPER SELECTED</span><strong>Pick a user to begin</strong></>}</div><button className="primary" onClick={getRecommendations} disabled={loadingRecommendations || loadingActivity}>{loadingRecommendations ? 'Building list…' : 'Get recommendations'}</button></div>
        {error && <div className="error" role="alert">{error}</div>}
        <ActivityPanel profile={profile} activity={activity} loading={loadingActivity} />
        {!recommendation && !loadingRecommendations && <div className="empty"><span>⌁</span><h2>Ready when you are.</h2><p>{selectedAlgorithm.detail} Choose a shopper, then request a Top-10 list.</p></div>}
        {loadingRecommendations && <div className="empty"><span className="spinner" /><h2>Ranking products…</h2><p>Using the saved {selectedAlgorithm.name.toLowerCase()} model.</p></div>}
        {recommendation && <><div className="result-summary"><div><span className={`route ${recommendation.personalized ? 'personalized' : ''}`}>{recommendation.personalized ? 'PERSONALIZED' : 'COLD START'}</span><strong>{recommendation.route.replaceAll('_', ' ')}</strong></div><p>{recommendation.personalized ? 'Products are ranked from the chosen model and this shopper’s recorded behavior.' : 'This shopper has no recorded behavior, so the global popularity fallback is shown.'}</p></div><div className="product-grid">{recommendation.recommendations.map((product, index) => <ProductCard product={product} index={index} key={product.item_id} />)}</div></>}
      </section>
    </section>
    <footer>Evaluation note: hybrid is displayed for comparison; validation selected a CF-only blend. New demo users are temporary and are not written to MySQL.</footer>
  </main>
}
