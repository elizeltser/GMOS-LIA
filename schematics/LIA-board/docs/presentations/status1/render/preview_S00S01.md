---
marp: true
html: true
theme: default
size: 16:9
paginate: true
footer: 'GMOS LIA Board · Status 1 · Eli Zeltser · 29 Oct 2026'
style: |
  section { font-size: 26px; padding: 40px 56px; }
  section h1 { font-size: 40px; }
  section table { font-size: 20px; }
  .risk-green  { background: #d4edda; font-weight: bold; }
  .risk-orange { background: #ffe0b2; font-weight: bold; }
  .risk-red    { background: #f8d7da; font-weight: bold; }
  .tag { font-size: 16px; font-weight: bold; padding: 2px 8px; border-radius: 4px; }
  .tag-hard { background: #d4edda; }
  .tag-fluid { background: #fff3cd; }
  .tag-proposed { background: #e2e3f5; }
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: '' -->

<style scoped>h1 { font-size: 56px; }</style>

# LIA Board: Status and Decisions

**Eli Zeltser** · 29 October 2026

Presented to the GMOS research team

Source: schematics/LIA-board/docs/presentations/status1_presentation_prompt.md §0

<!-- Facts: §0 of the prompt. Say: Status of the lock-in readout board that replaces the bench setup. What is decided, what is still open, and what I need from the team. -->
---
# What this talk covers

1. Board requirements as I understand them: hard vs fluid
2. My design guidelines, with a look to the future
3. The major design decisions in front of me
4. Risk of each decision, with mitigations
5. Current status and the next goals

Requirement: <span class="tag tag-hard">HARD: must</span> <span class="tag tag-fluid">FLUID: TBD</span> <span class="tag tag-proposed">PROPOSED: owner may drop</span>
Risk: <span class="risk-green">GREEN: low</span> <span class="risk-orange">ORANGE: medium</span> <span class="risk-red">RED: high</span>

Source: schematics/LIA-board/docs/presentations/status1_presentation_prompt.md §1

<!-- Facts: §1 of the prompt. Say: Five parts. Tags mark requirements, colours mark risk; both always carry a text label, so the shared green means "must" on a tag and "low risk" in a risk cell. -->
