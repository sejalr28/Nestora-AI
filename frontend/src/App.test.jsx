import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import App from "./App";

vi.mock("./api/waterSchedule", () => ({
  waterScheduleApi: {
    list: vi.fn().mockResolvedValue([
      { id: 1, source: "corporation", start_time: "08:00:00", end_time: "10:00:00", note: "Fill early" },
      { id: 2, source: "bore", start_time: "21:00:00", end_time: "01:00:00", note: null },
    ]),
    update: vi.fn(),
  },
}));

vi.mock("./api/buildings", () => ({
  buildingsApi: {
    list: vi.fn().mockResolvedValue([{ id: 1, name: "Building 7", has_bore_water: true }]),
    create: vi.fn(),
  },
}));

vi.mock("./api/flats", () => ({
  flatsApi: {
    listByBuilding: vi.fn().mockResolvedValue([]),
    create: vi.fn(),
    update: vi.fn(),
  },
}));

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );
}

describe("App routing + layout", () => {
  it("redirects the index route to Water Schedule", async () => {
    renderAt("/");
    // Water Schedule fetches on mount, so the heading appears after that
    // resolves -- findByRole waits for it instead of asserting synchronously.
    expect(await screen.findByRole("heading", { name: "Water Schedule" })).toBeInTheDocument();
  });

  it("renders all five nav links in the sidebar", async () => {
    renderAt("/water-schedule");
    for (const label of ["Water Schedule", "Buildings", "Vendors", "Residents", "Service Requests"]) {
      expect(screen.getAllByRole("link", { name: label }).length).toBeGreaterThan(0);
    }
    // Let WaterSchedulePage's fetch-on-mount settle before the test ends,
    // so its state update doesn't land after unmount (act() warning).
    await screen.findByRole("heading", { name: "Water Schedule" });
  });

  it("navigates to a different page when a sidebar link is clicked", async () => {
    const user = userEvent.setup();
    renderAt("/water-schedule");

    expect(await screen.findByRole("heading", { name: "Water Schedule" })).toBeInTheDocument();

    // Desktop and mobile sidebars both render "Buildings" links (mobile one
    // is hidden via CSS, not absent from the DOM) -- click the first.
    const buildingsLinks = screen.getAllByRole("link", { name: "Buildings" });
    await user.click(buildingsLinks[0]);

    expect(await screen.findByRole("heading", { name: "Buildings" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Water Schedule" })).not.toBeInTheDocument();
  });

  it("shows a not-found placeholder for an unknown route instead of crashing", () => {
    renderAt("/this-route-does-not-exist");
    expect(screen.getByRole("heading", { name: "Not found" })).toBeInTheDocument();
  });
});