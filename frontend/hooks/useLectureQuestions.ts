'use client';

import { Dispatch, FormEvent, SetStateAction, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiClient, QueryHistoryItem, QueryResponse, User } from '@/lib/api';
import {
  detectLectureQueryMode,
  getChatMessageList,
  getFilteredAndSortedHistory,
  getVisibleHistory,
  LectureQuestionFilter,
  LectureQuestionSort,
} from '@/lib/lectureAnalytics';

export function useLectureQuestions(lectureId: number, currentUser: User | null) {
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [currentAnswer, setCurrentAnswer] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [showRecentQuestions, setShowRecentQuestions] = useState(true);
  const [questionFilter, setQuestionFilter] = useState<LectureQuestionFilter>('all');
  const [questionSort, setQuestionSort] = useState<LectureQuestionSort>('newest');
  const [faqQuestionIds, setFaqQuestionIds] = useState<Set<number>>(new Set());
  const [pinnedQuestionIds, setPinnedQuestionIds] = useState<Set<number>>(new Set());
  const [hiddenQuestionIds, setHiddenQuestionIds] = useState<Set<number>>(new Set());
  const [manualAnswers, setManualAnswers] = useState<Record<number, string>>({});
  const [answerDrafts, setAnswerDrafts] = useState<Record<number, string>>({});
  const [activeAnswerId, setActiveAnswerId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadHistory = useCallback(async () => {
    try {
      const response = await apiClient.getQueryHistory(lectureId);
      setHistory(response.queries);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  }, [lectureId]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [asking, currentAnswer, history]);

  const handleSubmit = useCallback(async (e?: FormEvent) => {
    e?.preventDefault();
    if (!question.trim() || asking) {
      return;
    }

    setAsking(true);
    setCurrentAnswer(null);

    try {
      const response = await apiClient.queryLecture(lectureId, question, 5, detectLectureQueryMode(question));
      setCurrentAnswer(response);
      setQuestion('');
      await loadHistory();
      setCurrentAnswer(null);
    } catch (error: any) {
      console.error('Failed to query:', error);
      alert(error.response?.data?.detail || 'Failed to get answer');
    } finally {
      setAsking(false);
    }
  }, [asking, lectureId, loadHistory, question]);

  const toggleId = useCallback((setter: Dispatch<SetStateAction<Set<number>>>, id: number) => {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const visibleHistory = useMemo(() => {
    const currentUserEmail =
      currentUser?.role === 'student' && currentUser.email ? currentUser.email : null;
    return getVisibleHistory(history, currentUserEmail);
  }, [currentUser?.email, currentUser?.role, history]);

  const chatMessageList = useMemo(() => getChatMessageList(visibleHistory), [visibleHistory]);

  const sortedHistory = useMemo(
    () =>
      getFilteredAndSortedHistory({
        history: visibleHistory,
        filter: questionFilter,
        sort: questionSort,
        hiddenQuestionIds,
        faqQuestionIds,
        pinnedQuestionIds,
      }),
    [faqQuestionIds, hiddenQuestionIds, pinnedQuestionIds, questionFilter, questionSort, visibleHistory]
  );

  const toggleFaqQuestion = useCallback((id: number) => {
    toggleId(setFaqQuestionIds, id);
  }, [toggleId]);

  const togglePinnedQuestion = useCallback((id: number) => {
    toggleId(setPinnedQuestionIds, id);
  }, [toggleId]);

  const toggleHiddenQuestion = useCallback((id: number) => {
    toggleId(setHiddenQuestionIds, id);
  }, [toggleId]);

  return {
    activeAnswerId,
    answerDrafts,
    asking,
    chatMessageList,
    currentAnswer,
    faqQuestionIds,
    handleSubmit,
    hiddenQuestionIds,
    history,
    loadHistory,
    manualAnswers,
    messagesEndRef,
    pinnedQuestionIds,
    question,
    questionFilter,
    questionSort,
    setActiveAnswerId,
    setAnswerDrafts,
    setManualAnswers,
    setQuestion,
    setQuestionFilter,
    setQuestionSort,
    setShowRecentQuestions,
    showRecentQuestions,
    sortedHistory,
    toggleFaqQuestion,
    toggleHiddenQuestion,
    toggleId,
    togglePinnedQuestion,
  };
}

export type LectureQuestionsState = ReturnType<typeof useLectureQuestions>;
