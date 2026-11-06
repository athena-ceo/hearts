// Copyright (c) 2026 Athena Decisions Systems SAS.
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Tests run as someone who prefers no motion: jsdom has no layout to fly cards across.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: query.includes("reduce"), media: query, onchange: null,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {},
    dispatchEvent: () => false,
  }),
});

// jsdom has no PointerEvent, and dragging reads the pointer's position.
class TestPointerEvent extends MouseEvent {
  pointerType: string;
  constructor(type: string, init: PointerEventInit = {}) {
    super(type, init);
    this.pointerType = init.pointerType ?? "mouse";
  }
}
Object.defineProperty(window, "PointerEvent", { writable: true, value: TestPointerEvent });

afterEach(() => {
  cleanup();
  localStorage.clear();
});
