import { CalendarDays, CheckCircle2, Clock3 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { apiFetch } from '../lib/apiClient';

type Slot = { time: string; available: boolean };
type DailyAvailability = { date: string; day_label: string; slots: Slot[]; fully_booked: boolean };

function formatDateLabel(iso: string, dayLabel: string) {
  const d = new Date(`${iso}T00:00:00`);
  return `${dayLabel} ${d.getDate()}/${d.getMonth() + 1}`;
}

/**
 * Public "Book a strategy session" widget — real booking logic against
 * GET/POST /appointments. Availability is always recomputed server-side
 * from today's date, so a day rolling off the window (and freshly booked
 * slots on it disappearing) is the "automatic reset" the spec asked for —
 * no client-side reset logic needed.
 */
export function AppointmentScheduler() {
  const [availability, setAvailability] = useState<DailyAvailability[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'booking' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  const loadAvailability = () => {
    apiFetch('/appointments/availability')
      .then((r) => r.json())
      .then((data: DailyAvailability[]) => {
        setAvailability(data);
        setSelectedDate((prev) => prev ?? data.find((d) => !d.fully_booked)?.date ?? null);
      })
      .catch(() => setAvailability([]));
  };

  useEffect(() => {
    loadAvailability();
  }, []);

  const activeDay = availability.find((d) => d.date === selectedDate) ?? null;

  const handleBook = async () => {
    if (!selectedDate || !selectedTime || !name.trim() || !email.trim() || status === 'booking') return;
    setStatus('booking');
    setErrorMessage('');
    try {
      const response = await apiFetch('/appointments', {
        method: 'POST',
        body: JSON.stringify({ date: selectedDate, time: selectedTime, name: name.trim(), email: email.trim() }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || 'That slot was just taken — please pick another.');
      }
      setStatus('success');
      // Reflect the now-booked slot immediately, without waiting on a refetch.
      setAvailability((prev) =>
        prev.map((day) =>
          day.date !== selectedDate
            ? day
            : {
                ...day,
                slots: day.slots.map((s) => (s.time === selectedTime ? { ...s, available: false } : s)),
                fully_booked: day.slots.every((s) => s.time === selectedTime || !s.available),
              }
        )
      );
      loadAvailability();
    } catch (error) {
      setStatus('error');
      setErrorMessage(error instanceof Error ? error.message : 'Something went wrong — please try again.');
    }
  };

  if (status === 'success') {
    return (
      <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 text-center backdrop-blur">
        <CheckCircle2 className="mx-auto text-emerald-400" size={36} />
        <p className="mt-3 font-display text-lg text-paper">Your appointment has been scheduled successfully.</p>
        <p className="mt-1 text-sm text-paper/60">
          {selectedDate ? formatDateLabel(selectedDate, activeDay?.day_label ?? '') : ''} • {selectedTime}
        </p>
        <button
          type="button"
          onClick={() => {
            setStatus('idle');
            setSelectedTime(null);
            setName('');
            setEmail('');
          }}
          className="mt-4 rounded-full border border-white/15 px-4 py-2 text-xs font-semibold text-paper/80 transition hover:text-paper"
        >
          Book another session
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
      <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gold-300">Appointment Scheduling</p>
      <h3 className="mt-3 font-display text-2xl text-paper">Book a strategy session</h3>
      <div className="mt-6 grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[1.25rem] border border-white/10 bg-black/20 p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-gold-100">
            <CalendarDays size={16} />
            Available dates
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {availability.map((day) => (
              <button
                key={day.date}
                type="button"
                disabled={day.fully_booked}
                onClick={() => {
                  setSelectedDate(day.date);
                  setSelectedTime(null);
                }}
                className={`rounded-full border px-3 py-2 text-sm transition ${
                  day.fully_booked
                    ? 'cursor-not-allowed border-white/5 text-paper/25 line-through'
                    : selectedDate === day.date
                    ? 'border-gold-400 bg-gold-400/20 text-gold-100'
                    : 'border-white/10 text-paper/80 hover:border-gold-400/50'
                }`}
              >
                {formatDateLabel(day.date, day.day_label)}
              </button>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {(activeDay?.slots ?? []).map((slot) => (
              <button
                key={slot.time}
                type="button"
                disabled={!slot.available}
                onClick={() => setSelectedTime(slot.time)}
                className={`rounded-full px-3 py-2 text-sm transition ${
                  !slot.available
                    ? 'cursor-not-allowed bg-white/5 text-paper/25 line-through'
                    : selectedTime === slot.time
                    ? 'bg-gold-400 text-ink'
                    : 'bg-gold-400/15 text-gold-100 hover:bg-gold-400/25'
                }`}
              >
                {slot.time}
              </button>
            ))}
          </div>
        </div>
        <div className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-gold-100">
            <Clock3 size={16} />
            Confirmation
          </div>
          <div className="mt-4 space-y-2 rounded-2xl bg-white p-4 text-ink">
            {selectedDate && selectedTime ? (
              <p className="font-semibold">
                {formatDateLabel(selectedDate, activeDay?.day_label ?? '')} • {selectedTime}
              </p>
            ) : (
              <p className="text-sm text-ink/50">Select a date and time to continue.</p>
            )}
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className="w-full rounded-xl border border-ink/10 bg-paper px-3 py-2 text-sm outline-none focus:border-gold-400"
            />
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              placeholder="you@company.com"
              className="w-full rounded-xl border border-ink/10 bg-paper px-3 py-2 text-sm outline-none focus:border-gold-400"
            />
            {status === 'error' ? <p className="text-xs text-red-600">{errorMessage}</p> : null}
          </div>
        </div>
      </div>
      <button
        type="button"
        onClick={handleBook}
        disabled={!selectedDate || !selectedTime || !name.trim() || !email.trim() || status === 'booking'}
        className="mt-6 w-full rounded-full bg-gold-400 px-5 py-3 text-sm font-semibold text-ink transition hover:bg-gold-300 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {status === 'booking' ? 'Booking...' : 'Confirm Booking'}
      </button>
    </div>
  );
}
