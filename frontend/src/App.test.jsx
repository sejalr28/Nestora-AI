import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import App from "./App";

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );
}

describe("App routing + layout", () => {
  it("redirects the index route to Water Schedule", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { name: "Water Schedule" })).toBeInTheDocument();
  });

  it("renders all five nav links in the sidebar", () => {
    renderAt("/water-schedule");
    for (const label of ["Water Schedule", "Buildings", "Vendors", "Residents", "Service Requests"]) {
      expect(screen.getAllByRole("link", { name: label }).length).toBeGreaterThan(0);
    }
  });

  it("navigates to a different page when a sidebar link is clicked", async () => {
    const user = userEvent.setup();
    renderAt("/water-schedule");

    expect(screen.getByRole("heading", { name: "Water Schedule" })).toBeInTheDocument();

    // Desktop and mobile sidebars both render "Buildings" links (mobile one
    // is hidden via CSS, not absent from the DOM) -- click the first.
    const buildingsLinks = screen.getAllByRole("link", { name: "Buildings" });
    await user.click(buildingsLinks[0]);

    expect(screen.getByRole("heading", { name: "Buildings" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Water Schedule" })).not.toBeInTheDocument();
  });

  it("shows a not-found placeholder for an unknown route instead of crashing", () => {
    renderAt("/this-route-does-not-exist");
    expect(screen.getByRole("heading", { name: "Not found" })).toBeInTheDocument();
  });
});