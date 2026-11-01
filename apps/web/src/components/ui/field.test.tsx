import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Field, TextInput } from "./field";

describe("Field", () => {
  it("associates the label and surfaces an accessible error", () => {
    render(
      <Field id="email" label="Email" hint="We never share it" error="Enter a valid address">
        <TextInput id="email" />
      </Field>,
    );
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAttribute("aria-describedby", "email-hint email-error");
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid address");
  });
});
