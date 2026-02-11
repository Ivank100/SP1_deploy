'use client';

import { Flashcard } from '@/lib/api';
import { useEffect, useMemo, useState } from 'react';

interface FlashcardsProps {
  flashcards: Flashcard[];
}

export default function Flashcards({ flashcards }: FlashcardsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [deletedIds, setDeletedIds] = useState<Set<number>>(new Set());
  const [reviewById, setReviewById] = useState<Record<number, 'missed' | 'got' | null>>({});
  const [ratingById, setRatingById] = useState<Record<number, 'good' | 'bad' | null>>({});

  useEffect(() => {
    setDeletedIds(new Set());
    setActiveIndex(0);
    setShowAnswer(false);
    setReviewById({});
    setRatingById({});
  }, [flashcards]);

  const visibleCards = useMemo(
    () => flashcards.filter((card) => !deletedIds.has(card.id)),
    [flashcards, deletedIds],
  );

  useEffect(() => {
    if (activeIndex >= visibleCards.length && visibleCards.length > 0) {
      setActiveIndex(visibleCards.length - 1);
      setShowAnswer(false);
    }
  }, [activeIndex, visibleCards.length]);

  const activeCard = visibleCards[activeIndex];
  const activeReview = activeCard ? reviewById[activeCard.id] ?? null : null;
  const activeRating = activeCard ? ratingById[activeCard.id] ?? null : null;
  const missedTotal = Object.values(reviewById).filter((value) => value === 'missed').length;
  const gotTotal = Object.values(reviewById).filter((value) => value === 'got').length;
  const goodTotal = Object.values(ratingById).filter((value) => value === 'good').length;
  const badTotal = Object.values(ratingById).filter((value) => value === 'bad').length;

  const handleNext = () => {
    if (visibleCards.length === 0) {
      return;
    }
    setActiveIndex((prev) => (prev + 1) % visibleCards.length);
    setShowAnswer(false);
  };

  const handlePrevious = () => {
    if (visibleCards.length === 0) {
      return;
    }
    setActiveIndex((prev) => (prev - 1 + visibleCards.length) % visibleCards.length);
    setShowAnswer(false);
  };

  const handleDelete = () => {
    if (!activeCard) {
      return;
    }
    setDeletedIds((prev) => new Set(prev).add(activeCard.id));
    setShowAnswer(false);
  };

  const toggleReview = (value: 'missed' | 'got') => {
    if (!activeCard) {
      return;
    }
    setReviewById((prev) => ({
      ...prev,
      [activeCard.id]: prev[activeCard.id] === value ? null : value,
    }));
  };

  const toggleRating = (value: 'good' | 'bad') => {
    if (!activeCard) {
      return;
    }
    setRatingById((prev) => ({
      ...prev,
      [activeCard.id]: prev[activeCard.id] === value ? null : value,
    }));
  };

  if (!flashcards || flashcards.length === 0) {
    return (
      <div className="text-sm text-gray-500 bg-gray-50 border border-dashed border-gray-200 rounded-lg p-4 text-center">
        Flashcards will appear here after you generate them.
      </div>
    );
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="w-full rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm font-semibold text-gray-900 shadow-sm hover:bg-gray-50"
      >
        Open Flashcards
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 px-4 py-6">
          <div className="w-full max-w-2xl rounded-2xl bg-[#1F2328] text-white shadow-xl">
            <div className="flex items-start justify-between border-b border-white/10 px-6 py-4">
              <div>
                <h3 className="text-lg font-semibold">Flashcards</h3>
                <p className="text-xs text-white/60">Auto-generated study cards.</p>
              </div>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="text-xs text-white/60 hover:text-white"
              >
                Close
              </button>
            </div>

            <div className="px-6 py-6">
              <div className="mb-4 flex items-center justify-between text-xs text-white/60">
                <span>{visibleCards.length ? `${activeIndex + 1}/${visibleCards.length} cards` : '0 cards'}</span>
                <button
                  type="button"
                  onClick={handleDelete}
                  className="rounded-md border border-white/10 px-2 py-1 text-xs text-white/60 hover:text-white"
                >
                  Delete
                </button>
              </div>

              <div
                onClick={() => setShowAnswer((prev) => !prev)}
                className="flex min-h-[240px] cursor-pointer flex-col items-center justify-center rounded-2xl bg-[#2A2F36] px-6 py-8 text-center shadow-inner"
              >
                <div className="text-xs uppercase tracking-widest text-white/50">
                  {showAnswer ? 'Answer' : 'Question'}
                </div>
                <div className="mt-4 text-2xl font-semibold leading-snug">
                  {activeCard
                    ? showAnswer
                      ? activeCard.back || (activeCard as any).answer || ''
                      : activeCard.front || (activeCard as any).question || ''
                    : 'No cards available'}
                </div>
                {!showAnswer && (
                  <div className="mt-6 text-xs text-white/50">See answer</div>
                )}
              </div>

              <div className="mt-6 flex items-center justify-between">
                <button
                  type="button"
                  onClick={handlePrevious}
                  className="rounded-full border border-white/10 px-4 py-2 text-xs text-white/70 hover:text-white"
                >
                  Previous
                </button>
                <button
                  type="button"
                  onClick={handleNext}
                  className="rounded-full border border-white/10 px-4 py-2 text-xs text-white/70 hover:text-white"
                >
                  Next
                </button>
              </div>

              <div className="mt-6 flex items-center justify-center gap-4">
                <button
                  type="button"
                  onClick={() => toggleReview('missed')}
                  className={`rounded-full border px-4 py-2 text-xs ${
                    activeReview === 'missed'
                      ? 'border-red-400 text-red-100 bg-red-500/10'
                      : 'border-red-500/40 text-red-200 hover:border-red-400'
                  }`}
                >
                  Missed it · {missedTotal}
                </button>
                <button
                  type="button"
                  onClick={() => toggleReview('got')}
                  className={`rounded-full border px-4 py-2 text-xs ${
                    activeReview === 'got'
                      ? 'border-emerald-400 text-emerald-100 bg-emerald-500/10'
                      : 'border-emerald-500/40 text-emerald-200 hover:border-emerald-400'
                  }`}
                >
                  Got it · {gotTotal}
                </button>
              </div>

              <div className="mt-6 flex items-center justify-center gap-4 text-xs text-white/70">
                <button
                  type="button"
                  onClick={() => toggleRating('good')}
                  className={`rounded-full border px-4 py-2 ${
                    activeRating === 'good'
                      ? 'border-white/50 text-white bg-white/10'
                      : 'border-white/10 hover:text-white'
                  }`}
                >
                  Good content · {goodTotal}
                </button>
                <button
                  type="button"
                  onClick={() => toggleRating('bad')}
                  className={`rounded-full border px-4 py-2 ${
                    activeRating === 'bad'
                      ? 'border-white/50 text-white bg-white/10'
                      : 'border-white/10 hover:text-white'
                  }`}
                >
                  Bad content · {badTotal}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

