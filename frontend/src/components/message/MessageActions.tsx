import { useState } from 'react';
import { Check, Copy, RefreshCw, ThumbsDown, ThumbsUp } from 'lucide-react';
import { apiFetch } from '../../lib/apiClient';

type MessageActionsProps = {
  question: string;
  answer: string;
  sessionId?: string | null;
  conversationId?: string | null;
  onRegenerate?: () => void;
  className?: string;
};

type Rating = 'helpful' | 'not_helpful';

/** Copy / Regenerate / 👍👎 feedback row shared by the floating chat widget
 * and the Customer Dashboard's conversation view — one implementation, one
 * `/chat/feedback` call, instead of duplicating this per surface. */
export function MessageActions({ question, answer, sessionId, conversationId, onRegenerate, className }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [rating, setRating] = useState<Rating | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState('');

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(answer);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard permission denied — silently no-op, nothing to recover.
    }
  };

  const submitFeedback = async (nextRating: Rating, withComment?: string) => {
    setRating(nextRating);
    try {
      await apiFetch('/chat/feedback', {
        method: 'POST',
        body: JSON.stringify({
          question,
          answer,
          rating: nextRating,
          comment: withComment || undefined,
          session_id: sessionId || undefined,
          conversation_id: conversationId || undefined,
        }),
      });
      setSubmitted(true);
      setShowComment(false);
    } catch {
      setRating(null);
    }
  };

  const handleThumbsUp = () => {
    if (submitted) return;
    submitFeedback('helpful');
  };

  const handleThumbsDown = () => {
    if (submitted) return;
    setRating('not_helpful');
    setShowComment(true);
  };

  return (
    <div className={`mt-2 flex flex-wrap items-center gap-1.5 ${className ?? ''}`}>
      <button
        type="button"
        onClick={handleCopy}
        className="flex items-center gap-1 rounded-full border border-ink/10 px-2.5 py-1 text-[11px] font-medium text-ink/50 transition hover:border-gold-400 hover:text-gold-700"
        aria-label="Copy response"
      >
        {copied ? <Check size={11} /> : <Copy size={11} />}
        {copied ? 'Copied' : 'Copy'}
      </button>

      {onRegenerate ? (
        <button
          type="button"
          onClick={onRegenerate}
          className="flex items-center gap-1 rounded-full border border-ink/10 px-2.5 py-1 text-[11px] font-medium text-ink/50 transition hover:border-gold-400 hover:text-gold-700"
          aria-label="Regenerate response"
        >
          <RefreshCw size={11} />
          Regenerate
        </button>
      ) : null}

      {!submitted ? (
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleThumbsUp}
            className={`rounded-full border p-1.5 transition ${
              rating === 'helpful' ? 'border-emerald-300 bg-emerald-50 text-emerald-700' : 'border-ink/10 text-ink/40 hover:text-emerald-600'
            }`}
            aria-label="Helpful"
          >
            <ThumbsUp size={11} />
          </button>
          <button
            type="button"
            onClick={handleThumbsDown}
            className={`rounded-full border p-1.5 transition ${
              rating === 'not_helpful' ? 'border-red-300 bg-red-50 text-red-600' : 'border-ink/10 text-ink/40 hover:text-red-500'
            }`}
            aria-label="Not helpful"
          >
            <ThumbsDown size={11} />
          </button>
        </div>
      ) : (
        <span className="text-[11px] font-medium text-emerald-600">Thanks for your feedback</span>
      )}

      {showComment && !submitted ? (
        <div className="mt-1.5 flex w-full items-center gap-1.5">
          <input
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What went wrong? (optional)"
            className="flex-1 rounded-full border border-ink/10 bg-paper px-3 py-1.5 text-[11px] outline-none focus:border-gold-400"
          />
          <button
            type="button"
            onClick={() => submitFeedback('not_helpful', comment.trim() || undefined)}
            className="rounded-full bg-ink px-3 py-1.5 text-[11px] font-semibold text-paper"
          >
            Submit
          </button>
        </div>
      ) : null}
    </div>
  );
}
