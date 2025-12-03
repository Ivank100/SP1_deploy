'use client';

import { Flashcard } from '@/lib/api';

interface FlashcardsProps {
  flashcards: Flashcard[];
}

export default function Flashcards({ flashcards }: FlashcardsProps) {
  if (!flashcards || flashcards.length === 0) {
    return (
      <div className="text-sm text-gray-500 bg-gray-50 border border-dashed border-gray-200 rounded-lg p-4 text-center">
        Flashcards will appear here after you generate them.
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {flashcards.map((card) => (
        <div
          key={card.id}
          className="border border-gray-200 rounded-lg p-4 bg-white shadow-sm hover:shadow transition-shadow"
        >
          <div className="text-xs font-semibold uppercase text-primary-600 mb-2">
            Question
          </div>
          <p className="text-gray-900 font-medium mb-3 whitespace-pre-wrap">{card.front}</p>
          <div className="text-xs font-semibold uppercase text-gray-500 mb-2">
            Answer
          </div>
          <p className="text-gray-700 whitespace-pre-wrap">{card.back}</p>
          {card.page_number && (
            <p className="mt-3 text-xs text-gray-500">Page {card.page_number}</p>
          )}
        </div>
      ))}
    </div>
  );
}

