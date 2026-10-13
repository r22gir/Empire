import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { isAppDeepLink, safeUrl } from "./safeUrl.ts";

describe("safeUrl app deep links", () => {
  it("allows presentation / organizer / quotes hrefs from the screen-path map", () => {
    assert.equal(safeUrl("/?screen=presentation&mode=presentation"), "/?screen=presentation&mode=presentation");
    assert.equal(safeUrl("/?product=vision&section=analyzer"), "/?product=vision&section=analyzer");
    assert.equal(safeUrl("/?product=workroom&section=quotes"), "/?product=workroom&section=quotes");
    assert.equal(isAppDeepLink("/?screen=quote"), true);
  });

  it("rejects javascript and stale-looking schemes", () => {
    assert.equal(safeUrl("javascript:alert(1)"), null);
    assert.equal(safeUrl("data:text/html,hi"), null);
  });

  it("allows https and root", () => {
    assert.equal(safeUrl("https://empirebox.store"), "https://empirebox.store");
    assert.equal(safeUrl("/"), "/");
  });
});
