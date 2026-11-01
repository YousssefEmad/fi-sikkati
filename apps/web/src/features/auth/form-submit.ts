import type { SyntheticEvent } from "react";
import type { FieldValues, UseFormHandleSubmit } from "react-hook-form";

/** react-hook-form's handleSubmit returns a Promise; the DOM onSubmit handler must not. */
export function onValidSubmit<T extends FieldValues>(
  handleSubmit: UseFormHandleSubmit<T>,
  handler: (values: T) => Promise<void>,
) {
  return (event: SyntheticEvent<HTMLFormElement>) => {
    void handleSubmit(handler)(event);
  };
}
