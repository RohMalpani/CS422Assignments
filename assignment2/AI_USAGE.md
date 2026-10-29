# AI usage acknowledgment — Assignment 2

Claude Code (Anthropic) was used as a coding assistant, step by step, for Part 1:
- explaining the iperf3 control/data protocol and drafting `iperf3_client.py`;
- drafting the `struct tcp_info` decoder (`goodput.py`), which we verified against C `offsetof()`;
- boilerplate for the experiment driver, plotting and summary tables;
- debugging and testing runs against public iperf3 servers in WSL2.

Each step was explained, tested and logged in `DECISIONS.md`; group members are responsible for understanding and being able to explain all code.

## Report and pipeline preparation

OpenAI Codex assisted with the Part 1/2 report, wiring Part 2 plotting into the
entry point, and completing the Part 3 report from the saved live-run data.
It added reproducible Part 3 summary tables and compact comparison plots,
checked successful-run filtering and matched repetitions, and compiled and
visually reviewed the report. The custom algorithm's existing design was
preserved; its preliminary motivation was updated using the completed dataset.
No new live measurements were collected during this report-completion step.

Codex also compared the design description with Assignment 3's kernel source,
made the existing controller safeguards explicit in both pseudocode documents,
and reorganized the report to follow Assignment 3's structure. This documentation
revision did not modify the kernel controller or collect new measurements.

Codex rewrote the report in assignment question order, aligned formatting with the other reports, clarified the seven Part 2 plot interpretations, and rebuilt and visually checked the PDF. This revision used existing measurements and did not run new experiments.

Codex revised the controller section to present it as a proposed algorithm, preserving its pseudocode and thresholds, and rebuilt the report PDF.
