import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button } from "./button";

describe("Button", () => {
  it("defaults to type=button so it never submits forms accidentally", () => {
    render(<Button>Go</Button>);
    expect(screen.getByRole("button", { name: "Go" })).toHaveAttribute("type", "button");
  });

  it("calls onClick and respects disabled", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(
      <>
        <Button onClick={onClick}>Active</Button>
        <Button onClick={onClick} disabled>
          Off
        </Button>
      </>,
    );
    await user.click(screen.getByRole("button", { name: "Active" }));
    await user.click(screen.getByRole("button", { name: "Off" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
