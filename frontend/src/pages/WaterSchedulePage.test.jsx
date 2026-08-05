import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import WaterSchedulePage from "./WaterSchedulePage";
import { waterScheduleApi } from "../api/waterSchedule";

vi.mock("../api/waterSchedule", () => ({
  waterScheduleApi: {
    list: vi.fn(),
    update: vi.fn(),
  },
}));

const BOTH_SCHEDULES = [
  { id: 1, source: "corporation", start_time: "08:00:00", end_time: "10:00:00", note: "Fill early" },
  { id: 2, source: "bore", start_time: "21:00:00", end_time: "01:00:00", note: "Alternate nights" },
];

beforeEach(() => {
  vi.clearAllMocks();
});

describe("WaterSchedulePage", () => {
  it("shows a loading state before data arrives", () => {
    waterScheduleApi.list.mockReturnValue(new Promise(() => {})); // never resolves
    render(<WaterSchedulePage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders both sources with formatted times and notes once loaded", async () => {
    waterScheduleApi.list.mockResolvedValue(BOTH_SCHEDULES);
    render(<WaterSchedulePage />);

    expect(await screen.findByText("8:00 AM – 10:00 AM")).toBeInTheDocument();
    expect(screen.getByText("9:00 PM – 1:00 AM")).toBeInTheDocument();
    expect(screen.getByText("Fill early")).toBeInTheDocument();
    expect(screen.getByText("Alternate nights")).toBeInTheDocument();
  });

  it("shows 'Not set yet' for a source with no schedule row", async () => {
    waterScheduleApi.list.mockResolvedValue([BOTH_SCHEDULES[0]]); // bore missing
    render(<WaterSchedulePage />);

    await screen.findByText("8:00 AM – 10:00 AM");
    expect(screen.getByText("Not set yet.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Set timing" })).toBeInTheDocument();
  });

  it("shows a retry-able error if loading fails", async () => {
    waterScheduleApi.list.mockRejectedValueOnce(new Error("Network down"));
    render(<WaterSchedulePage />);

    expect(await screen.findByText(/Couldn't load the water schedule: Network down/)).toBeInTheDocument();

    waterScheduleApi.list.mockResolvedValueOnce(BOTH_SCHEDULES);
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("8:00 AM – 10:00 AM")).toBeInTheDocument();
  });

  it("edits and saves a schedule with the correct payload, then reloads", async () => {
    const user = userEvent.setup();
    waterScheduleApi.list.mockResolvedValue(BOTH_SCHEDULES);
    waterScheduleApi.update.mockResolvedValue({});

    render(<WaterSchedulePage />);
    await screen.findByText("8:00 AM – 10:00 AM");

    const updateButtons = screen.getAllByRole("button", { name: "Update timing" });
    await user.click(updateButtons[0]); // corporation card is first

    const noteInput = screen.getByPlaceholderText("e.g. Municipal line — fill early");
    await user.clear(noteInput);
    await user.type(noteInput, "New note");

    await user.click(screen.getByRole("button", { name: "Post update" }));

    expect(waterScheduleApi.update).toHaveBeenCalledWith("corporation", {
      start_time: "08:00:00",
      end_time: "10:00:00",
      note: "New note",
      updated_by: "Committee",
    });
    // list() is called once on mount and again after a successful save
    expect(waterScheduleApi.list).toHaveBeenCalledTimes(2);
  });

  it("shows a save error inside the modal without closing it", async () => {
    const user = userEvent.setup();
    waterScheduleApi.list.mockResolvedValue(BOTH_SCHEDULES);
    waterScheduleApi.update.mockRejectedValue(new Error("Validation failed"));

    render(<WaterSchedulePage />);
    await screen.findByText("8:00 AM – 10:00 AM");

    await user.click(screen.getAllByRole("button", { name: "Update timing" })[0]);
    await user.click(screen.getByRole("button", { name: "Post update" }));

    expect(await screen.findByText("Validation failed")).toBeInTheDocument();
    // modal is still open -- Cancel button still present
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("closes the modal without saving when Cancel is clicked", async () => {
    const user = userEvent.setup();
    waterScheduleApi.list.mockResolvedValue(BOTH_SCHEDULES);

    render(<WaterSchedulePage />);
    await screen.findByText("8:00 AM – 10:00 AM");

    await user.click(screen.getAllByRole("button", { name: "Update timing" })[0]);
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("button", { name: "Post update" })).not.toBeInTheDocument();
    expect(waterScheduleApi.update).not.toHaveBeenCalled();
  });
});