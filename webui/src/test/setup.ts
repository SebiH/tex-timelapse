import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// `globals: false` in vite.config.ts means RTL's own auto-registered
// `afterEach(cleanup)` never fires (it only self-registers when `afterEach`
// is already a global), so without this every render() would keep piling
// its DOM onto the previous test's.
afterEach(() => {
    cleanup();
});

// jsdom doesn't implement these; several Radix primitives used throughout the
// app (Select, Slider, AlertDialog, ...) reach for them even when a test
// never opens/animates anything, so they're polyfilled globally rather than
// per-test.

const noop = () => undefined;

if (!window.matchMedia) {
    window.matchMedia = (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: noop,
        removeListener: noop,
        addEventListener: noop,
        removeEventListener: noop,
        dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}

if (!window.ResizeObserver) {
    window.ResizeObserver = class ResizeObserver {
        observe = noop;
        unobserve = noop;
        disconnect = noop;
    };
}

if (!Element.prototype.hasPointerCapture) {
    Element.prototype.hasPointerCapture = () => false;
}
if (!Element.prototype.setPointerCapture) {
    Element.prototype.setPointerCapture = noop;
}
if (!Element.prototype.releasePointerCapture) {
    Element.prototype.releasePointerCapture = noop;
}
if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = noop;
}
