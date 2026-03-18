'use client';

import { useRef, useState, useEffect } from 'react';
import { TranscriptSegment } from '@/lib/api';
import { formatTimestamp } from '@/lib/formatters';

interface AudioPlayerProps {
  sourceUrl: string;
  segments: TranscriptSegment[];
}

export default function AudioPlayer({ sourceUrl, segments }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, []);

  const activeSegmentIndex = segments.findIndex(
    (segment) => currentTime >= segment.start && currentTime < segment.end
  );

  const handleSegmentClick = (segment: TranscriptSegment) => {
    if (audioRef.current) {
      audioRef.current.currentTime = segment.start;
      audioRef.current.play().catch(() => null);
    }
  };

  return (
    <div className="space-y-4">
      <audio ref={audioRef} controls className="w-full">
        <source src={sourceUrl} />
        Your browser does not support audio playback.
      </audio>
      <div className="max-h-96 overflow-y-auto rounded-lg border border-gray-200 divide-y">
        {segments.map((segment, index) => {
          const isActive = index === activeSegmentIndex;
          return (
            <button
              key={`${segment.start}-${segment.end}-${index}`}
              type="button"
              onClick={() => handleSegmentClick(segment)}
              className={`w-full text-left p-3 focus:outline-none ${
                isActive ? 'bg-primary-50 border-l-4 border-primary-500' : 'bg-white'
              }`}
            >
              <div className="text-xs font-semibold text-gray-500 mb-1">
                {formatTimestamp(segment.start)} - {formatTimestamp(segment.end)}
              </div>
              <p className={`text-sm ${isActive ? 'text-primary-900' : 'text-gray-700'}`}>
                {segment.text}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
