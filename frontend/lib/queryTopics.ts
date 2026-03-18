/**
 * This file extracts and groups query topics for analytics displays.
 * It helps turn raw question history into cleaner topic summaries for the UI.
 */
const BLACKLIST_PATTERNS = [
  /teacher'?s name/i,
  /who is the teacher/i,
  /^h$/i,
  /^hi$/i,
  /^ok$/i,
  /^what'?s that$/i,
];

const STOP_WORDS = new Set([
  'the',
  'a',
  'an',
  'of',
  'to',
  'in',
  'is',
  'are',
  'there',
  'types',
  'it',
  'that',
  'this',
  'these',
  'those',
  'and',
  'or',
]);

const PREFIX_PATTERNS = [
  /^what is\s+/,
  /^what are\s+/,
  /^what does\s+/,
  /^what do\s+/,
  /^how to\s+/,
  /^how do\s+/,
  /^how does\s+/,
  /^define\s+/,
  /^explain\s+/,
  /^difference between\s+/,
  /^what'?s\s+/,
  /^whats\s+/,
];

const SYNONYM_MAP: Record<string, string> = {
  'i/o': 'io',
  io: 'io',
  syscall: 'system call',
  irq: 'interrupt',
  os: 'os',
};

const formatAcronym = (token: string) => {
  const map: Record<string, string> = {
    io: 'I/O',
    cpu: 'CPU',
    ram: 'RAM',
    dma: 'DMA',
    os: 'OS',
    api: 'API',
    irq: 'IRQ',
  };

  return map[token] || token;
};

const extractTopicTokens = (text: string) => {
  let normalized = text.toLowerCase().replace(/[^\w\s/]/g, ' ').replace(/\s+/g, ' ').trim();

  for (const pattern of PREFIX_PATTERNS) {
    if (pattern.test(normalized)) {
      normalized = normalized.replace(pattern, '').trim();
      break;
    }
  }

  Object.entries(SYNONYM_MAP).forEach(([from, to]) => {
    normalized = normalized.replace(new RegExp(`\\b${from}\\b`, 'g'), to);
  });

  return normalized
    .split(' ')
    .map((token) => token.trim())
    .filter(Boolean)
    .map((token) => {
      if (token.endsWith('s') && token.length > 3 && !token.endsWith('ss')) {
        return token.slice(0, -1);
      }

      return token;
    })
    .filter((token) => !STOP_WORDS.has(token));
};

const jaccard = (a: Set<string>, b: Set<string>) => {
  const aList = Array.from(a);
  const bList = Array.from(b);
  const intersection = new Set(aList.filter((token) => b.has(token)));
  const union = new Set([...aList, ...bList]);

  return union.size === 0 ? 0 : intersection.size / union.size;
};

const makeTopicLabel = (tokenFreq: Map<string, number>, count: number) => {
  const entries = Array.from(tokenFreq.entries()).sort((a, b) => b[1] - a[1]);
  const tokens = entries.slice(0, 3).map(([token]) => token);

  if (tokens.includes('system') && tokens.includes('call')) {
    return 'System Calls';
  }

  if (tokens.includes('io') && tokens.includes('management')) {
    return 'I/O Management';
  }

  const label = tokens
    .map((token) => formatAcronym(token))
    .map((token) => token.charAt(0).toUpperCase() + token.slice(1))
    .join(' ');

  if (tokens.length === 1 && count > 1 && !label.endsWith('s') && !label.endsWith('ing')) {
    return `${label}s`;
  }

  return label;
};

export const summarizeQuestionTopics = (questions: string[]) => {
  const clusters: Array<{
    tokenSet: Set<string>;
    tokenFreq: Map<string, number>;
    questions: string[];
  }> = [];
  let ignoredCount = 0;

  questions.forEach((question) => {
    if (!question || BLACKLIST_PATTERNS.some((pattern) => pattern.test(question.trim()))) {
      ignoredCount += 1;
      return;
    }

    const tokens = extractTopicTokens(question);
    if (tokens.length === 0) {
      ignoredCount += 1;
      return;
    }

    const tokenSet = new Set(tokens);
    let matchedCluster = clusters.find((cluster) => {
      const tokenList = Array.from(tokenSet);
      const clusterList = Array.from(cluster.tokenSet);
      const shared = tokenList.filter((token) => cluster.tokenSet.has(token)).length;
      const subset =
        tokenList.every((token) => cluster.tokenSet.has(token)) ||
        clusterList.every((token) => tokenSet.has(token));

      return jaccard(tokenSet, cluster.tokenSet) >= 0.4 || shared >= 2 || subset;
    });

    if (!matchedCluster) {
      clusters.push({
        tokenSet: new Set(tokenSet),
        tokenFreq: new Map(tokens.map((token) => [token, 1])),
        questions: [question],
      });
      return;
    }

    matchedCluster.questions.push(question);
    tokens.forEach((token) => {
      matchedCluster.tokenSet.add(token);
      matchedCluster.tokenFreq.set(token, (matchedCluster.tokenFreq.get(token) || 0) + 1);
    });
  });

  const topicsAll = clusters
    .map((cluster) => ({
      topic: makeTopicLabel(cluster.tokenFreq, cluster.questions.length),
      count: cluster.questions.length,
      questions: cluster.questions,
    }))
    .sort((a, b) => b.count - a.count);

  return {
    ignoredCount,
    recurringTopics: topicsAll.filter((topic) => topic.count >= 2),
    topicsAll,
  };
};
