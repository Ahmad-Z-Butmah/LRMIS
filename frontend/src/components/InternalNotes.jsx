import React, { useState, useEffect } from 'react'
import { addComment, getApplicationComments } from '../api/staffConsoleApi'
import './InternalNotes.css'

const ACTOR_ID = 'staff_console'

function formatDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function InternalNotes({ notes = [], applicationId, onNoteAdded }) {
  const [text, setText]           = useState('')
  const [busy, setBusy]           = useState(false)
  const [error, setError]         = useState(null)
  const [comments, setComments]   = useState([])
  const [loadErr, setLoadErr]     = useState(null)

  // Load persisted comments from GET /applications/{id}/comments
  useEffect(() => {
    if (!applicationId) return
    setLoadErr(null)
    getApplicationComments(applicationId)
      .then((list) => setComments(list || []))
      .catch((e) => setLoadErr(e.message))
  }, [applicationId])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!text.trim()) return
    setBusy(true)
    setError(null)
    try {
      const result = await addComment(applicationId, {
        comment_text: text.trim(),
        created_by:   ACTOR_ID,
        actor_type:   'staff',
        visibility:   'staff_only',
      })
      // Add the returned comment to local list immediately
      if (result) setComments((prev) => [...prev, result])
      setText('')
      if (onNoteAdded) onNoteAdded()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  // Merge: workflow-transition notes (internal_notes) + staff comments
  const allNotes = [
    ...notes.map((n) => ({
      _source:    'workflow',
      author:     n.actor_id || n.author || n.created_by || 'system',
      visibility: n.visibility || 'internal',
      time:       n.timestamp || n.created_at,
      text:       n.text || n.content || n.note || '—',
    })),
    ...comments.map((c) => ({
      _source:    'comment',
      author:     c.created_by || c.actor_type || 'staff',
      visibility: c.visibility || 'staff_only',
      time:       c.created_at,
      text:       c.comment_text || '—',
    })),
  ].sort((a, b) => {
    if (!a.time) return 1
    if (!b.time) return -1
    return new Date(a.time) - new Date(b.time)
  })

  return (
    <div className="in">
      {loadErr && (
        <div className="alert alert--error in__error">
          Failed to load comments: {loadErr}
        </div>
      )}

      {allNotes.length === 0 ? (
        <p className="in__empty">No internal notes recorded.</p>
      ) : (
        <div className="in__list">
          {allNotes.map((note, i) => (
            <div key={i} className="in__note">
              <div className="in__meta">
                <span className="in__author">{note.author}</span>
                {note.visibility && (
                  <span className="in__vis">{note.visibility}</span>
                )}
                {note._source === 'comment' && (
                  <span className="in__src-tag">comment</span>
                )}
                {note.time && (
                  <span className="in__time">{formatDateTime(note.time)}</span>
                )}
              </div>
              <p className="in__text">{note.text}</p>
            </div>
          ))}
        </div>
      )}

      {error && <div className="alert alert--error in__error">{error}</div>}

      <form className="in__form" onSubmit={handleSubmit}>
        <div className="form-field">
          <label className="form-label">Add Internal Note (Staff Only)</label>
          <textarea
            className="form-input"
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Add a staff-only internal note…"
            disabled={busy}
          />
        </div>
        <div className="in__form-footer">
          <button
            type="submit"
            className="btn btn--primary"
            disabled={busy || !text.trim()}
          >
            {busy ? 'Saving…' : 'Add Note'}
          </button>
        </div>
      </form>
    </div>
  )
}
