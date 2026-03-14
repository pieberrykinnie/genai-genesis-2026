# Project Overview

## Problem

City councils are being asked to approve data centre projects with major infrastructure implications and limited technical visibility.

## Solution

DataSite Impact Analyzer is a council-facing decision system that quantifies trade-offs using real Canadian datasets, deterministic formulas, and ML signals.

It helps councils answer:
- How much grid stress and rate pressure could this project create?
- How much water does it consume relative to local supply?
- Are economic claims realistic versus permanent job creation?
- What policy conditions should be mandatory before approval?

## Target Audience

- Municipal councils
- Planning departments
- Economic development teams
- Public stakeholders reviewing project transparency

## Product Experience

1. Proposal Intake
2. Location Context (map + risk chips + noise radius)
3. Impact Results (plain-language pillar summaries)
4. Decision Brief (recommendation, clauses, evidence freshness)

## AI/ML Stack

- Deterministic calculation engine: transparent formulas and evidence pack
- XGBoost model: real ON + AB historical grid data for strain prediction
- Railtracks workflow: grounded memo generation, verification, repair, and traceability

## Design Principle

For high-stakes municipal decisions, policy selection must be deterministic and auditable.
The LLM explains evidence; it does not invent policy.

## Hackathon Fit

- Sustainability impact: grid, water, and community risk are first-class outputs
- Technical depth: real ingestion, model training/inference, strict API contracts
- Product value: understandable outputs for non-technical decision makers
