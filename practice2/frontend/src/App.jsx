import { useCallback, useEffect, useMemo, useState } from 'react'
import { Calendar, dateFnsLocalizer } from 'react-big-calendar'
import { format, getDay, startOfWeek } from 'date-fns'
import { ru } from 'date-fns/locale'
import 'react-big-calendar/lib/css/react-big-calendar.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
const TOKEN_KEY = 'mr_booking_token'

const localizer = dateFnsLocalizer({
  format,
  startOfWeek,
  getDay,
  locales: { ru },
})

const initialForm = {
  room_id: 1,
  start_time: '',
  end_time: '',
}

const initialNewRoom = { name: '', capacity: '' }

function initialWeekRange() {
  const start = startOfWeek(new Date(), { locale: ru })
  const end = new Date(start)
  end.setDate(end.getDate() + 6)
  end.setHours(23, 59, 59, 999)
  return { start, end }
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) ?? '')
  const [user, setUser] = useState(null)
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authMode, setAuthMode] = useState('login')

  const [rooms, setRooms] = useState([])
  const [bookings, setBookings] = useState([])
  const [calendarEvents, setCalendarEvents] = useState([])
  const [calendarRange, setCalendarRange] = useState(initialWeekRange)
  const [isLoadingRooms, setIsLoadingRooms] = useState(true)
  const [isLoadingBookings, setIsLoadingBookings] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [authBusy, setAuthBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [form, setForm] = useState(initialForm)
  const [newRoom, setNewRoom] = useState(initialNewRoom)
  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState({ name: '', capacity: '' })
  const [roomBusy, setRoomBusy] = useState(false)

  const authHeaders = useCallback(() => {
    const h = { 'Content-Type': 'application/json' }
    if (token) h.Authorization = `Bearer ${token}`
    return h
  }, [token])

  const selectedRoom = useMemo(
    () => rooms.find((room) => room.id === Number(form.room_id)),
    [rooms, form.room_id],
  )

  const roomById = useMemo(() => Object.fromEntries(rooms.map((r) => [r.id, r])), [rooms])
  const isAdmin = Boolean(user?.is_admin)

  const loadMe = useCallback(async () => {
    if (!token) {
      setUser(null)
      return
    }
    try {
      const response = await fetch(`${API_BASE}/api/auth/me`, { headers: authHeaders() })
      if (!response.ok) {
        localStorage.removeItem(TOKEN_KEY)
        setToken('')
        setUser(null)
        return
      }
      setUser(await response.json())
    } catch {
      setUser(null)
    }
  }, [token, authHeaders])

  useEffect(() => {
    loadMe()
  }, [loadMe])

  const loadRooms = useCallback(async () => {
    setIsLoadingRooms(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE}/api/rooms`)
      if (!response.ok) {
        throw new Error('Не удалось получить список переговорок')
      }
      const data = await response.json()
      setRooms(data)
      if (data.length > 0) {
        setForm((prev) => ({ ...prev, room_id: data[0].id }))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoadingRooms(false)
    }
  }, [])

  const loadBookingsForRange = useCallback(
    async (rangeStart, rangeEnd) => {
      if (!rangeStart || !rangeEnd || !token) {
        setCalendarEvents([])
        return
      }
      setIsLoadingBookings(true)
      setError('')
      try {
        const params = new URLSearchParams({
          range_start: rangeStart.toISOString(),
          range_end: rangeEnd.toISOString(),
        })
        const response = await fetch(`${API_BASE}/api/bookings?${params}`, { headers: authHeaders() })
        if (!response.ok) {
          throw new Error('Не удалось загрузить бронирования для календаря')
        }
        const data = await response.json()
        setCalendarEvents(
          data.map((b) => ({
            id: b.id,
            title: `${roomById[b.room_id]?.name ?? 'Комната ' + b.room_id} — ${b.user_email}`,
            start: new Date(b.start_time),
            end: new Date(b.end_time),
            resourceId: b.room_id,
          })),
        )
      } catch (err) {
        setError(err.message)
      } finally {
        setIsLoadingBookings(false)
      }
    },
    [roomById, token, authHeaders],
  )

  useEffect(() => {
    loadRooms()
  }, [loadRooms])

  useEffect(() => {
    loadBookingsForRange(calendarRange.start, calendarRange.end)
  }, [calendarRange, loadBookingsForRange])

  const onAuthSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSuccess('')
    setAuthBusy(true)
    const path = authMode === 'register' ? '/api/auth/register' : '/api/auth/login'
    try {
      const response = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail.trim(), password: authPassword }),
      })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(body.detail || 'Ошибка входа')
      }
      const next = body.access_token
      localStorage.setItem(TOKEN_KEY, next)
      setToken(next)
      setUser(body.user)
      setAuthPassword('')
      setSuccess(authMode === 'register' ? 'Регистрация выполнена' : 'Вход выполнен')
    } catch (err) {
      setError(err.message)
    } finally {
      setAuthBusy(false)
    }
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setToken('')
    setUser(null)
    setCalendarEvents([])
    setSuccess('Вы вышли из аккаунта')
  }

  const handleInput = (event) => {
    const { name, value } = event.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const toIsoString = (value) => (value ? new Date(value).toISOString() : '')

  const onSubmit = async (event) => {
    event.preventDefault()
    if (!token) return
    setError('')
    setSuccess('')
    setIsSubmitting(true)

    const payload = {
      room_id: Number(form.room_id),
      start_time: toIsoString(form.start_time),
      end_time: toIsoString(form.end_time),
    }

    try {
      const response = await fetch(`${API_BASE}/api/bookings`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}))
        throw new Error(errorBody.detail || 'Не удалось создать бронирование')
      }
      const created = await response.json()
      setBookings((prev) => [created, ...prev].slice(0, 8))
      setSuccess('Бронирование успешно создано')
      setForm((prev) => ({ ...prev, start_time: '', end_time: '' }))
      loadBookingsForRange(calendarRange.start, calendarRange.end)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const parseCapacity = (value) => {
    const n = Number(value)
    return Number.isFinite(n) && n > 0 ? n : null
  }

  const onCreateRoom = async (event) => {
    event.preventDefault()
    const capacity = parseCapacity(newRoom.capacity)
    if (!newRoom.name.trim() || !capacity) {
      setError('Укажите название и положительную вместимость')
      return
    }
    setRoomBusy(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE}/api/rooms`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ name: newRoom.name.trim(), capacity }),
      })
      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}))
        throw new Error(errBody.detail || 'Не удалось создать переговорку')
      }
      setNewRoom(initialNewRoom)
      setSuccess('Переговорка добавлена')
      await loadRooms()
    } catch (err) {
      setError(err.message)
    } finally {
      setRoomBusy(false)
    }
  }

  const startEdit = (room) => {
    setEditingId(room.id)
    setEditDraft({ name: room.name, capacity: String(room.capacity) })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditDraft({ name: '', capacity: '' })
  }

  const saveEdit = async (roomId) => {
    const capacity = editDraft.capacity === '' ? null : parseCapacity(editDraft.capacity)
    const name = editDraft.name.trim()
    const body = {}
    if (name) body.name = name
    if (capacity !== null) body.capacity = capacity
    if (Object.keys(body).length === 0) {
      setError('Измените название или вместимость')
      return
    }
    setRoomBusy(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE}/api/rooms/${roomId}`, {
        method: 'PATCH',
        headers: authHeaders(),
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}))
        throw new Error(errBody.detail || 'Не удалось сохранить изменения')
      }
      cancelEdit()
      setSuccess('Переговорка обновлена')
      await loadRooms()
    } catch (err) {
      setError(err.message)
    } finally {
      setRoomBusy(false)
    }
  }

  const removeRoom = async (room) => {
    if (!window.confirm(`Удалить переговорку «${room.name}»?`)) return
    setRoomBusy(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE}/api/rooms/${room.id}`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}))
        throw new Error(errBody.detail || 'Не удалось удалить переговорку')
      }
      setSuccess('Переговорка удалена')
      await loadRooms()
    } catch (err) {
      setError(err.message)
    } finally {
      setRoomBusy(false)
    }
  }

  const onCalendarRangeChange = useCallback((range) => {
    if (Array.isArray(range)) {
      const start = range[0]
      const end = range[range.length - 1]
      setCalendarRange({ start, end })
    } else if (range?.start && range?.end) {
      setCalendarRange({ start: range.start, end: range.end })
    }
  }, [])

  const eventStyleGetter = useCallback((event) => {
    const palette = [
      { bg: '#1f2747', border: '#7b8cff', fg: '#eef1ff' },
      { bg: '#16384a', border: '#4ec4e8', fg: '#e8f8ff' },
      { bg: '#2d1f4d', border: '#b894f5', fg: '#f4efff' },
      { bg: '#183c31', border: '#5cdba8', fg: '#e8fff4' },
      { bg: '#4a2328', border: '#ff9a8c', fg: '#fff2f0' },
    ]
    const idx = (event.resourceId || 0) % palette.length
    const c = palette[idx]
    return {
      style: {
        backgroundColor: c.bg,
        borderLeft: `3px solid ${c.border}`,
        borderTop: 'none',
        borderRight: 'none',
        borderBottom: 'none',
        color: c.fg,
        borderRadius: '6px',
        fontSize: '12px',
        fontWeight: 600,
        boxShadow: '0 2px 8px rgba(0,0,0,0.35)',
      },
    }
  }, [])

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero-top">
          <div>
            <span className="badge">Meeting Room Booking</span>
            <h1>Бронирование переговорок</h1>
            <p>
              Войдите, чтобы создавать брони и видеть календарь. Управление переговорками (добавление, правка, удаление)
              доступно только администратору.
            </p>
          </div>
          <div className="auth-panel">
            {user ? (
              <div className="auth-user">
                <div>
                  <strong>{user.email}</strong>
                  {isAdmin && <span className="badge-admin">админ</span>}
                </div>
                <button type="button" className="btn-secondary btn-compact" onClick={logout}>
                  Выйти
                </button>
              </div>
            ) : (
              <form className="auth-form" onSubmit={onAuthSubmit}>
                <input
                  type="email"
                  placeholder="Email"
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  required
                />
                <input
                  type="password"
                  placeholder="Пароль (мин. 6 символов)"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  minLength={6}
                  required
                />
                <div className="auth-actions">
                  <button type="submit" className="btn-compact" disabled={authBusy}>
                    {authMode === 'login' ? 'Войти' : 'Регистрация'}
                  </button>
                  <button
                    type="button"
                    className="btn-compact ghost"
                    onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
                  >
                    {authMode === 'login' ? 'Создать аккаунт' : 'Уже есть аккаунт'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </header>

      <main className="grid-main">
        <section className="card calendar-card">
          <div className="card-title-row">
            <h2>Календарь</h2>
            <span className="muted">{isLoadingBookings ? 'Загрузка…' : ''}</span>
          </div>
          {!token ? (
            <p className="muted calendar-hint">Войдите в аккаунт, чтобы видеть занятость переговорок в выбранном диапазоне.</p>
          ) : (
            <div className="rbc-wrap">
              <Calendar
                culture="ru"
                localizer={localizer}
                events={calendarEvents}
                startAccessor="start"
                endAccessor="end"
                style={{ height: 520 }}
                defaultView="week"
                views={['month', 'week', 'day', 'agenda']}
                messages={{
                  today: 'Сегодня',
                  previous: 'Назад',
                  next: 'Вперёд',
                  month: 'Месяц',
                  week: 'Неделя',
                  day: 'День',
                  agenda: 'Список',
                  date: 'Дата',
                  time: 'Время',
                  event: 'Событие',
                  showMore: (total) => `+ ещё ${total}`,
                }}
                onRangeChange={onCalendarRangeChange}
                eventPropGetter={eventStyleGetter}
              />
            </div>
          )}
        </section>

        <div className="form-row">
          <section className="card">
            <div className="card-title-row">
              <h2>Новая бронь</h2>
              <span className="muted">{selectedRoom ? `Вместимость: ${selectedRoom.capacity}` : ''}</span>
            </div>

            {!token ? (
              <p className="muted">Войдите, чтобы создать бронирование на свой аккаунт.</p>
            ) : (
              <>
                <p className="account-line">
                  Бронь создаётся для: <strong>{user?.email}</strong>
                </p>
                <form className="form" onSubmit={onSubmit}>
                  <label>
                    Переговорка
                    <select
                      name="room_id"
                      value={form.room_id}
                      onChange={handleInput}
                      disabled={isLoadingRooms || rooms.length === 0}
                    >
                      {rooms.map((room) => (
                        <option key={room.id} value={room.id}>
                          {room.name} (до {room.capacity} чел.)
                        </option>
                      ))}
                    </select>
                  </label>

                  <div className="row">
                    <label>
                      Начало
                      <input
                        type="datetime-local"
                        name="start_time"
                        value={form.start_time}
                        onChange={handleInput}
                        required
                      />
                    </label>
                    <label>
                      Окончание
                      <input
                        type="datetime-local"
                        name="end_time"
                        value={form.end_time}
                        onChange={handleInput}
                        required
                      />
                    </label>
                  </div>

                  <button type="submit" disabled={isSubmitting || isLoadingRooms}>
                    {isSubmitting ? 'Создание...' : 'Создать бронирование'}
                  </button>
                </form>
              </>
            )}

            {error && <p className="message error">{error}</p>}
            {success && <p className="message success">{success}</p>}
          </section>

          <section className="card">
            <div className="card-title-row">
              <h2>Переговорки</h2>
              <span className="muted">{isAdmin ? 'управление (админ)' : 'только просмотр'}</span>
            </div>

            {isLoadingRooms ? (
              <p className="muted">Загрузка...</p>
            ) : (
              <ul className="room-list">
                {rooms.map((room) => (
                  <li key={room.id}>
                    <strong>{room.name}</strong>
                    <span>{room.capacity} мест</span>
                  </li>
                ))}
              </ul>
            )}

            {isAdmin && (
              <>
                <h2 className="secondary-title">Админ: добавить переговорку</h2>
                <form className="form room-add" onSubmit={onCreateRoom}>
                  <div className="row">
                    <label>
                      Название
                      <input
                        type="text"
                        placeholder="Название"
                        value={newRoom.name}
                        onChange={(e) => setNewRoom((p) => ({ ...p, name: e.target.value }))}
                        disabled={roomBusy}
                      />
                    </label>
                    <label>
                      Мест
                      <input
                        type="number"
                        min={1}
                        placeholder="6"
                        value={newRoom.capacity}
                        onChange={(e) => setNewRoom((p) => ({ ...p, capacity: e.target.value }))}
                        disabled={roomBusy}
                      />
                    </label>
                  </div>
                  <button type="submit" className="btn-secondary" disabled={roomBusy || isLoadingRooms || !token}>
                    Добавить
                  </button>
                </form>

                <h2 className="secondary-title">Админ: редактирование</h2>
                <ul className="room-admin">
                  {rooms.map((room) => (
                    <li key={room.id}>
                      {editingId === room.id ? (
                        <div className="room-edit">
                          <input
                            type="text"
                            value={editDraft.name}
                            onChange={(e) => setEditDraft((d) => ({ ...d, name: e.target.value }))}
                            disabled={roomBusy}
                          />
                          <input
                            type="number"
                            min={1}
                            value={editDraft.capacity}
                            onChange={(e) => setEditDraft((d) => ({ ...d, capacity: e.target.value }))}
                            disabled={roomBusy}
                          />
                          <div className="room-actions">
                            <button type="button" className="btn-small" onClick={() => saveEdit(room.id)} disabled={roomBusy}>
                              Сохранить
                            </button>
                            <button type="button" className="btn-small ghost" onClick={cancelEdit} disabled={roomBusy}>
                              Отмена
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="room-row">
                          <div>
                            <strong>{room.name}</strong>
                            <span className="muted">{room.capacity} мест</span>
                          </div>
                          <div className="room-actions">
                            <button type="button" className="btn-small ghost" onClick={() => startEdit(room)} disabled={roomBusy}>
                              Изменить
                            </button>
                            <button type="button" className="btn-small danger" onClick={() => removeRoom(room)} disabled={roomBusy}>
                              Удалить
                            </button>
                          </div>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </>
            )}

            <h2 className="secondary-title">Последние созданные брони</h2>
            {!token ? (
              <p className="muted">Войдите, чтобы создавать брони.</p>
            ) : bookings.length === 0 ? (
              <p className="muted">Пока нет созданных бронирований в этом сеансе.</p>
            ) : (
              <ul className="booking-list">
                {bookings.map((item) => (
                  <li key={item.id}>
                    <div>
                      <strong>{roomById[item.room_id]?.name ?? 'Комната #' + item.room_id}</strong>
                      <span>{item.user_email}</span>
                    </div>
                    <small>
                      {new Date(item.start_time).toLocaleString()} — {new Date(item.end_time).toLocaleString()}
                    </small>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </main>
    </div>
  )
}

export default App
