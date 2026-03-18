'use client';

/**
 * This component provides a reusable slide viewer UI block.
 * It wraps display behavior that can be dropped into multiple pages or features.
 */
import { useState, useEffect, useImperativeHandle, forwardRef } from 'react';

interface Slide {
  slide_number: number;
  text: string;
}

interface SlideViewerProps {
  slides: Slide[];
  initialActiveSlide?: number | null;
}

export interface SlideViewerRef {
  jumpToSlide: (slideNumber: number) => void;
}

const SlideViewer = forwardRef<SlideViewerRef, SlideViewerProps>(
  ({ slides, initialActiveSlide = null }, ref) => {
    const [activeSlide, setActiveSlide] = useState<number | null>(
      initialActiveSlide ?? (slides[0]?.slide_number ?? null)
    );

    const handleSelect = (slideNumber: number) => {
      setActiveSlide(slideNumber);
      const el = document.getElementById(`slide-${slideNumber}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };

    useImperativeHandle(ref, () => ({
      jumpToSlide: handleSelect,
    }));

    // Update active slide when initialActiveSlide changes externally
    useEffect(() => {
      if (initialActiveSlide !== null && initialActiveSlide !== activeSlide) {
        handleSelect(initialActiveSlide);
      }
    }, [initialActiveSlide]);

  if (!slides || slides.length === 0) {
    return <p className="text-sm text-gray-500">No slide content available.</p>;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div className="md:col-span-1 space-y-2 max-h-80 overflow-y-auto border border-gray-200 rounded-lg p-2 bg-white">
        {slides.map((slide) => {
          const isActive = slide.slide_number === activeSlide;
          return (
            <button
              key={slide.slide_number}
              type="button"
              onClick={() => handleSelect(slide.slide_number)}
              className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium ${
                isActive ? 'bg-primary-100 text-primary-700' : 'hover:bg-gray-100 text-gray-700'
              }`}
            >
              Slide {slide.slide_number}
            </button>
          );
        })}
      </div>
      <div className="md:col-span-3 max-h-80 overflow-y-auto border border-gray-200 rounded-lg p-4 bg-white space-y-6">
        {slides.map((slide) => (
          <div
            key={slide.slide_number}
            id={`slide-${slide.slide_number}`}
            className={`p-3 rounded-lg ${
              slide.slide_number === activeSlide ? 'bg-primary-50 border border-primary-200' : ''
            }`}
          >
            <div className="text-xs font-semibold text-gray-500 mb-1">
              Slide {slide.slide_number}
            </div>
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{slide.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
});

SlideViewer.displayName = 'SlideViewer';

export default SlideViewer;

