import { describe, it, expect } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

describe("Button component", () => {
  it("renders with text", () => {
    render(React.createElement(Button, null, "Click me"));
    expect(screen.getByText("Click me")).toBeInTheDocument();
  });

  it("applies default variant class", () => {
    render(React.createElement(Button, null, "Default"));
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("bg-primary");
  });

  it("applies destructive variant", () => {
    render(React.createElement(Button, { variant: "destructive" }, "Delete"));
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("bg-destructive");
  });

  it("can be disabled", () => {
    render(React.createElement(Button, { disabled: true }, "Disabled"));
    const btn = screen.getByRole("button");
    expect(btn).toBeDisabled();
  });

  it("handles click events", async () => {
    let clicked = false;
    render(
      React.createElement(Button, { onClick: () => (clicked = true) }, "Click")
    );
    screen.getByRole("button").click();
    expect(clicked).toBe(true);
  });
});

describe("Card components", () => {
  it("renders card with title", () => {
    render(
      React.createElement(
        Card,
        null,
        React.createElement(
          CardHeader,
          null,
          React.createElement(CardTitle, null, "My Card")
        ),
        React.createElement(CardContent, null, "Card body")
      )
    );
    expect(screen.getByText("My Card")).toBeInTheDocument();
    expect(screen.getByText("Card body")).toBeInTheDocument();
  });
});
