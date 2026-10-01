# ADR-002: Bidding zones

**Date:** 2026-10-01 · **Status:** accepted

## Context
We need a set of bidding zones that is small enough to finish fast but varied enough to tell a European story.

## Options
1. All EU zones (~40) — complete, but slow to pull and noisy to present
2. 8 contrasting zones — focused, covers every market "type"
3. Spain only — too narrow

## Decision
Option 2. Eight zones:

| Code | Zone | Why it's in |
|---|---|---|
| ES | Spain | Solar giant, frequent zero/negative prices |
| PT | Portugal | Coupled with Spain (Iberian market) |
| FR | France | Nuclear-heavy, big exporter |
| DE_LU | Germany–Luxembourg | Largest market, wind + solar, most negative hours |
| NL | Netherlands | Fast solar growth, gas-priced evenings |
| BE | Belgium | Interconnected hub between FR/NL/DE |
| PL | Poland | Coal-heavy contrast case |
| IT_NORD | North Italy | Gas-driven, high-price contrast |

## Why
Covers solar-heavy, wind-heavy, nuclear, coal and gas-driven markets, plus tightly coupled neighbours (ES–PT, FR–BE–NL–DE). Enough contrast for every question (Q1–Q4).

## Consequences
- Easy to add zones later (Nordics, Austria) — the pipeline takes a list of zone codes.
