import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, FALLBACK_ERROR_MESSAGE, getHello } from "./client";

function mockFetch(impl: (url: string) => Promise<Response>) {
  const fn = vi.fn(impl);
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("getHello", () => {
  it("returns the message on success and calls the same-origin URL", async () => {
    const fetchMock = mockFetch(async () =>
      Response.json({ message: "Welcome to Canasta, Ana!" }),
    );
    await expect(getHello("Ana")).resolves.toEqual({
      message: "Welcome to Canasta, Ana!",
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/hello?name=Ana");
  });

  it("throws the envelope message on a non-2xx envelope", async () => {
    mockFetch(async () =>
      Response.json(
        { error: { code: "validation_error", message: "Invalid name" } },
        { status: 422 },
      ),
    );
    const promise = getHello("!!");
    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(promise).rejects.toThrow("Invalid name");
  });

  it("uses the fallback message on a non-2xx without an envelope", async () => {
    mockFetch(async () => new Response("<html>bad gateway</html>", { status: 502 }));
    await expect(getHello("Ana")).rejects.toThrow(FALLBACK_ERROR_MESSAGE);
  });

  it("uses the fallback message on invalid JSON", async () => {
    mockFetch(async () => new Response("not json", { status: 200 }));
    await expect(getHello("Ana")).rejects.toThrow(FALLBACK_ERROR_MESSAGE);
  });

  it("uses the fallback message when JSON lacks a message", async () => {
    mockFetch(async () => Response.json({ other: 1 }));
    await expect(getHello("Ana")).rejects.toThrow(FALLBACK_ERROR_MESSAGE);
  });

  it("uses the fallback message on a network failure", async () => {
    mockFetch(async () => {
      throw new TypeError("Failed to fetch");
    });
    await expect(getHello("Ana")).rejects.toThrow(FALLBACK_ERROR_MESSAGE);
  });

  it("URL-encodes names with spaces and accents", async () => {
    const fetchMock = mockFetch(async () => Response.json({ message: "ok" }));
    await getHello("José Núñez");
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/hello?name=${encodeURIComponent("José Núñez")}`,
    );
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("Jos%C3%A9%20N%C3%BA%C3%B1ez");
  });

  it("prefixes VITE_API_BASE_URL when set", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://x.test");
    const fetchMock = mockFetch(async () => Response.json({ message: "ok" }));
    await getHello("Ana");
    expect(fetchMock).toHaveBeenCalledWith("https://x.test/api/v1/hello?name=Ana");
  });

  it("uses an empty base when VITE_API_BASE_URL is empty", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    const fetchMock = mockFetch(async () => Response.json({ message: "ok" }));
    await getHello("Ana");
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/hello?name=Ana");
  });
});
