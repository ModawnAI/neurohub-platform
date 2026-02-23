"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

/**
 * Manages focus when routes change for WCAG 2.1 AA compliance.
 * Moves focus to the main content area on navigation.
 */
export function RouteFocusManager() {
  const pathname = usePathname();
  const isFirstRender = useRef(true);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    // On route change, move focus to main content
    const main = document.querySelector("main") || document.querySelector("[role='main']");
    if (main instanceof HTMLElement) {
      main.setAttribute("tabindex", "-1");
      main.focus({ preventScroll: false });
      // Remove tabindex after focus so it doesn't interfere with tab order
      const handler = () => main.removeAttribute("tabindex");
      main.addEventListener("blur", handler, { once: true });
    }
  }, [pathname]);

  return null;
}
