---
name: pinchtab
description: |
  Browser automation using PinchTab (pinchtab.dev).
  Use when the user wants to control a browser, navigate pages, click buttons, take screenshots,
  extract data, or automate any browser task.
  
  Triggers include: "open a website", "fill out a form", "click a button", "take a screenshot",
  "scrape data", "test a web app", "login to a site", "automate browser actions", or any task
  requiring programmatic web interaction.
  
  PinchTab runs as a service and can be controlled via CLI commands or SDK.
  
  Usage: npx pinchtab <command> [options]
  
  Core commands:
  - open <url>          - Navigate to URL
  - click <selector>    - Click element
  - fill <selector> <text> - Fill input field
  - screenshot [path]   - Take screenshot
  - pdf <path>          - Save as PDF
  - get <property>      - Get element property
  - wait <condition>    - Wait for condition
  - close               - Close browser

allowed-tools:
  - Bash(npx pinchtab:*)
  - Bash(pinchtab)
---

# PinchTab Browser Automation Skill

PinchTab is a browser automation tool that runs as a service and can be controlled via CLI.

## Installation

PinchTab is available via npx:
```bash
npx pinchtab open https://example.com
```

## Core Workflow

Every browser automation follows this pattern:

1. **Navigate**: `npx pinchtab open <url>`
2. **Wait**: Wait for page to load
3. **Interact**: Click, fill, select elements
4. **Extract**: Get text, attributes, or screenshots
5. **Close**: `npx pinchtab close`

## Common Commands

```bash
# Navigation
npx pinchtab open https://example.com
npx pinchtab back
npx pinchtab forward
npx pinchtab reload

# Interaction
npx pinchtab click "#submit-button"
npx pinchtab fill "#email" "user@example.com"
npx pinchtab select "#country" "United States"

# Information
npx pinchtab get text "#content"
npx pinchtab get attr "href" "#link"
npx pinchtab get url
npx pinchtab get title

# Wait
npx pinchtab wait "#loaded"
npx pinchtab wait 5000
npx pinchtab wait networkidle

# Capture
npx pinchtab screenshot
npx pinchtab screenshot --full
npx pinchtab screenshot /path/to/image.png
npx pinchtab pdf output.pdf

# Evaluate JavaScript
npx pinchtab eval "document.title"
npx pinchtab eval "document.querySelector('#content').innerText"
```

## Selectors

PinchTab supports CSS selectors:
- ID: `#submit-button`
- Class: `.btn-primary`
- Attribute: `[data-testid="submit"]`
- Combination: `form.login-form input[type="email"]`

## Common Patterns

### Form Submission
```bash
npx pinchtab open https://example.com/login
npx pinchtab fill "#email" "user@example.com"
npx pinchtab fill "#password" "password123"
npx pinchtab click "#login-button"
npx pinchtab wait networkidle
```

### Data Extraction
```bash
npx pinchtab open https://example.com/products
npx pinchtab get text ".product-name"
npx pinchtab screenshot
```

### Screenshot
```bash
npx pinchtab open https://example.com
npx pinchtab wait networkidle
npx pinchtab screenshot /tmp/example.png
```

## Tips

- Use `wait networkidle` after navigation to ensure page is fully loaded
- Use specific selectors for more reliable automation
- Take screenshots for debugging or verification
- Close the browser when done to free resources

## Service Mode

PinchTab can run as a background service:
```bash
npx pinchtab start
npx pinchtab open https://example.com
# ... more commands
npx pinchtab stop
```

## Notes

- PinchTab uses npx, so no global installation required
- The service runs in the background and persists between commands
- Use `npx pinchtab help` for more commands and options
