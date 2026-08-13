import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import WorkflowsPage from "./WorkflowsPage";
import { workflowsApi } from "../api/workflows";

vi.mock("../api/workflows", () => ({ workflowsApi: { run: vi.fn() } }));

beforeEach(() => {
  vi.clearAllMocks();
});

const SAMPLE_OUTCOME = {
  goal: "assign an available plumber to every open plumbing request",
  plan: [],
  results: [
    {
      step: 1,
      tool: "find_available_vendor",
      arguments: { category: "Plumber" },
      reason: "check capacity",
      status: "done",
      result: { vendor: { name: "Ganesh Pipe Works" } },
    },
    {
      step: 2,
      tool: "assign_vendor_to_request",
      arguments: { request_id: 101, vendor_id: 1, assigned_slot: "9-10 AM" },
      reason: "assign it",
      status: "done",
      result: { status: "assigned" },
    },
  ],
  summary: "Assigned Ganesh Pipe Works to the open plumbing request.",
};

describe("WorkflowsPage", () => {
  it("disables the run button until a goal is entered", () => {
    render(<WorkflowsPage />);
    expect(screen.getByRole("button", { name: "Run workflow" })).toBeDisabled();
  });

  it("runs the workflow and renders the summary and steps", async () => {
    const user = userEvent.setup();
    workflowsApi.run.mockResolvedValue(SAMPLE_OUTCOME);

    render(<WorkflowsPage />);
    await user.type(screen.getByLabelText("Workflow goal"), "assign an available plumber");
    await user.click(screen.getByRole("button", { name: "Run workflow" }));

    expect(await screen.findByText("Assigned Ganesh Pipe Works to the open plumbing request.")).toBeInTheDocument();
    expect(screen.getByText("Steps (2)")).toBeInTheDocument();
    expect(screen.getByText("Step 1: find_available_vendor")).toBeInTheDocument();
    expect(screen.getByText("Step 2: assign_vendor_to_request")).toBeInTheDocument();
    expect(workflowsApi.run).toHaveBeenCalledWith("assign an available plumber");
  });

  it("shows a loading state while running", async () => {
    const user = userEvent.setup();
    let resolveRun;
    workflowsApi.run.mockReturnValue(new Promise((resolve) => { resolveRun = resolve; }));

    render(<WorkflowsPage />);
    await user.type(screen.getByLabelText("Workflow goal"), "do something");
    await user.click(screen.getByRole("button", { name: "Run workflow" }));

    expect(screen.getByRole("button", { name: "Running…" })).toBeInTheDocument();
    resolveRun(SAMPLE_OUTCOME);
    expect(await screen.findByRole("button", { name: "Run workflow" })).toBeInTheDocument();
  });

  it("shows step-level error status distinctly from done", async () => {
    const user = userEvent.setup();
    workflowsApi.run.mockResolvedValue({
      ...SAMPLE_OUTCOME,
      results: [
        { step: 1, tool: "assign_vendor_to_request", arguments: {}, reason: "bad id", status: "error", result: { error: "No such request" } },
      ],
      summary: "The assignment failed.",
    });

    render(<WorkflowsPage />);
    await user.type(screen.getByLabelText("Workflow goal"), "assign something invalid");
    await user.click(screen.getByRole("button", { name: "Run workflow" }));

    expect(await screen.findByText("error")).toBeInTheDocument();
    expect(screen.getByText(/No such request/)).toBeInTheDocument();
  });

  it("shows an error with retry on failure", async () => {
    const user = userEvent.setup();
    workflowsApi.run.mockRejectedValueOnce(new Error("Network down"));

    render(<WorkflowsPage />);
    await user.type(screen.getByLabelText("Workflow goal"), "do something");
    await user.click(screen.getByRole("button", { name: "Run workflow" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't run the workflow: Network down");

    workflowsApi.run.mockResolvedValueOnce(SAMPLE_OUTCOME);
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Assigned Ganesh Pipe Works to the open plumbing request.")).toBeInTheDocument();
  });

  it("fills the goal field when an example goal is clicked", async () => {
    const user = userEvent.setup();
    render(<WorkflowsPage />);

    await user.click(screen.getByText("Assign an available plumber to every open plumbing request"));

    expect(screen.getByLabelText("Workflow goal")).toHaveValue(
      "Assign an available plumber to every open plumbing request"
    );
  });

  it("does not run on an empty goal", async () => {
    const user = userEvent.setup();
    render(<WorkflowsPage />);
    await user.type(screen.getByLabelText("Workflow goal"), "   ");
    expect(screen.getByRole("button", { name: "Run workflow" })).toBeDisabled();
    expect(workflowsApi.run).not.toHaveBeenCalled();
  });
});