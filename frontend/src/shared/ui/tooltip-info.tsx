"use client";

import { Info } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";

interface TooltipInfoProps {
  content: string;
  className?: string;
}

export function TooltipInfo({ content, className = "" }: TooltipInfoProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (isVisible && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setPosition({
        top: rect.top - 10,
        left: rect.left + rect.width / 2,
      });
    }
  }, [isVisible]);

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className={`inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-100 text-blue-600 hover:bg-blue-200 transition-colors ml-1 ${className}`}
        aria-label="Mais informações"
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsVisible(!isVisible);
        }}
      >
        <Info className="w-3 h-3" />
      </button>
      {isVisible && typeof window !== 'undefined' && createPortal(
        <div
          className="fixed z-[9999] px-3 py-2 bg-gray-900 text-white text-xs rounded-md shadow-xl w-48 whitespace-normal pointer-events-none"
          style={{
            top: `${position.top}px`,
            left: `${position.left}px`,
            transform: 'translate(-50%, -100%)',
          }}
        >
          {content}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-900"></div>
        </div>,
        document.body
      )}
    </>
  );
}
