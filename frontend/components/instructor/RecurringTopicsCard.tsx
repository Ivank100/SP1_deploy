'use client';

/**
 * This component renders instructor-focused UI for recurring topics card.
 * It displays analytics or workflow information used on instructor screens.
 */
import { summarizeQuestionTopics } from '@/lib/queryTopics';

type RecurringTopicsCardProps = {
  questions: string[];
  showAll: boolean;
  onToggleShowAll: (showAll: boolean) => void;
};

export default function RecurringTopicsCard({
  questions,
  showAll,
  onToggleShowAll,
}: RecurringTopicsCardProps) {
  const { ignoredCount, recurringTopics, topicsAll } = summarizeQuestionTopics(questions);
  const visibleTopics = showAll ? topicsAll : topicsAll.slice(0, 2);
  const remainingTopicCount = Math.max(0, topicsAll.length - visibleTopics.length);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xl font-semibold text-gray-900">Course Overview</h2>
        <span className="text-xs text-gray-500">{recurringTopics.length} recurring topics</span>
      </div>
      <p className="text-sm text-gray-500 mb-4">Key concepts that students are repeatedly confused about.</p>

      {ignoredCount > 0 && (
        <p className="text-xs text-gray-500 mb-3">
          {ignoredCount} question{ignoredCount === 1 ? '' : 's'} ignored (non-conceptual).
        </p>
      )}

      {visibleTopics.length === 0 ? (
        <p className="text-sm text-gray-500">No topics yet.</p>
      ) : (
        <div className="space-y-2">
          {visibleTopics.map((topic, index) => (
            <div key={`${topic.topic}-${index}`} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
              <div className="flex items-start justify-between mb-1">
                <p className="font-medium text-gray-900">
                  {index + 1}. {topic.topic}
                </p>
                <span className="text-xs text-gray-500 bg-white px-2 py-1 rounded">{topic.count} questions</span>
              </div>
              <div className="mt-2 text-xs text-gray-600 space-y-1">
                {topic.questions.slice(0, 2).map((question, questionIndex) => (
                  <p key={questionIndex} className="pl-2 border-l-2 border-gray-300">
                    "{question}"
                  </p>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {remainingTopicCount > 0 && !showAll && (
        <button
          type="button"
          onClick={() => onToggleShowAll(true)}
          className="mt-3 text-sm text-gray-600 hover:text-gray-800"
        >
          Show more (+{remainingTopicCount} remaining topics)
        </button>
      )}

      {showAll && topicsAll.length > 2 && (
        <button
          type="button"
          onClick={() => onToggleShowAll(false)}
          className="mt-3 text-sm text-gray-600 hover:text-gray-800"
        >
          Show less
        </button>
      )}
    </div>
  );
}
