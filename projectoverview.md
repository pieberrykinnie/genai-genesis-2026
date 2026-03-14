Dashboard-style app

Target user: City councils and planners

Goal: Project the economical, environmental, and sociological effects of a new data centre (with some parameters) being built at a location

Tech stack:
* Frontend: TypeScript + Next.js 16.1.6 + Tailwind v4 + pnpm + 10.32.1
* **DO NOT USE NPM**
* Backend: Python 3.14 + FastAPI 0.135 + uv 0.10.10
* External APIs: MapTiler, Groq (or https://github.com/microsoft/BitNet in place of Groq for LLM tasks)

User flow:

1. City council inputs details about the data center proposal and where it's being built
2. System takes real Canadian geolocational, energy, sustainability, etc. data
3. System runs complex, real calculations to measure impact
4. System generates full report w.r.t. effects of the data center being built on the location
5. System suggests different courses of action when dealing with the proposal (possible negotiations, etc.)

Important: Data and calculation should be as real and informed as it is feasible to. Minimize features and maximize real data being involved

## 0. Project Summary

**What it is:** A dynamic negotiation and impact-modeling engine for municipal governments. By combining real-time Canadian open data with predictive ML, it stress-tests proposed data centers against local infrastructure limits, generating a strict, mathematically sound Community Benefit Agreement (CBA) term sheet to protect local taxpayers.

**The pitch frame (important for demo):** The era of vague job promises and secret NDAs is over. City councils face intense public backlash over strained grids, water depletion, and spiked utility bills. DataSite shifts the power dynamic. It arms municipalities to stress-test data center proposals and generates a legally actionable Community Benefit Agreement (CBA) playbook—dictating the exact water replenishment targets, local hiring minimums, and grid infrastructure costs the developer must legally commit to before a single shovel hits the dirt.

Judging criteria 

Criteria 1: Innovation & Originality
Focuses on the project's ability to introduce novel concepts, methods, or applications, and to demonstrate creative problem-solving.
Criteria 2: Technical Complexity & Execution
Operational effectiveness, code quality, and success in meeting specified requirements and performance standards.
Criteria 3: Product Experience & Design
Overall structure of the project, including visual appeal user experience, and the organization of its architecture and code.
Criteria 4: Impact & Practical Value
The project's potential to address real-world problems, create positive change, and contribute to meaningful outcomes.

Award we are aiming for - 
Google Best Sustainability AI Hack
1 winner
Awarded to the team that creates the most innovative AI solution to address environmental or sustainability challenges and drive meaningful real-world impact

---

**See also:** `projectspec.md` (full API, data sources, ML), `AGENTS.md` (required inputs, data URLs, practical rules), `README.md` (quickstart, scripts).

