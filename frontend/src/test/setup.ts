import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
    cleanup();
});

Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: (query: string) => ({
        addEventListener: () => undefined,
        addListener: () => undefined,
        dispatchEvent: () => false,
        matches: false,
        media: query,
        onchange: null,
        removeEventListener: () => undefined,
        removeListener: () => undefined,
    }),
    writable: true,
});

class ResizeObserverStub implements ResizeObserver {
    disconnect() {}
    observe() {}
    unobserve() {}
}

window.ResizeObserver = ResizeObserverStub;

Object.defineProperties(HTMLElement.prototype, {
    hasPointerCapture: {
        configurable: true,
        value: () => false,
    },
    releasePointerCapture: {
        configurable: true,
        value: () => undefined,
    },
    scrollIntoView: {
        configurable: true,
        value: () => undefined,
    },
    setPointerCapture: {
        configurable: true,
        value: () => undefined,
    },
});
