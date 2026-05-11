import { useEffect, useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

const initialForm = {
  room_id: 1,
  user_email: '',
  start_time: '',
  end_time: '',
}

function App() {
  const [rooms, setRooms] = useState([])
  const [bookings, setBookings] = useState([])
  const [isLoadingRooms, setIsLoadingRooms] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [form, setForm] = useState(initialForm)

  const selectedRoom = useMemo(
    () => rooms.find((room) => room.id === Number(form.room_id)),
    [rooms, form.room_id],
  )

  useEffect(() => {
    const loadRooms = async () => {
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
    }

    loadRooms()
  }, [])

  const handleInput = (event) => {
    const { name, value } = event.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const toIsoString = (value) => (value ? new Date(value).toISOString() : '')

  const onSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSuccess('')
    setIsSubmitting(true)

    const payload = {
      room_id: Number(form.room_id),
      user_email: form.user_email.trim(),
      start_time: toIsoString(form.start_time),
      end_time: toIsoString(form.end_time),
    }

    try {
      const response = await fetch(`${API_BASE}/api/bookings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}))
        throw new Error(errorBody.detail || 'Не удалось создать бронирование')
      }
      const created = await response.json()
      setBookings((prev) => [created, ...prev].slice(0, 8))
      setSuccess('Бронирование успешно создано')
      setForm((prev) => ({ ...prev, user_email: '', start_time: '', end_time: '' }))
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <span className="badge">Meeting Room Booking</span>
          <h1>Бронирование переговорок</h1>
          <p>
            Быстрый подбор свободной комнаты, проверка конфликтов по времени и создание брони
            в пару кликов.
          </p>
        </div>
      </header>

      <main className="grid">
        <section className="card">
          <div className="card-title-row">
            <h2>Новая бронь</h2>
            <span className="muted">{selectedRoom ? `Вместимость: ${selectedRoom.capacity}` : ''}</span>
          </div>

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

            <label>
              Email сотрудника
              <input
                type="email"
                name="user_email"
                placeholder="employee@company.com"
                value={form.user_email}
                onChange={handleInput}
                required
              />
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

          {error && <p className="message error">{error}</p>}
          {success && <p className="message success">{success}</p>}
        </section>

        <section className="card">
          <h2>Переговорки</h2>
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

          <h2 className="secondary-title">Последние созданные брони</h2>
          {bookings.length === 0 ? (
            <p className="muted">Пока нет созданных бронирований в этом сеансе.</p>
          ) : (
            <ul className="booking-list">
              {bookings.map((item) => (
                <li key={item.id}>
                  <div>
                    <strong>Комната #{item.room_id}</strong>
                    <span>{item.user_email}</span>
                  </div>
                  <small>
                    {new Date(item.start_time).toLocaleString()} - {new Date(item.end_time).toLocaleString()}
                  </small>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
