"use client";

import { cn } from "@/lib/utils";
import {
  type MouseEvent,
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";

const MouseEnterContext = createContext<{
  isMouseEntered: boolean;
}>({ isMouseEntered: false });

export function useMouseEnter() {
  return useContext(MouseEnterContext);
}

interface CardContainerProps {
  children: ReactNode;
  className?: string;
  containerClassName?: string;
}

export function CardContainer({
  children,
  className,
  containerClassName,
}: CardContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isMouseEntered, setIsMouseEntered] = useState(false);

  const handleMouseMove = useCallback((e: MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const { left, top, width, height } =
      containerRef.current.getBoundingClientRect();
    const x = (e.clientX - left - width / 2) / 25;
    const y = (e.clientY - top - height / 2) / 25;
    containerRef.current.style.transform = `rotateY(${x}deg) rotateX(${-y}deg)`;
  }, []);

  const handleMouseEnter = useCallback(() => {
    setIsMouseEntered(true);
    if (containerRef.current) {
      containerRef.current.style.transition = "transform 0.1s ease";
    }
  }, []);

  const handleMouseLeave = useCallback(() => {
    setIsMouseEntered(false);
    if (containerRef.current) {
      containerRef.current.style.transition = "transform 0.5s ease";
      containerRef.current.style.transform = "rotateY(0deg) rotateX(0deg)";
    }
  }, []);

  return (
    <MouseEnterContext.Provider value={{ isMouseEntered }}>
      <div
        className={cn("flex items-center justify-center", containerClassName)}
        style={{ perspective: "1000px" }}
      >
        <div
          ref={containerRef}
          className={cn(
            "relative flex items-center justify-center transition-all duration-200 ease-linear",
            className,
          )}
          style={{ transformStyle: "preserve-3d" }}
          onMouseMove={handleMouseMove}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          {children}
        </div>
      </div>
    </MouseEnterContext.Provider>
  );
}

interface CardBodyProps {
  children: ReactNode;
  className?: string;
}

export function CardBody({ children, className }: CardBodyProps) {
  return (
    <div
      className={cn(
        "h-auto w-auto [transform-style:preserve-3d] [&>*]:[transform-style:preserve-3d]",
        className,
      )}
    >
      {children}
    </div>
  );
}

interface CardItemProps {
  children: ReactNode;
  className?: string;
  translateZ?: number | string;
  as?: React.ElementType;
}

export function CardItem({
  children,
  className,
  translateZ = 0,
  as: Component = "div",
}: CardItemProps) {
  const { isMouseEntered } = useMouseEnter();

  return (
    <Component
      className={cn("", className)}
      style={{
        transform: isMouseEntered
          ? `translateZ(${translateZ}px)`
          : "translateZ(0px)",
        transition: "transform 0.2s ease",
      }}
    >
      {children}
    </Component>
  );
}
