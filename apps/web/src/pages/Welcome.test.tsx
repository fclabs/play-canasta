import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { afterEach, describe, expect, it, vi } from "vitest";
import Welcome from "./Welcome";

function mockFetch(impl: (url: string) => Promise<Response>) {
  const fn = vi.fn(impl);
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Welcome page", () => {
  it("renders heading, description, labelled input and button without fetching", () => {
    const fetchMock = mockFetch(async () => Response.json({ message: "x" }));
    render(<Welcome />);
    expect(
      screen.getByRole("heading", { name: "Welcome to Canasta" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Your name")).toHaveAttribute("maxlength", "40");
    expect(screen.getByRole("button", { name: "Ping API" })).toBeInTheDocument();
    expect(screen.getByText(/card game/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows pending state then the status message on success", async () => {
    let resolve!: (r: Response) => void;
    const fetchMock = mockFetch(() => new Promise<Response>((r) => (resolve = r)));
    const user = userEvent.setup();
    render(<Welcome />);
    await user.type(screen.getByLabelText("Your name"), "Ana");
    await user.click(screen.getByRole("button", { name: "Ping API" }));

    const pending = screen.getByRole("button", { name: "Pinging…" });
    expect(pending).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/hello?name=Ana");

    resolve(Response.json({ message: "Welcome to Canasta, Ana!" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Welcome to Canasta, Ana!",
    );
    const button = screen.getByRole("button", { name: "Ping API" });
    expect(button).toBeEnabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows the envelope message on a 422", async () => {
    mockFetch(async () =>
      Response.json(
        { error: { code: "validation_error", message: "Invalid name" } },
        { status: 422 },
      ),
    );
    const user = userEvent.setup();
    render(<Welcome />);
    await user.click(screen.getByRole("button", { name: "Ping API" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid name");
    expect(screen.getByRole("button", { name: "Ping API" })).toBeEnabled();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it.each([
    ["network error", () => Promise.reject(new TypeError("Failed to fetch"))],
    ["invalid JSON", async () => new Response("nope", { status: 200 })],
  ])("shows the fallback message on %s", async (_label, impl) => {
    mockFetch(impl);
    const user = userEvent.setup();
    render(<Welcome />);
    await user.click(screen.getByRole("button", { name: "Ping API" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not reach the server",
    );
    expect(screen.getByRole("button", { name: "Ping API" })).toBeEnabled();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("truncates pasted input to 40 characters and sends at most 40", async () => {
    const fetchMock = mockFetch(async () => Response.json({ message: "ok" }));
    const user = userEvent.setup();
    render(<Welcome />);
    const input = screen.getByLabelText("Your name");
    await user.click(input);
    await user.paste("a".repeat(60));
    expect(input).toHaveValue("a".repeat(40));
    await user.click(screen.getByRole("button", { name: "Ping API" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const url = new URL(String(fetchMock.mock.calls[0]?.[0]), "http://localhost");
    expect(url.searchParams.get("name")?.length).toBe(40);
  });

  it("truncates programmatically oversized values (no maxlength enforcement)", async () => {
    const { fireEvent } = await import("@testing-library/react");
    render(<Welcome />);
    const input = screen.getByLabelText("Your name");
    fireEvent.change(input, { target: { value: "b".repeat(60) } });
    expect(input).toHaveValue("b".repeat(40));
  });

  it("encodes accents and spaces in the request", async () => {
    const fetchMock = mockFetch(async () => Response.json({ message: "ok" }));
    const user = userEvent.setup();
    render(<Welcome />);
    await user.type(screen.getByLabelText("Your name"), "José Núñez");
    await user.click(screen.getByRole("button", { name: "Ping API" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/hello?name=${encodeURIComponent("José Núñez")}`,
    );
  });

  it("is keyboard operable: Tab goes input then button, Enter submits", async () => {
    const fetchMock = mockFetch(async () => Response.json({ message: "ok" }));
    const user = userEvent.setup();
    render(<Welcome />);
    await user.tab();
    expect(screen.getByLabelText("Your name")).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Ping API" })).toHaveFocus();
    await user.click(screen.getByLabelText("Your name"));
    await user.keyboard("Ana{Enter}");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  });

  it("has no serious or critical axe violations", async () => {
    mockFetch(async () => Response.json({ message: "ok" }));
    const { container } = render(<Welcome />);
    const results = await axe(container);
    const bad = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    );
    expect(bad).toEqual([]);
  });
});
